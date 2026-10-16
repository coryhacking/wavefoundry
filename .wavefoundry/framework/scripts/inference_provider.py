"""Shared inference selection for serving, setup and indexing.

Adapters are trusted distribution code. Deadlines are transport obligations,
not a Python sandbox; late results are rejected, never retried elsewhere.
"""
from __future__ import annotations

import math
import inspect
from pathlib import Path
import re
import sys
import time
import types

import inference_profile
import tensorwell_client as tc

_cached_provider = None
_cached_key = None
_cache_until = 0.0
_declaration_generation = None
_declaration_helpers = frozenset()


class ProviderUnavailable(RuntimeError):
    def __init__(self):
        super().__init__("Declared inference provider is unavailable or incompatible; check the distribution adapter and index compatibility.")


def mode():
    global _declaration_generation, _declaration_helpers
    value = inference_profile.PROVIDER
    module = inference_profile.ADAPTER_MODULE
    if value not in ("tensorwell", "local", "extension") or not isinstance(module, str):
        raise ProviderUnavailable()
    if value != "extension" and module:
        raise ProviderUnavailable()
    if value == "extension":
        if _declaration_generation != tc._generation:
            import mcp_tool_extensions as extensions
            valid = (isinstance(extensions.EXTENSION_MODULES, tuple)
                     and not extensions._module_name_problems("module", extensions.EXTENSION_MODULES, set())
                     and not extensions._helper_module_problems(set(extensions.EXTENSION_MODULES)))
            _declaration_helpers = frozenset(extensions.EXTENSION_HELPER_MODULES) if valid else frozenset()
            _declaration_generation = tc._generation
        if module not in _declaration_helpers:
            raise ProviderUnavailable()
    return value


def _observe(backend, reason, state):
    with tc.process_hold_guard():
        tc._status.update(backend=backend, reason=reason, profiles=[])
        tc._observe_availability(state, reason)


def _descriptor(task):
    import model_bundle
    return {"model": tc.EMBEDDING_MODEL if task == "embedding" else tc.RERANKER_MODEL,
            "task": task, "precision_class": "full",
            "compatibility_fingerprint": model_bundle.EMBEDDING_COMPATIBILITY_FINGERPRINT,
            **({"dimensions": 384} if task == "embedding" else {"score_type": "raw_logits"})}


def _load_provider():
    global _cached_provider, _cached_key, _cache_until
    deadline = time.monotonic() + tc.DISCOVERY_SECONDS
    try:
        name = inference_profile.ADAPTER_MODULE
        key = (name, id(sys.modules.get(name)), tc._generation)
        if _cached_provider is not None and key == _cached_key and time.monotonic() < _cache_until:
            return _cached_provider
        path = Path(__file__).resolve().parent / (name + ".py")
        if (path.name not in [p.name for p in path.parent.iterdir()]
                or path.is_symlink() or not path.is_file() or path.resolve().parent != Path(__file__).resolve().parent):
            raise ValueError
        module = sys.modules.get(name)
        if module is None:
            module = types.ModuleType(name)
            module.__file__ = str(path)
            module.__wf_extension__ = True
            sys.modules[name] = module
            try:
                exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
            except BaseException:
                sys.modules.pop(name, None)
                raise
        elif Path(module.__file__).resolve() != path.resolve():
            raise ValueError
        result = module.create_provider(deadline=deadline)
        tc._remaining(deadline)
        if not isinstance(result, dict):
            raise ValueError
        label = result.get("provider")
        if not isinstance(label, str) or re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", label) is None or label in {"tensorwell", "in_process"}:
            raise ValueError
        for task, operation in (("embedding", "embed"), ("reranking", "rerank")):
            callback = result.get(operation)
            if (result.get(task) != _descriptor(task) or not callable(callback)
                    or inspect.iscoroutinefunction(callback) or inspect.isasyncgenfunction(callback)):
                raise ValueError
            if task == "embedding":
                inspect.signature(callback).bind([], role="document", deadline=deadline)
            else:
                inspect.signature(callback).bind("", [], deadline=deadline)
        result = {**result, "embedding": dict(result["embedding"]), "reranking": dict(result["reranking"])}
        _observe(label, "declared_provider", "ready_compatible")
        _cached_provider = result
        _cached_key = (name, id(module), tc._generation)
        _cache_until = time.monotonic() + tc.CACHE_SECONDS
        return result
    except Exception:
        _cached_provider = None
        _observe("extension", "provider_unavailable", "unavailable")
        raise ProviderUnavailable() from None


