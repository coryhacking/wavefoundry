"""Offline tests for the opt-in vendored-script verifier (wave 1zls7, change 1zltw).

Every test injects the fetch function or a fake response, or serves the registry from a
local loopback HTTP server with proxies neutralised, so the default suite never opens a
connection off this machine. The verifier itself downloads only when run directly.
"""
from __future__ import annotations

import base64
import contextlib
import hashlib
import http.server
import importlib
import io
import os
import shutil
import socket
import sys
import tarfile
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

SCRIPTS_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import verify_vendored_scripts as vvs  # noqa: E402
import vendored_integrity  # noqa: E402  the one read cap lives here (wave 1zyb2)

VENDOR_DIR = SCRIPTS_ROOT.parent / "dashboard" / "vendor"
URL = "https://registry.npmjs.org/demo/-/demo-1.0.0.tgz"
CONTENT = b"/* demo bundle */\nconsole.log(1);\n"


def _tarball(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _integrity(data: bytes) -> str:
    return "sha512-" + base64.b64encode(hashlib.sha512(data).digest()).decode("ascii")


def _readme(url: str, integrity: str, sha256: str, source: str = "package/dist/demo.js") -> str:
    return (
        "# Vendored\n\n"
        "| File | Package | Source in the tarball | Licence | SHA-256 |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| `demo/demo.js` | `demo@1.0.0` | `{source}` | MIT (`demo/LICENSE`) | `{sha256}` |\n\n"
        "## Registry integrity\n\n"
        "| Package | Tarball | `dist.integrity` |\n"
        "| --- | --- | --- |\n"
        f"| `demo@1.0.0` | `{url}` | `{integrity}` |\n"
    )


class VerifierLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="wf-vvs-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "demo").mkdir()
        (self.tmp / "demo" / "demo.js").write_bytes(CONTENT)
        self.tarball = _tarball({"package/dist/demo.js": CONTENT, "package/package.json": b"{}"})
        self.fetched: list[str] = []

    def _fetch(self, url: str) -> bytes:
        self.fetched.append(url)
        return self.tarball

    def _run(self, readme: str, fetch=None) -> tuple[int, str]:
        (self.tmp / "README.md").write_text(readme, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vvs.verify(self.tmp / "README.md", self.tmp, fetch=fetch or self._fetch)
        return code, out.getvalue()

    def _good_readme(self, **overrides: str) -> str:
        args = {
            "url": URL,
            "integrity": _integrity(self.tarball),
            "sha256": hashlib.sha256(CONTENT).hexdigest(),
        }
        args.update(overrides)
        return _readme(**args)

    def test_matching_data_passes_with_exit_zero(self):
        code, out = self._run(self._good_readme())
        self.assertEqual(code, 0, out)
        self.assertEqual(self.fetched, [URL])
        self.assertIn("ok", out)

    def test_tarball_integrity_mismatch_fails_with_exit_one(self):
        code, out = self._run(self._good_readme(integrity=_integrity(b"other bytes")))
        self.assertEqual(code, 1, out)
        self.assertIn("integrity mismatch", out)

    def test_vendored_file_sha256_mismatch_fails_with_exit_one(self):
        (self.tmp / "demo" / "demo.js").write_bytes(CONTENT + b"// tampered\n")
        code, out = self._run(self._good_readme())
        self.assertEqual(code, 1, out)
        self.assertIn("sha256 mismatch", out)

    def test_recorded_sha256_that_differs_from_the_member_fails(self):
        code, out = self._run(self._good_readme(sha256="0" * 64))
        self.assertEqual(code, 1, out)
        self.assertIn("sha256 mismatch", out)

    def test_missing_tarball_member_fails_with_exit_one(self):
        code, out = self._run(self._good_readme().replace("package/dist/demo.js", "package/dist/absent.js"))
        self.assertEqual(code, 1, out)
        self.assertIn("missing member", out)

    def test_non_registry_url_is_refused_before_any_fetch(self):
        for bad in ("http://registry.npmjs.org/demo/-/demo-1.0.0.tgz",
                    "https://registry.npmjs.org.evil.example/demo-1.0.0.tgz",
                    "https://evil.example/demo-1.0.0.tgz"):
            with self.subTest(url=bad):
                self.fetched.clear()
                code, out = self._run(self._good_readme(url=bad))
                self.assertEqual(code, 2, out)
                self.assertIn("demo@1.0.0: refused: non-registry URL", out)
                self.assertEqual(self.fetched, [])

    def test_unparseable_readme_exits_two(self):
        code, out = self._run("# nothing here\n")
        self.assertEqual(code, 2, out)
        self.assertIn("cannot parse", out)

    def test_download_failure_exits_two(self):
        def failing(url: str) -> bytes:
            raise vvs.FetchError("connection refused")
        code, out = self._run(self._good_readme(), fetch=failing)
        self.assertEqual(code, 2, out)
        self.assertIn("download failed", out)
        self.assertNotIn("refused:", out)

    def test_a_refused_download_is_labelled_refused_not_failed(self):
        """Delivery review N5: a refusal (a redirect off the registry, the
        size cap) prints its own label, distinct from a download failure."""
        def refusing(url: str) -> bytes:
            raise vvs.FetchRefused("redirect left the registry: https://evil.example/x")
        code, out = self._run(self._good_readme(), fetch=refusing)
        self.assertEqual(code, 2, out)
        self.assertIn("demo@1.0.0: refused: redirect left the registry", out)
        self.assertNotIn("download failed", out)

    def test_a_mismatch_outranks_an_unverifiable_package(self):
        """Delivery review N4: one package mismatching and another that could
        not be checked exits 1 (the mismatch), not 2."""
        other_url = "https://registry.npmjs.org/other/-/other-1.0.0.tgz"
        readme = self._good_readme(integrity=_integrity(b"other bytes")) + (
            f"| `other@1.0.0` | `{other_url}` | `{_integrity(b'x')}` |\n"
        )
        readme = readme.replace(
            "\n\n## Registry integrity",
            f"\n| `other/other.js` | `other@1.0.0` | `package/other.js` | MIT (`other/LICENSE`) | `{'0' * 64}` |"
            "\n\n## Registry integrity", 1)

        for error in (vvs.FetchError("connection refused"), vvs.FetchRefused("size cap")):
            def fetch(url: str, error=error) -> bytes:
                if url == other_url:
                    raise error
                return self.tarball
            with self.subTest(error=type(error).__name__):
                code, out = self._run(readme, fetch=fetch)
                self.assertIn("integrity mismatch", out)
                self.assertIn("other@1.0.0:", out)
                self.assertEqual(code, 1, out)


class _FakeResponse:
    def __init__(self, final_url: str, body: bytes) -> None:
        self._url = final_url
        self._body = io.BytesIO(body)

    def geturl(self) -> str:
        return self._url

    def read(self, n: int = -1) -> bytes:
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        return None


class DefaultFetchTests(unittest.TestCase):
    """The opener seam is ``vvs._open`` (wave 1zls7, change 1zodv); no test reaches the network."""

    def test_final_url_off_the_registry_is_refused_as_defence_in_depth(self):
        fake = _FakeResponse("https://evil.example/demo.tgz", b"x")
        with mock.patch.object(vvs, "_open", return_value=fake):
            with self.assertRaises(vvs.FetchError) as ctx:
                vvs.default_fetch(URL)
        self.assertIn("redirect left the registry", str(ctx.exception))
        self.assertIsInstance(ctx.exception, vvs.FetchRefused)

    def test_open_uses_the_checking_redirect_handler_and_the_timeout(self):
        opener = mock.Mock()
        with mock.patch.object(vvs.urllib.request, "build_opener", return_value=opener) as build:
            vvs._open(URL)
        self.assertIn(vvs._RegistryRedirectHandler, build.call_args.args)
        self.assertEqual(opener.open.call_args.kwargs.get("timeout"), vvs.REQUEST_TIMEOUT_SECONDS)

    def test_redirect_within_the_registry_is_accepted(self):
        fake = _FakeResponse("https://registry.npmjs.org/demo/-/demo-1.0.0.tgz?x=1", b"body")
        with mock.patch.object(vvs, "_open", return_value=fake):
            self.assertEqual(vvs.default_fetch(URL), b"body")

    def test_tarball_over_the_size_cap_is_refused(self):
        fake = _FakeResponse(URL, b"a" * 11)
        with mock.patch.object(vvs, "MAX_TARBALL_BYTES", 10), \
                mock.patch.object(vvs, "_open", return_value=fake):
            with self.assertRaises(vvs.FetchError) as ctx:
                vvs.default_fetch(URL)
        self.assertIn("size cap", str(ctx.exception))
        self.assertIsInstance(ctx.exception, vvs.FetchRefused)

    def test_a_network_error_is_a_failure_not_a_refusal(self):
        with mock.patch.object(vvs, "_open", side_effect=OSError("unreachable")):
            with self.assertRaises(vvs.FetchError) as ctx:
                vvs.default_fetch(URL)
        self.assertNotIsInstance(ctx.exception, vvs.FetchRefused)

    def test_default_fetch_refuses_a_non_registry_url_without_opening(self):
        with mock.patch.object(vvs, "_open") as opener, \
                mock.patch.object(vvs.urllib.request, "urlopen") as urlopen:
            with self.assertRaises(vvs.FetchError):
                vvs.default_fetch("https://evil.example/demo.tgz")
        opener.assert_not_called()
        urlopen.assert_not_called()


class _Server:
    """A loopback HTTP server that counts requests and serves ``routes``.

    ``routes`` maps a request path to ``(status, location_or_body)``: a 3xx status redirects to
    the location (a callable is called for it), any other status returns the body.
    """

    def __init__(self, routes: dict) -> None:
        self.routes = routes
        self.hits: list[str] = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                outer.hits.append(self.path)
                status, value = outer.routes.get(self.path, (404, b"missing"))
                if callable(value):
                    value = value()
                self.send_response(status)
                if 300 <= status < 400:
                    self.send_header("Location", value)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_header("Content-Length", str(len(value)))
                self.end_headers()
                self.wfile.write(value)

            def log_message(self, *args) -> None:
                return None

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.base = f"http://127.0.0.1:{self.httpd.server_address[1]}/"
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)


class RedirectBeforeFollowTests(unittest.TestCase):
    """Wave 1zls7, change 1zodv (AC-1): every redirect target is checked before it is followed,
    against real loopback servers. A second server stands for an off-registry host and counts
    every request it receives, so "never requested" is observed, not inferred."""

    def setUp(self) -> None:
        self.off = _Server({})
        self.addCleanup(self.off.close)
        self.registry = _Server({})
        self.addCleanup(self.registry.close)
        self.off.routes.update({
            "/back": (302, lambda: self.registry.base + "ok.tgz"),
            "/other.tgz": (200, b"off-registry body"),
        })
        self.registry.routes.update({
            "/ok.tgz": (200, b"tarball body"),
            "/on-relative": (302, "/ok.tgz"),
            "/on-absolute": (301, lambda: self.registry.base + "ok.tgz"),
            "/off": (302, lambda: self.off.base + "other.tgz"),
            "/off-then-back": (307, lambda: self.off.base + "back"),
        })
        # Neutralise proxies for the test only: the environment variables and the platform's
        # system proxy settings (macOS and Windows) that ``ProxyHandler`` reads.
        env = {k: v for k, v in os.environ.items() if not k.lower().endswith("_proxy")}
        patches = [
            mock.patch.dict(os.environ, env, clear=True),
            mock.patch.object(urllib.request, "getproxies", return_value={}),
            mock.patch.object(vvs, "REGISTRY_PREFIX", self.registry.base),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_an_on_registry_redirect_is_followed(self):
        for path in ("on-relative", "on-absolute"):
            with self.subTest(path=path):
                self.assertEqual(vvs.default_fetch(self.registry.base + path), b"tarball body")
        self.assertEqual(self.off.hits, [])

    def test_an_off_registry_redirect_is_refused_without_requesting_the_target(self):
        with self.assertRaises(vvs.FetchRefused) as ctx:
            vvs.default_fetch(self.registry.base + "off")
        self.assertIn("redirect left the registry", str(ctx.exception))
        self.assertIn(self.off.base + "other.tgz", str(ctx.exception))
        self.assertEqual(self.off.hits, [])

    def test_a_chain_that_leaves_the_registry_and_returns_is_refused(self):
        with self.assertRaises(vvs.FetchRefused):
            vvs.default_fetch(self.registry.base + "off-then-back")
        self.assertEqual(self.off.hits, [])
        self.assertNotIn("/ok.tgz", self.registry.hits)

    def test_the_refusal_reads_the_live_registry_predicate(self):
        """The handler calls the module's ``_is_registry_url``, not a captured copy."""
        calls: list[str] = []
        real = vvs._is_registry_url

        def spy(url: str) -> bool:
            calls.append(url)
            return real(url)

        with mock.patch.object(vvs, "_is_registry_url", spy):
            with self.assertRaises(vvs.FetchRefused):
                vvs.default_fetch(self.registry.base + "off")
        self.assertIn(self.off.base + "other.tgz", calls)

    def test_the_verifier_prints_refused_and_exits_two(self):
        tmp = Path(tempfile.mkdtemp(prefix="wf-vvs-redirect-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "demo").mkdir()
        (tmp / "demo" / "demo.js").write_bytes(CONTENT)
        readme = _readme(self.registry.base + "off", _integrity(b"x"), hashlib.sha256(CONTENT).hexdigest())
        (tmp / "README.md").write_text(readme, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vvs.verify(tmp / "README.md", tmp)
        self.assertEqual(code, 2, out.getvalue())
        self.assertIn("demo@1.0.0: refused: redirect left the registry", out.getvalue())
        self.assertEqual(self.off.hits, [])


class MalformedRowTests(unittest.TestCase):
    """Wave 1zls7, change 1zodv (AC-2): a data row that does not fully match its table's
    pattern makes the run exit 2 and names the line, instead of being skipped."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="wf-vvs-rows-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "demo").mkdir()
        (self.tmp / "demo" / "demo.js").write_bytes(CONTENT)
        self.tarball = _tarball({"package/dist/demo.js": CONTENT})
        self.sha = hashlib.sha256(CONTENT).hexdigest()
        self.good = _readme(URL, _integrity(self.tarball), self.sha)

    def _run(self, readme: str) -> tuple[int, str]:
        (self.tmp / "README.md").write_text(readme, encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vvs.verify(self.tmp / "README.md", self.tmp, fetch=lambda url: self.tarball)
        return code, out.getvalue()

    def test_the_valid_readme_passes(self):
        code, out = self._run(self.good)
        self.assertEqual(code, 0, out)

    def test_a_malformed_file_row_among_valid_rows_exits_two_and_names_it(self):
        anchor = "\n\n## Registry integrity"
        cases = {
            "shortened sha256": f"| `demo/b.js` | `demo@1.0.0` | `package/b.js` | MIT | `{self.sha[:63]}` |",
            "path without backticks": f"| demo/c.js | `demo@1.0.0` | `package/c.js` | MIT | `{self.sha}` |",
        }
        for label, row in cases.items():
            with self.subTest(case=label):
                readme = self.good.replace(anchor, "\n" + row + anchor, 1)
                code, out = self._run(readme)
                self.assertEqual(code, 2, out)
                self.assertIn("line 6: malformed file table row", out)
                # The row is named by line number, never echoed (wave 1zyb2).
                self.assertNotIn(row, out)

    def test_a_malformed_registry_row_exits_two_and_names_it(self):
        row = "| `demo@1.0.0` | https://registry.npmjs.org/demo/-/demo-1.0.0.tgz | `sha512-abc` |"
        code, out = self._run(self.good + row + "\n")
        self.assertEqual(code, 2, out)
        self.assertIn("malformed registry table row", out)
        self.assertRegex(out, r"line \d+: malformed registry table row")
        self.assertNotIn(row, out)

    def test_each_table_header_must_appear_exactly_once(self):
        missing = self.good.replace("| File | Package | Source in the tarball | Licence | SHA-256 |",
                                    "| File | Package | Source | Licence | SHA-256 |")
        doubled = self.good + "\n| Package | Tarball | `dist.integrity` |\n| --- | --- | --- |\n"
        for label, readme in (("missing", missing), ("doubled", doubled)):
            with self.subTest(case=label):
                code, out = self._run(readme)
                self.assertEqual(code, 2, out)
                self.assertIn("table header", out)

    def test_the_table_ends_at_the_first_line_not_starting_with_a_pipe(self):
        """A line that leaves the table ends it; prose after it is not read as rows."""
        code, out = self._run(self.good + "\nProse after the table.\n\n## Next\n\n| other | table |\n")
        self.assertEqual(code, 0, out)

    def _shipped_variant(self, edit) -> tuple[int, str]:
        """Run the verifier over an edited copy of the shipped README; parsing fails
        first, so no fetch is attempted (the fetch would raise)."""
        lines = (VENDOR_DIR / "README.md").read_text(encoding="utf-8").splitlines(keepends=True)
        first = next(i for i, line in enumerate(lines) if line.startswith("| `react/"))
        (self.tmp / "README.md").write_text("".join(edit(lines, first)), encoding="utf-8")

        def no_fetch(url: str) -> bytes:
            raise AssertionError(f"fetched {url}")

        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vvs.verify(self.tmp / "README.md", VENDOR_DIR, fetch=no_fetch)
        return code, out.getvalue()

    def test_an_indented_row_exits_two_and_names_it(self):
        """Review F1: a row indented one to three spaces is refused, not dropped."""
        for indent in (" ", "   "):
            with self.subTest(indent=len(indent)):
                def edit(lines, first):
                    lines[first + 1] = indent + lines[first + 1]
                    return lines
                code, out = self._shipped_variant(edit)
                self.assertEqual(code, 2, out)
                self.assertRegex(out, r"line \d+: indented file table row")
                self.assertNotIn("`react-dom/react-dom.production.min.js`", out)

    def test_a_last_row_without_its_leading_pipe_exits_two(self):
        """Review N1: the leading pipe is optional in a rendered table, so a last row
        without it is refused, not dropped."""
        def edit(lines, first):
            lines[first + 2] = lines[first + 2].lstrip("| ")
            return lines
        code, out = self._shipped_variant(edit)
        self.assertEqual(code, 2, out)
        self.assertRegex(out, r"line \d+: malformed file table row")
        self.assertNotIn("elk.bundled.js", out)

    def test_rows_after_a_blank_line_exit_two_and_name_the_line(self):
        """Review F1: a blank line inside a table does not end it silently."""
        def edit(lines, first):
            lines.insert(first + 1, "\n")
            return lines
        code, out = self._shipped_variant(edit)
        self.assertEqual(code, 2, out)
        self.assertRegex(out, r"line \d+: file table row after the end of the table")
        self.assertNotIn("`react-dom/react-dom.production.min.js`", out)

    def test_registry_rows_after_a_blank_line_are_refused(self):
        def edit(lines, first):
            index = next(i for i, line in enumerate(lines) if line.startswith("| `react-dom@"))
            lines.insert(index, "\n")
            return lines
        code, out = self._shipped_variant(edit)
        self.assertEqual(code, 2, out)
        self.assertIn("registry table row after the end of the table", out)


class ShippedReadmeTests(unittest.TestCase):
    def test_readme_tables_parse_into_the_three_pinned_packages_and_files(self):
        files, registry = vvs.parse_readme((VENDOR_DIR / "README.md").read_text(encoding="utf-8"))
        self.assertEqual(sorted(registry), ["elkjs@0.10.0", "react-dom@18.3.1", "react@18.3.1"])
        self.assertEqual(
            sorted((f.path, f.package) for f in files),
            [
                ("elkjs/elk.bundled.js", "elkjs@0.10.0"),
                ("react-dom/react-dom.production.min.js", "react-dom@18.3.1"),
                ("react/react.production.min.js", "react@18.3.1"),
            ],
        )
        for package, entry in registry.items():
            name, version = package.rsplit("@", 1)
            self.assertEqual(entry.url, f"https://registry.npmjs.org/{name}/-/{name}-{version}.tgz")
            self.assertTrue(entry.integrity.startswith("sha512-"))
        for f in files:
            self.assertEqual(hashlib.sha256((VENDOR_DIR / f.path).read_bytes()).hexdigest(), f.sha256)

    def test_import_performs_no_request(self):
        def no_network(*args, **kwargs):
            raise AssertionError("network opened at import")
        with mock.patch("urllib.request.urlopen", side_effect=no_network), \
                mock.patch.object(socket, "create_connection", side_effect=no_network), \
                mock.patch.object(socket.socket, "connect", side_effect=no_network):
            importlib.reload(vvs)


class OfflineCheckTests(unittest.TestCase):
    """The offline comparison (wave 1zv8c, change 1zv8a): hashes only, never a request."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="wf-vvs-off-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "demo").mkdir()
        (self.tmp / "demo" / "demo.js").write_bytes(CONTENT)
        tarball = _tarball({"package/dist/demo.js": CONTENT})
        (self.tmp / "README.md").write_text(
            _readme(URL, _integrity(tarball), hashlib.sha256(CONTENT).hexdigest()), encoding="utf-8")

    def _offline(self, vendor_dir: Path | None = None) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vvs.verify_offline(vendor_dir or self.tmp)
        return code, out.getvalue()

    def test_real_vendored_files_match_their_pinned_hashes(self):
        self.assertEqual(vvs.offline_problems(VENDOR_DIR), [])

    def test_every_real_vendored_script_is_listed_in_the_file_table(self):
        self.assertEqual(vvs.unlisted_scripts(VENDOR_DIR), [])

    def test_matching_files_exit_zero(self):
        code, out = self._offline()
        self.assertEqual(code, 0, out)

    def test_changed_byte_exits_one_naming_the_file(self):
        (self.tmp / "demo" / "demo.js").write_bytes(CONTENT[:-2] + b"X\n")
        code, out = self._offline()
        self.assertEqual(code, 1, out)
        self.assertIn("demo/demo.js", out)
        self.assertIn("sha256 mismatch", out)

    def test_missing_file_exits_one_naming_the_file(self):
        (self.tmp / "demo" / "demo.js").unlink()
        code, out = self._offline()
        self.assertEqual(code, 1, out)
        self.assertIn("demo/demo.js", out)
        self.assertIn("missing", out)

    def test_unparseable_readme_exits_two(self):
        (self.tmp / "README.md").write_text("# nothing here\n", encoding="utf-8")
        code, out = self._offline()
        self.assertEqual(code, 2, out)
        self.assertIn("cannot parse", out)

    def test_absent_readme_exits_two(self):
        (self.tmp / "README.md").unlink()
        code, _out = self._offline()
        self.assertEqual(code, 2)

    def test_unlisted_js_is_reported_recursively(self):
        (self.tmp / "extra" / "deep").mkdir(parents=True)
        (self.tmp / "extra" / "deep" / "stray.js").write_bytes(b"1")
        self.assertEqual(vvs.unlisted_scripts(self.tmp), ["extra/deep/stray.js"])

    def test_unlisted_mjs_and_cjs_are_reported_in_any_letter_case(self):
        (self.tmp / "extra").mkdir()
        for name in ("a.mjs", "b.cjs", "C.MJS", "D.Cjs"):
            (self.tmp / "extra" / name).write_bytes(b"1")
        self.assertEqual(
            vvs.unlisted_scripts(self.tmp),
            ["extra/C.MJS", "extra/D.Cjs", "extra/a.mjs", "extra/b.cjs"])

    def test_dotfiles_readme_and_licences_are_ignored(self):
        (self.tmp / ".DS_Store").write_bytes(b"x")
        (self.tmp / "demo" / ".DS_Store").write_bytes(b"x")
        (self.tmp / "demo" / "LICENSE").write_text("MIT", encoding="utf-8")
        (self.tmp / "demo" / "LICENSE.md").write_text("MIT", encoding="utf-8")
        self.assertEqual(vvs.unlisted_scripts(self.tmp), [])

    def test_offline_mode_makes_no_request(self):
        def no_network(*args, **kwargs):
            raise AssertionError("offline mode must not use the network")
        with mock.patch.object(vvs, "default_fetch", side_effect=no_network), \
                mock.patch.object(vvs, "_open", side_effect=no_network), \
                mock.patch.object(socket, "socket", side_effect=no_network), \
                mock.patch.object(vvs, "DEFAULT_VENDOR_DIR", self.tmp):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = vvs.main(["--offline"])
        self.assertEqual(code, 0, out.getvalue())


def _row_readme(rel: str, sha256: str) -> str:
    """A README whose single file row names ``rel`` (any spelling) with ``sha256``."""
    tarball = _tarball({"package/dist/demo.js": CONTENT})
    return (
        "# Vendored\n\n"
        "| File | Package | Source in the tarball | Licence | SHA-256 |\n"
        "| --- | --- | --- | --- | --- |\n"
        f"| `{rel}` | `demo@1.0.0` | `package/dist/demo.js` | MIT (`demo/LICENSE`) | `{sha256}` |\n\n"
        "## Registry integrity\n\n"
        "| Package | Tarball | `dist.integrity` |\n"
        "| --- | --- | --- |\n"
        f"| `demo@1.0.0` | `{URL}` | `{_integrity(tarball)}` |\n"
    )


_SECRET = b"outside-the-vendor-folder\n"
_SECRET_SHA = hashlib.sha256(_SECRET).hexdigest()


class ConfinedVendoredReadTests(unittest.TestCase):
    """Wave 1zxo0 (1zxns): every vendored read is confined to the vendor folder, refuses
    links and non-regular files, and is capped; the README goes through the same checks."""

    def setUp(self) -> None:
        self.base = Path(tempfile.mkdtemp(prefix="wf-vvs-conf-"))
        self.addCleanup(shutil.rmtree, self.base, ignore_errors=True)
        self.vendor = self.base / "vendor"
        (self.vendor / "demo").mkdir(parents=True)
        (self.vendor / "demo" / "demo.js").write_bytes(CONTENT)
        self.outside = self.base / "secret.txt"
        self.outside.write_bytes(_SECRET)
        self.opened: list[str] = []

    def _write_readme(self, rel: str, sha256: str = _SECRET_SHA) -> None:
        (self.vendor / "README.md").write_text(_row_readme(rel, sha256), encoding="utf-8")

    def _spy_open(self):
        real_open = os.open
        real_builtin = open

        def spy(path, *args, **kwargs):
            self.opened.append(os.fspath(path))
            return real_open(path, *args, **kwargs)

        def spy_builtin(path, *args, **kwargs):
            if isinstance(path, (str, os.PathLike)):
                self.opened.append(os.fspath(path))
            return real_builtin(path, *args, **kwargs)

        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(vvs.os, "open", side_effect=spy))
        stack.enter_context(mock.patch("builtins.open", side_effect=spy_builtin))
        return stack

    def _assert_refused_unread(self, rel: str, label: str | None = None) -> None:
        self._write_readme(rel)
        with self._spy_open():
            problems = vvs.offline_problems(self.vendor)
        self.assertEqual(len(problems), 1, problems)
        line = problems[0]
        label = rel if label is None else label
        self.assertTrue(line.startswith(f"{label}: "), line)
        if label != rel:
            # A row refused for its spelling is named by number, never echoed.
            self.assertNotIn(rel, line)
        # Nothing after the label carries an absolute path.
        tail = line[len(label):]
        self.assertNotIn(str(self.base), tail)
        self.assertNotIn(str(self.base.resolve()), tail)
        # Nothing but the README was opened, and no digest of anything else is printed.
        self.assertEqual([Path(o).name for o in self.opened], ["README.md"], self.opened)
        self.assertNotIn("sha256 mismatch", line)
        computed = [token for token in line.replace(":", " ").split() if len(token) == 64]
        self.assertEqual(computed, [], line)

    def test_lexical_row_classes_are_refused_unread(self):
        for rel in (
            str(self.outside),
            "/etc/hosts",
            "C:/x/y.js",
            "c:demo.js",
            "demo\\demo.js",
            "demo//demo.js",
            "./demo/demo.js",
            "demo/./demo.js",
            "../secret.txt",
            "demo/../../secret.txt",
            "demo/",
            "demo/de\x07mo.js",
            "demo/\x1b[2Jdemo.js",
            "demo/de\tmo.js",
        ):
            with self.subTest(rel=rel):
                self.opened.clear()
                self._assert_refused_unread(rel, label="row 1")

    def test_a_lexically_refused_row_is_named_by_its_table_position(self):
        good_sha = hashlib.sha256(CONTENT).hexdigest()
        readme = _row_readme("demo/demo.js", good_sha)
        bad_row = (f"| `{self.outside}` | `demo@1.0.0` | `package/dist/demo.js` | MIT (`demo/LICENSE`) | "
                   f"`{_SECRET_SHA}` |\n")
        good_row = next(line for line in readme.splitlines(keepends=True) if line.startswith("| `demo/demo.js`"))
        (self.vendor / "README.md").write_text(readme.replace(good_row, good_row + bad_row), encoding="utf-8")
        problems = vvs.offline_problems(self.vendor)
        self.assertEqual(len(problems), 1, problems)
        self.assertTrue(problems[0].startswith("row 2: "), problems)
        self.assertNotIn(str(self.outside), problems[0])

    def test_a_row_without_a_registry_entry_is_not_echoed_when_refused(self):
        readme = _row_readme(str(self.outside), _SECRET_SHA).replace("`demo@1.0.0` | `package", "`other@1.0.0` | `package")
        (self.vendor / "README.md").write_text(readme, encoding="utf-8")
        with self.assertRaises(vvs.ReadmeError) as ctx:
            vvs.offline_problems(self.vendor)
        self.assertIn("row 1:", str(ctx.exception))
        self.assertNotIn(str(self.outside), str(ctx.exception))

    @unittest.skipIf(os.name == "nt", "symlink creation needs privileges on Windows")
    def test_a_link_component_is_refused_unread(self):
        (self.vendor / "leaf.js").symlink_to(self.outside)
        (self.vendor / "dirlink").symlink_to(self.base, target_is_directory=True)
        (self.vendor / "inner.js").symlink_to(self.vendor / "demo" / "demo.js")
        # A directory link that stays inside the vendor folder is still a link component.
        (self.vendor / "alias").symlink_to(self.vendor / "demo", target_is_directory=True)
        for rel in ("leaf.js", "dirlink/secret.txt", "inner.js", "alias/demo.js"):
            with self.subTest(rel=rel):
                self.opened.clear()
                self._assert_refused_unread(rel)

    def test_a_path_resolving_outside_the_vendor_folder_is_refused(self):
        # No link component and no `..`: simulate a resolution that leaves the folder.
        self._write_readme("demo/demo.js", hashlib.sha256(CONTENT).hexdigest())
        real_resolve = Path.resolve

        def fake_resolve(path, *args, **kwargs):
            if path.name == "demo.js":
                return real_resolve(self.outside)
            return real_resolve(path, *args, **kwargs)

        with mock.patch.object(Path, "resolve", fake_resolve), self._spy_open():
            problems = vvs.offline_problems(self.vendor)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("outside the vendor folder", problems[0])
        self.assertEqual([Path(o).name for o in self.opened], ["README.md"])

    def test_a_directory_row_is_refused_unread(self):
        (self.vendor / "adir.js").mkdir()
        self._assert_refused_unread("adir.js")

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
    def test_a_fifo_row_is_refused_without_blocking(self):
        os.mkfifo(self.vendor / "pipe.js")
        self._assert_refused_unread("pipe.js")

    def test_an_oversized_row_is_refused_unread(self):
        (self.vendor / "big.js").write_bytes(b"x" * 4097)
        with mock.patch.object(vendored_integrity, "MAX_VENDORED_FILE_BYTES", 4096):
            self._assert_refused_unread("big.js")

    def test_growth_past_the_cap_after_lstat_is_refused_by_the_read_count(self):
        # lstat sees a small file; the read then returns more than the cap.
        target = self.vendor / "demo" / "demo.js"
        body = b"y" * 4097
        target.write_bytes(body)
        self._write_readme("demo/demo.js", hashlib.sha256(body).hexdigest())
        real_lstat = os.lstat

        def small_lstat(path, *args, **kwargs):
            result = real_lstat(path, *args, **kwargs)
            if Path(path) == target:
                values = list(result)
                values[6] = 1  # st_size
                return os.stat_result(values)
            return result

        with mock.patch.object(vendored_integrity, "MAX_VENDORED_FILE_BYTES", 4096), \
                mock.patch.object(vvs.os, "lstat", side_effect=small_lstat):
            problems = vvs.offline_problems(self.vendor)
        self.assertEqual(len(problems), 1, problems)
        self.assertIn("exceeds the size cap", problems[0])

    def test_the_read_requests_at_most_cap_plus_one_bytes(self):
        target = self.vendor / "demo" / "demo.js"
        requested: list[object] = []
        real_fdopen = os.fdopen
        real_builtin = open

        class _Recording:
            def __init__(self, handle):
                self._handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self._handle.close()

            def fileno(self):
                return self._handle.fileno()

            def read(self, *args):
                requested.append(args)
                return self._handle.read(*args)

        def fdopen(fd, *args, **kwargs):
            return _Recording(real_fdopen(fd, *args, **kwargs))

        def builtin(path, *args, **kwargs):
            return _Recording(real_builtin(path, *args, **kwargs))

        with mock.patch.object(vendored_integrity, "MAX_VENDORED_FILE_BYTES", 4096), \
                mock.patch.object(vvs.os, "fdopen", side_effect=fdopen), \
                mock.patch("builtins.open", side_effect=builtin):
            data = vvs._read_regular(target)
        self.assertEqual(data, CONTENT)
        self.assertEqual(requested, [(4097,)])

    def test_verify_applies_the_same_checks_to_its_vendored_read(self):
        tarball = _tarball({"package/dist/demo.js": CONTENT})
        for rel, label in (("../secret.txt", "row 1"), (str(self.outside), "row 1"),
                           ("demo\\demo.js", "row 1"), ("demo/\x07.js", "row 1"), ("adir.js", "adir.js")):
            with self.subTest(rel=rel):
                (self.vendor / "adir.js").mkdir(exist_ok=True)
                self._write_readme(rel)
                self.opened.clear()
                out = io.StringIO()
                with contextlib.redirect_stdout(out), self._spy_open():
                    code = vvs.verify(self.vendor / "README.md", self.vendor, fetch=lambda url: tarball)
                text = out.getvalue()
                self.assertEqual(code, 1, text)
                self.assertIn(f"{label}: cannot read vendored file", text)
                if label != rel:
                    self.assertNotIn(rel, text)
                self.assertNotIn(_SECRET_SHA, text)
                self.assertNotIn(str(self.base.resolve()), text)
                self.assertNotIn(str(self.base), text)
                self.assertEqual([Path(o).name for o in self.opened], ["README.md"])

    def _readme_refusals(self) -> list[str]:
        messages: list[str] = []
        with self.assertRaises(vvs.ReadmeError) as ctx:
            vvs.offline_problems(self.vendor)
        messages.append(str(ctx.exception))
        with self.assertRaises(vvs.ReadmeError) as ctx:
            vvs.unlisted_scripts(self.vendor)
        messages.append(str(ctx.exception))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vvs.verify(self.vendor / "README.md", self.vendor, fetch=lambda url: b"")
        self.assertEqual(code, 2)
        messages.append(out.getvalue())
        for message in messages:
            self.assertIn("README.md", message)
            self.assertNotIn(str(self.base), message)
            self.assertNotIn(str(self.base.resolve()), message)
        return messages

    def test_a_directory_readme_is_refused_in_all_three_readers(self):
        (self.vendor / "README.md").mkdir()
        for message in self._readme_refusals():
            self.assertIn("not a regular file", message)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFOs are POSIX only")
    def test_a_fifo_readme_is_refused_without_blocking(self):
        os.mkfifo(self.vendor / "README.md")
        for message in self._readme_refusals():
            self.assertIn("not a regular file", message)

    def test_an_oversized_readme_is_refused_in_all_three_readers(self):
        self._write_readme("demo/demo.js", hashlib.sha256(CONTENT).hexdigest())
        with mock.patch.object(vendored_integrity, "MAX_VENDORED_FILE_BYTES", 16):
            for message in self._readme_refusals():
                self.assertIn("exceeds the size cap", message)

    def test_an_unreadable_readme_message_carries_no_absolute_path(self):
        (self.vendor / "README.md").write_bytes(b"\xff\xfe not utf-8")
        for message in self._readme_refusals():
            self.assertIn("UnicodeDecodeError", message)

    def test_verify_reads_the_cap_from_the_shipped_module(self):
        # The network verifier's vendored read honors the one cap in vendored_integrity.
        self._write_readme("demo/demo.js", hashlib.sha256(CONTENT).hexdigest())
        tarball = _tarball({"package/dist/demo.js": CONTENT})
        out = io.StringIO()
        # The README is larger than the patched cap, so it is parsed before patching.
        files, registry = vvs._read_readme(self.vendor / "README.md", self.vendor)
        with contextlib.redirect_stdout(out), \
                mock.patch.object(vvs, "_read_readme", return_value=(files, registry)), \
                mock.patch.object(vendored_integrity, "MAX_VENDORED_FILE_BYTES", len(CONTENT) - 1):
            code = vvs.verify(self.vendor / "README.md", self.vendor, fetch=lambda url: tarball)
        text = out.getvalue()
        self.assertEqual(code, 1, text)
        self.assertIn("demo/demo.js: cannot read vendored file: exceeds the size cap", text)

    def test_the_cap_constant_equals_the_tarball_cap(self):
        self.assertEqual(vendored_integrity.MAX_VENDORED_FILE_BYTES, vvs.MAX_TARBALL_BYTES)

    def test_the_real_vendor_folder_still_passes(self):
        self.assertEqual(vvs.offline_problems(VENDOR_DIR), [])

    def test_build_pack_refuses_a_tree_with_a_bad_row(self):
        import build_pack

        framework = self.base / "framework"
        vendor = framework / "dashboard" / "vendor"
        vendor.mkdir(parents=True)
        (vendor / "README.md").write_text(_row_readme("../../../secret.txt", _SECRET_SHA), encoding="utf-8")
        with self.assertRaises(SystemExit) as ctx:
            build_pack._check_vendored_scripts(framework)
        message = str(ctx.exception.code)
        self.assertIn("row 1: ", message)
        self.assertNotIn("../../../secret.txt", message)
        self.assertNotIn(str(self.base), message)


if __name__ == "__main__":
    unittest.main()
