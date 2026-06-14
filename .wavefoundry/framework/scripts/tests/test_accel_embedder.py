"""Wave 1p517: tests for the GPU static-shape embedder dispatch + pooling.

Hardware-free: the ONNX session and tokenizer are mocked, so these run in CI without a
GPU/ANE (per AC-7). The real CoreML cos-equivalence is validated on the operator's machine.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

SCRIPTS = Path(__file__).resolve().parent.parent


def load_accel():
    spec = importlib.util.spec_from_file_location("accel_embedder", SCRIPTS / "accel_embedder.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["accel_embedder"] = mod
    spec.loader.exec_module(mod)
    return mod


class _Enc:
    def __init__(self, seq):
        self.ids = [1] * seq
        self.attention_mask = [1] * seq
        self.type_ids = [0] * seq


class _FakeTokenizer:
    def enable_truncation(self, **_): pass
    def enable_padding(self, **_): pass
    def encode_batch(self, texts):
        return [_Enc(512) for _ in texts]


class _FakeSession:
    """Returns a fixed [B, S, H] hidden state; row r's CLS token (pos 0) = unit vector e_r."""
    def __init__(self, hidden):
        self._hidden = hidden
        self._names = ["input_ids", "attention_mask", "token_type_ids"]

    def get_inputs(self):
        return [type("I", (), {"name": n}) for n in self._names]

    def run(self, _outputs, feed):
        b = feed["input_ids"].shape[0]
        return [self._hidden[:b]]


def _make_embedder(ae, hidden):
    """Build a StaticShapeEmbedder bypassing __init__ (no real ONNX/CoreML)."""
    emb = ae.StaticShapeEmbedder.__new__(ae.StaticShapeEmbedder)
    emb.model_name = "fake/model"
    emb.provider = "CoreMLExecutionProvider"
    emb.session = _FakeSession(hidden)
    emb.input_names = ["input_ids", "attention_mask", "token_type_ids"]
    emb.tokenizer = _FakeTokenizer()
    return emb


class _FakeRerankSession:
    """Cross-encoder session: returns a [B, 1] logit; row r's logit = r (asserts per-passage order).

    Mirrors the RoBERTa reranker, which takes only input_ids + attention_mask (no token_type_ids).
    """
    def __init__(self):
        self._names = ["input_ids", "attention_mask"]

    def get_inputs(self):
        return [type("I", (), {"name": n}) for n in self._names]

    def get_outputs(self):
        return [type("O", (), {"name": "logits"})]

    def run(self, _outputs, feed):
        b = feed["input_ids"].shape[0]
        return [np.arange(b, dtype=np.float32).reshape(b, 1)]


def _make_reranker(ae):
    """Build a StaticShapeReranker bypassing __init__ (no real ONNX/CoreML)."""
    rr = ae.StaticShapeReranker.__new__(ae.StaticShapeReranker)
    rr.model_name = "fake/reranker"
    rr.provider = "CoreMLExecutionProvider"
    rr.session = _FakeRerankSession()
    rr.input_names = ["input_ids", "attention_mask"]   # roberta reranker: no token_type_ids
    rr.output_name = "logits"
    rr.tokenizer = _FakeTokenizer()
    return rr