class _Adapter:
    is_service_provider = True
    batch_size = 40

    def __init__(self, provider, task):
        self._provider = provider
        self._task = task
        self.provider_label = provider["provider"]
        self.model_name = provider[task]["model"]
        self.precision_class = provider[task]["precision_class"]
        self._generation = tc._generation
        self._module_name = inference_profile.ADAPTER_MODULE

    def _operation(self, texts, *, role="document", query=None):
        try:
            if (self._generation != tc._generation or inference_profile.PROVIDER != "extension"
                    or self._module_name != inference_profile.ADAPTER_MODULE
                    or (self._task == "reranking" and tc._truthy("WAVEFOUNDRY_DISABLE_RERANKER"))):
                raise ValueError
            values = list(texts)
            for text in values:
                tc._text(text)
            if query is not None:
                tc._text(query)
            deadline = time.monotonic() + tc.INFERENCE_SECONDS
            response = (self._provider["embed"](values, role=role, deadline=deadline)
                        if self._task == "embedding" else
                        self._provider["rerank"](query, values, deadline=deadline))
            tc._remaining(deadline)
            if self._generation != tc._generation:
                raise ValueError
            if not isinstance(response, dict) or response.get("descriptor") != _descriptor(self._task):
                raise ValueError
            data = response.get("results")
            if not isinstance(data, list) or len(data) != len(values):
                raise ValueError
            for value in data:
                numbers = value if self._task == "embedding" else [value]
                if (not isinstance(numbers, list) or (self._task == "embedding" and len(numbers) != 384)
                        or any(type(n) not in (int, float) or not math.isfinite(n) or abs(n) > tc.FLOAT32_MAX for n in numbers)):
                    raise ValueError
            return data
        except Exception:
            _observe("extension", "inference_unavailable", "unavailable")
            raise ProviderUnavailable() from None

    def embed(self, texts, batch_size=256, **kwargs):
        return iter(self._operation(texts))

    def embed_query(self, text):
        return self._operation([text], role="query")[0]

    def rerank(self, query, texts):
        return self._operation(texts, query=query)


def extension_precision(model_name):
    if mode() != "extension":
        return None
    provider = _load_provider()
    if provider["embedding"]["model"] != model_name:
        raise ProviderUnavailable()
    return provider["embedding"]["precision_class"]


def _select(task, model_name, precision_class="full", diagnostic=None):
    selected = mode()
    if task == "reranking" and tc._truthy("WAVEFOUNDRY_DISABLE_RERANKER"):
        return tc._selection_result(None, "reranker_disabled", diagnostic)
    if selected == "tensorwell":
        return (tc.select_embedder(model_name, precision_class, diagnostic=diagnostic)
                if task == "embedding" else tc.select_reranker(model_name, diagnostic=diagnostic))
    if selected == "local":
        _observe("local", "provider_policy", "policy_disabled")
        return tc._selection_result(None, "provider_policy", diagnostic)
    provider = _load_provider()
    if provider[task]["model"] != model_name or (task == "embedding" and provider[task]["precision_class"] != precision_class):
        _observe("extension", "index_precision_mismatch", "incompatible")
        raise ProviderUnavailable()
    return tc._selection_result(_Adapter(provider, task), "declared_provider", diagnostic)


def select_embedder(model_name, precision_class="full", *, diagnostic=None):
    return _select("embedding", model_name, precision_class, diagnostic)


def select_reranker(model_name, *, diagnostic=None):
    return _select("reranking", model_name, diagnostic=diagnostic)


def start_background(root):
    if mode() == "tensorwell":
        tc.start_background(root)