class AccelEmbedderTests(unittest.TestCase):
    def setUp(self):
        self.ae = load_accel()

    def test_make_embedder_none_when_no_gpu_available(self):
        # No GPU available (CPU-only machine) → None, regardless of the passed selection.
        with patch.object(self.ae, "_available_gpu_providers", return_value=[]):
            self.assertIsNone(self.ae.make_embedder("BAAI/bge-small-en-v1.5", ["CPUExecutionProvider"]))
            self.assertIsNone(self.ae.make_embedder("BAAI/bge-small-en-v1.5", []))

    def test_make_embedder_falls_back_to_available_gpu(self):
        # Decoupling: even when the (flaky) selection lacks a GPU, accel uses an AVAILABLE GPU so a
        # transient fastembed-probe failure (fresh cache) doesn't disable acceleration.
        with patch.object(self.ae, "_available_gpu_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.ae, "StaticShapeEmbedder") as cls:
            cls.return_value.offloads_to_gpu.return_value = True
            got = self.ae.make_embedder("BAAI/bge-small-en-v1.5", ["CPUExecutionProvider"])
        self.assertIs(got, cls.return_value)
        # Constructed with the available GPU provider + CPU fallback.
        self.assertEqual(cls.call_args.args[1], ["CoreMLExecutionProvider", "CPUExecutionProvider"])

    def test_make_embedder_respects_explicit_cpu_request(self):
        # An explicit WAVEFOUNDRY_EMBED_PROVIDER=cpu disables the GPU accel path entirely.
        with patch.dict(os.environ, {"WAVEFOUNDRY_EMBED_PROVIDER": "cpu"}):
            self.assertEqual(self.ae._available_gpu_providers(), [])
            self.assertIsNone(self.ae.make_embedder("BAAI/bge-small-en-v1.5", ["CPUExecutionProvider"]))

    # ── 1p52p: cross-encoder reranker ───────────────────────────────────────────

    def test_rerank_returns_one_logit_per_passage(self):
        # rerank pads the batch to STATIC_BATCH internally and slices back to the real count;
        # row r's logit = r (per _FakeRerankSession), so 3 passages → [0, 1, 2].
        rr = _make_reranker(self.ae)
        scores = rr.rerank("q", ["a", "b", "c"])
        self.assertEqual(scores, [0.0, 1.0, 2.0])
        self.assertTrue(all(isinstance(s, float) for s in scores))  # raw logits, fastembed scale

    def test_rerank_batches_across_static_batch_boundary(self):
        rr = _make_reranker(self.ae)
        n = self.ae.STATIC_BATCH + 5  # forces 2 internal batches
        scores = rr.rerank("q", [f"p{i}" for i in range(n)])
        self.assertEqual(len(scores), n)
        self.assertEqual(scores[:3], [0.0, 1.0, 2.0])                       # batch 1, rows 0..2
        self.assertEqual(scores[self.ae.STATIC_BATCH:self.ae.STATIC_BATCH + 3], [0.0, 1.0, 2.0])  # batch 2

    def test_make_reranker_cpu_int8_when_no_gpu(self):
        # No GPU → build the CPU INT8 reranker on CPUExecutionProvider (not None — CPU machines rerank).
        with patch.object(self.ae, "_available_gpu_providers", return_value=[]), \
             patch.object(self.ae, "StaticShapeReranker") as cls, \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_DISABLE_RERANKER", None)
            got = self.ae.make_reranker("cross-encoder/ms-marco-MiniLM-L-6-v2", [])
        self.assertIs(got, cls.return_value)
        self.assertEqual(cls.call_args.args[1], ["CPUExecutionProvider"])  # CPU INT8 path

    def test_make_reranker_falls_back_to_available_gpu(self):
        # GPU available → build the FP16 GPU reranker (gpu provider + CPU fallback in the provider list).
        with patch.object(self.ae, "_available_gpu_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.ae, "StaticShapeReranker") as cls, \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_DISABLE_RERANKER", None)
            cls.return_value.offloads_to_gpu.return_value = True
            got = self.ae.make_reranker("cross-encoder/ms-marco-MiniLM-L-6-v2", [])
        self.assertIs(got, cls.return_value)
        self.assertEqual(cls.call_args.args[1], ["CoreMLExecutionProvider", "CPUExecutionProvider"])

    def test_make_reranker_gpu_fragmented_falls_back_to_cpu(self):
        # A GPU graph that doesn't actually offload (offloads_to_gpu False) → fall through to CPU INT8.
        gpu_inst = MagicMock(); gpu_inst.offloads_to_gpu.return_value = False
        cpu_inst = MagicMock()
        with patch.object(self.ae, "_available_gpu_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.object(self.ae, "StaticShapeReranker", side_effect=[gpu_inst, cpu_inst]), \
             patch.dict(os.environ, {}, clear=False):
            os.environ.pop("WAVEFOUNDRY_DISABLE_RERANKER", None)
            got = self.ae.make_reranker("cross-encoder/ms-marco-MiniLM-L-6-v2", [])
        self.assertIs(got, cpu_inst)  # the CPU reranker, not the fragmented GPU one

    def test_make_reranker_disabled_returns_none(self):
        # WAVEFOUNDRY_DISABLE_RERANKER turns reranking off entirely (tests / opt-out), GPU or not.
        with patch.object(self.ae, "_available_gpu_providers", return_value=["CoreMLExecutionProvider"]), \
             patch.dict(os.environ, {"WAVEFOUNDRY_DISABLE_RERANKER": "1"}):
            self.assertIsNone(self.ae.make_reranker("cross-encoder/ms-marco-MiniLM-L-6-v2", []))

    def test_reranker_static_pin_keeps_logit_output_dim(self):
        # build_static_onnx(output_is_logit=True) pins input dims [B,S] but the [B,1] logit output's
        # dim1 must stay 1 (pinning it to S would corrupt the score). Build a tiny ONNX and check.
        try:
            import onnx
            from onnx import helper, TensorProto
        except ImportError:
            self.skipTest("onnx unavailable")
        import tempfile
        x = helper.make_tensor_value_info("input_ids", TensorProto.INT64, ["batch", "seq"])
        y = helper.make_tensor_value_info("logits", TensorProto.FLOAT, ["batch", 1])
        node = helper.make_node("Identity", ["input_ids"], ["logits_pre"])
        cast = helper.make_node("Cast", ["logits_pre"], ["logits"], to=TensorProto.FLOAT)
        graph = helper.make_graph([node, cast], "g", [x], [y])
        m = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
        with tempfile.TemporaryDirectory() as d:
            src = os.path.join(d, "src.onnx"); out = os.path.join(d, "out.onnx")
            onnx.save(m, src)
            self.ae.build_static_onnx(src, out, output_is_logit=True)
            pinned = onnx.load(out)
            in_dims = pinned.graph.input[0].type.tensor_type.shape.dim
            out_dims = pinned.graph.output[0].type.tensor_type.shape.dim
            self.assertEqual(in_dims[0].dim_value, self.ae.STATIC_BATCH)   # batch pinned
            self.assertEqual(in_dims[1].dim_value, self.ae.STATIC_SEQ)     # seq pinned
            self.assertEqual(out_dims[0].dim_value, self.ae.STATIC_BATCH)  # logit batch pinned
            self.assertEqual(out_dims[1].dim_value, 1)                     # logit dim1 LEFT at 1

    def test_reranker_fp16_matches_fp32_when_available(self):
        """AC-1 precision + supply-chain integrity for the ACTIVE reranker (RERANKER_MODEL): its GPU
        FP16 export's raw logits match the SAME model's FP32 export within 0.05 across ≥3 queries — so
        the FP16 export didn't corrupt scores and the confidence bands stay valid. GPU+models-gated
        (operator machine); a tampered/divergent FP16 export would fail. Skipped in CI (no GPU)."""
        if not self.ae._available_gpu_providers():
            self.skipTest("no GPU provider")
        # Active reranker logical name → its clean FP16 source.
        import importlib.util
        spec = importlib.util.spec_from_file_location("indexer_for_rr", SCRIPTS / "indexer.py")
        idxmod = importlib.util.module_from_spec(spec); spec.loader.exec_module(idxmod)
        model_name = idxmod.RERANKER_MODEL
        src = self.ae.CLEAN_ONNX_SOURCES.get(model_name)
        if src is None:
            self.skipTest(f"no clean source for {model_name}")
        repo = src[0]
        rr = self.ae.make_reranker(model_name, [])
        if rr is None:
            self.skipTest("GPU reranker unavailable (model not cached?)")
        # FP32 reference: the SAME repo's onnx/model.onnx on CPU.
        try:
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer
            import onnx, onnxruntime as ort
            fp32_src = hf_hub_download(repo, "onnx/model.onnx", cache_dir=str(self.ae._CLEAN_ONNX_CACHE))
            tok = Tokenizer.from_file(hf_hub_download(repo, "tokenizer.json", cache_dir=str(self.ae._CLEAN_ONNX_CACHE)))
        except Exception as exc:
            self.skipTest(f"FP32 reference unavailable: {exc}")
        B, S = self.ae.STATIC_BATCH, self.ae.STATIC_SEQ
        m = onnx.load(fp32_src)
        for vi in m.graph.input:
            d = vi.type.tensor_type.shape.dim
            if len(d) >= 1: d[0].dim_value = B; d[0].ClearField("dim_param")
            if len(d) >= 2: d[1].dim_value = S; d[1].ClearField("dim_param")
        d0 = m.graph.output[0].type.tensor_type.shape.dim
        if len(d0) >= 1: d0[0].dim_value = B; d0[0].ClearField("dim_param")
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmp:
            p = os.path.join(tmp, "fp32_static.onnx"); onnx.save(m, p)
            sess = ort.InferenceSession(p, providers=["CPUExecutionProvider"])
            inn = [i.name for i in sess.get_inputs()]; outn = sess.get_outputs()[0].name
            tok.enable_truncation(max_length=S); tok.enable_padding(length=S)

            def fp32_rerank(q, passages):
                pairs = [(q, x) for x in passages] + [(q, "")] * (B - len(passages))
                enc = tok.encode_batch(pairs)
                feat = {"input_ids": np.array([e.ids for e in enc], np.int64),
                        "attention_mask": np.array([e.attention_mask for e in enc], np.int64),
                        "token_type_ids": np.array([e.type_ids for e in enc], np.int64)}
                out = sess.run([outn], {n: feat[n] for n in inn})[0]
                return np.asarray(out).reshape(B, -1)[:len(passages), 0]

            queries = ["wave lifecycle stage gate", "embedding model cache", "how does reranking work"]
            passages = ["The stage gate blocks edits until prepared.", "Models are cached offline.",
                        "Reranking scores query-document pairs.", "Unrelated text about the weather today."]
            for q in queries:
                fp16 = np.array(rr.rerank(q, passages))
                fp32 = fp32_rerank(q, passages)
                self.assertLess(float(np.max(np.abs(fp16 - fp32))), 0.05, f"score drift on {q!r}")

    def test_make_embedder_none_when_onnx_missing(self):
        # Without `onnx`, the static-shape pin can't run → fall back to fastembed.
        real_import = __import__

        def _no_onnx(name, *a, **k):
            if name == "onnx":
                raise ImportError("no onnx")
            return real_import(name, *a, **k)

        with patch("builtins.__import__", side_effect=_no_onnx):
            self.assertIsNone(
                self.ae.make_embedder("Snowflake/snowflake-arctic-embed-xs", ["CoreMLExecutionProvider"])
            )

    def test_embed_uses_cls_pooling_normalized(self):
        H = 4
        hidden = np.zeros((self.ae.STATIC_BATCH, self.ae.STATIC_SEQ, H), dtype=np.float32)
        # CLS token (pos 0) of row r = (r+1) * e_{r mod H}; pos>0 set differently to prove CLS-only.
        for r in range(self.ae.STATIC_BATCH):
            hidden[r, 0, r % H] = float(r + 1)
            hidden[r, 1, :] = 99.0  # non-CLS positions must be ignored
        emb = _make_embedder(self.ae, hidden)

        out = list(emb.embed(["a", "b", "c"]))
        self.assertEqual(len(out), 3, "one vector per input text (batch padded to 64, sliced to 3)")
        for r, vec in enumerate(out):
            self.assertEqual(vec.shape, (H,))
            self.assertAlmostEqual(float(np.linalg.norm(vec)), 1.0, places=5)  # L2-normalized
            expected = np.zeros(H, dtype=np.float32); expected[r % H] = 1.0  # CLS direction, normalized
            np.testing.assert_allclose(vec, expected, atol=1e-5)

    def test_embed_batches_across_static_batch_boundary(self):
        H = 4
        hidden = np.zeros((self.ae.STATIC_BATCH, self.ae.STATIC_SEQ, H), dtype=np.float32)
        hidden[:, 0, 0] = 1.0  # every row's CLS points at e_0
        emb = _make_embedder(self.ae, hidden)
        n = self.ae.STATIC_BATCH + 5  # forces 2 internal batches
        out = list(emb.embed([f"t{i}" for i in range(n)]))
        self.assertEqual(len(out), n)
        for vec in out:
            np.testing.assert_allclose(vec, np.array([1, 0, 0, 0], dtype=np.float32), atol=1e-5)

    def test_resolve_prefers_clean_onnx_when_registered(self):
        # A CoreML-hostile model resolves to its clean export (download), not the fastembed graph.
        fake_hub = type(sys)("huggingface_hub")
        fake_hub.hf_hub_download = lambda repo, fn, **k: f"/cache/{repo.replace('/', '_')}/{fn}"
        with patch.dict(self.ae.CLEAN_ONNX_SOURCES,
                        {"BAAI/bge-small-en-v1.5": ("Repo/clean", "onnx/m.onnx", "tokenizer.json")},
                        clear=False), \
             patch.dict(sys.modules, {"huggingface_hub": fake_hub}):
            got = self.ae._resolve_model_files("BAAI/bge-small-en-v1.5")
        self.assertEqual(got, (os.path.realpath("/cache/Repo_clean/onnx/m.onnx"),
                               "/cache/Repo_clean/tokenizer.json"))

    def test_resolve_clean_none_when_download_fails(self):
        # Offline + not cached → clean source unavailable → caller falls back to the resident path.
        fake_hub = type(sys)("huggingface_hub")
        def _fail(*a, **k): raise OSError("offline")
        fake_hub.hf_hub_download = _fail
        with patch.dict(sys.modules, {"huggingface_hub": fake_hub}):
            self.assertIsNone(self.ae._resolve_clean_onnx("BAAI/bge-small-en-v1.5"))

    def test_resolve_clean_none_for_unregistered_model(self):
        self.assertIsNone(self.ae._resolve_clean_onnx("Snowflake/snowflake-arctic-embed-xs"))

    def test_resolve_downloads_resident_model_on_cold_cache(self):
        # Regression: a model with no clean export (arctic) whose fastembed cache is COLD must
        # trigger a download then resolve — NOT return None (which silently drops docs to CPU
        # when a launcher like the dashboard spawns indexer.py without prewarm).
        with tempfile.TemporaryDirectory() as d:
            snap = Path(d) / "snapshots" / "abc"
            (snap / "onnx").mkdir(parents=True)
            (snap / "onnx" / "model.onnx").write_text("")
            (snap / "tokenizer.json").write_text("")
            calls = {"n": 0}
            def fake_repo(_name):
                calls["n"] += 1
                return None if calls["n"] == 1 else Path(d)  # cold first, warm after fetch
            with patch.object(self.ae, "_resolve_clean_onnx", return_value=None), \
                 patch.object(self.ae, "_model_repo_dir", side_effect=fake_repo), \
                 patch.object(self.ae, "_ensure_fastembed_model_cached") as ensure:
                got = self.ae._resolve_model_files("Snowflake/snowflake-arctic-embed-xs")
            ensure.assert_called_once()  # the cold-cache fetch ran
            self.assertIsNotNone(got)
            self.assertTrue(got[0].endswith("model.onnx"))
            self.assertTrue(got[1].endswith("tokenizer.json"))

    def test_resolve_none_when_resident_unavailable_after_fetch(self):
        # Still missing after the fetch attempt → None (caller falls back to fastembed); no loop.
        with patch.object(self.ae, "_resolve_clean_onnx", return_value=None), \
             patch.object(self.ae, "_model_repo_dir", return_value=None), \
             patch.object(self.ae, "_ensure_fastembed_model_cached") as ensure:
            self.assertIsNone(self.ae._resolve_model_files("Some/unknown-model"))
        ensure.assert_called_once()

    def test_offloads_to_gpu_threshold(self):
        # cpu/wall below threshold → GPU; at/above → CPU-bound (reject).
        hidden = np.zeros((self.ae.STATIC_BATCH, self.ae.STATIC_SEQ, 4), dtype=np.float32)
        hidden[:, 0, 0] = 1.0
        emb = _make_embedder(self.ae, hidden)
        with patch("time.time", side_effect=[0.0, 1.0]), patch("time.process_time", side_effect=[0.0, 0.05]):
            self.assertTrue(emb.offloads_to_gpu())   # cpu/wall = 0.05 → GPU
        with patch("time.time", side_effect=[0.0, 1.0]), patch("time.process_time", side_effect=[0.0, 4.0]):
            self.assertFalse(emb.offloads_to_gpu())  # cpu/wall = 4.0 → CPU-bound


class IndexerAccelDispatchTests(unittest.TestCase):
    """The indexer prefers the accel embedder when make_embedder returns one, else fastembed."""

    def setUp(self):
        spec = importlib.util.spec_from_file_location("indexer", SCRIPTS / "indexer.py")
        self.idx = importlib.util.module_from_spec(spec)
        sys.modules["indexer"] = self.idx
        spec.loader.exec_module(self.idx)
        self.idx._EMBEDDER_CACHE.clear()

    def test_uses_accel_when_available(self):
        sentinel = object()
        with patch.object(self.idx, "_onnx_providers", return_value=["CoreMLExecutionProvider", "CPUExecutionProvider"]), \
             patch.object(self.idx.accel_embedder, "make_embedder", return_value=sentinel):
            got = self.idx._get_embedder("Snowflake/snowflake-arctic-embed-xs")
        self.assertIs(got, sentinel)

    def test_falls_back_to_fastembed_when_accel_none(self):
        fake_te = object()
        fake_fastembed = type(sys)("fastembed")
        fake_fastembed.TextEmbedding = lambda **kw: fake_te
        with patch.object(self.idx, "_onnx_providers", return_value=["CPUExecutionProvider"]), \
             patch.object(self.idx.accel_embedder, "make_embedder", return_value=None), \
             patch.dict(sys.modules, {"fastembed": fake_fastembed}):
            got = self.idx._get_embedder("BAAI/bge-small-en-v1.5")
        self.assertIs(got, fake_te)


class HfDownloadCachedFirstTests(unittest.TestCase):
    """Wave 1p5cx: clean-ONNX / reranker resolution must hit the local cache first (no Hub
    round-trip / no unauthenticated-request warning on a warm cache), downloading only on a miss."""

    def setUp(self):
        self.accel = load_accel()

    def test_cached_first_no_network_when_present(self):
        calls = []

        def fake_dl(repo, filename, cache_dir=None, local_files_only=False):
            calls.append(local_files_only)
            return f"/cache/{filename}"

        fake_hub = types.SimpleNamespace(hf_hub_download=fake_dl)
        with patch.dict(sys.modules, {"huggingface_hub": fake_hub}):
            path = self.accel._hf_download_cached_first("repo", "model.onnx", "/cache")
        self.assertEqual(path, "/cache/model.onnx")
        self.assertEqual(calls, [True], "cached load only; no online attempt")

    def test_cached_first_falls_back_to_download_on_miss(self):
        calls = []

        def fake_dl(repo, filename, cache_dir=None, local_files_only=False):
            calls.append(local_files_only)
            if local_files_only:
                raise RuntimeError("LocalEntryNotFound")
            return f"/downloaded/{filename}"

        fake_hub = types.SimpleNamespace(hf_hub_download=fake_dl)
        with patch.dict(sys.modules, {"huggingface_hub": fake_hub}):
            path = self.accel._hf_download_cached_first("repo", "model.onnx", "/cache")
        self.assertEqual(path, "/downloaded/model.onnx")
        self.assertEqual(calls, [True, False], "cached-first then online download")


if __name__ == "__main__":
    unittest.main()
