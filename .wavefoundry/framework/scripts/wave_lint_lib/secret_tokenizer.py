"""Bounded, offline Betterleaks token filters; provenance in scan/NOTICE.md."""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import math
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parents[2] / "scan"
UPSTREAM_COMMIT = "8f376ff9c31ed5309ac448fe601c5dd21b376155"
_EXPECTED = {
    "cl100k_base.tiktoken.gz": ("4414e3fb432aa5c4a9a19d5b91fe5ab27fecb8f5347208696a01bc507e093696", "223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7", 100256),
    "words.txt.gz": ("d4dd5530d98f4ff343864ed71cfc0064abeae34e4f078edc0b46590c2da8fb47", "e811a9be4d82bef94c0134d66ab7de8c7f656b160b2f0e9d033c528b613905c8", 33775),
}
MAX_TOKEN_BYTES = 65536
MAX_MERGE_WORK = 2_000_000
_asset_key: tuple[str, ...] | None = None
_ranks: dict[bytes, int] = {}
_words: frozenset[bytes] = frozenset()
_word_lengths: tuple[int, ...] = ()


class TokenizerError(ValueError):
    """A bounded token-filter operation could not complete."""


class AssetError(TokenizerError):
    """Pinned scanner data is missing, corrupt, or inconsistent."""


def utf8(value: str) -> bytes:
    return value.encode("utf-8", "surrogateescape")


def _read_bounded(path: Path, limit: int) -> bytes:
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise AssetError("scanner asset exceeds size limit")
    return data


def verify_assets() -> dict[str, str]:
    """Verify every asset before scanning, caching decoded data by content digest."""
    global _asset_key, _ranks, _words, _word_lengths
    try:
        names = ("manifest.json", "NOTICE.md", *_EXPECTED)
        blobs = {name: _read_bounded(ASSET_ROOT / name, 1_048_576 if name in _EXPECTED else 16384) for name in names}
        hashes = {name: hashlib.sha256(blob).hexdigest() for name, blob in blobs.items()}
        key = tuple(hashes[name] for name in names)
        if key == _asset_key:
            return hashes
        manifest = json.loads(blobs["manifest.json"])
        if manifest.get("schema") != 1 or manifest.get("upstream_commit") != UPSTREAM_COMMIT:
            raise AssetError("scanner asset manifest version mismatch")
        if manifest.get("notice_sha256") != hashes["NOTICE.md"]:
            raise AssetError("scanner asset notice digest mismatch")
        decoded = {}
        for name, (compressed_hash, raw_hash, lines) in _EXPECTED.items():
            meta = manifest["assets"][name]
            if hashes[name] != compressed_hash or meta.get("sha256") != compressed_hash:
                raise AssetError("scanner asset digest mismatch")
            with gzip.GzipFile(fileobj=io.BytesIO(blobs[name])) as stream:
                raw = stream.read(2_097_153)
            if len(raw) > 2_097_152 or hashlib.sha256(raw).hexdigest() != raw_hash:
                raise AssetError("scanner decompressed asset digest mismatch")
            if meta.get("uncompressed_sha256") != raw_hash or meta.get("uncompressed_bytes") != len(raw):
                raise AssetError("scanner asset manifest length mismatch")
            if meta.get("compressed_bytes") != len(blobs[name]) or meta.get("lines") != lines or len(raw.splitlines()) != lines:
                raise AssetError("scanner asset manifest count mismatch")
            decoded[name] = raw
        ranks = {base64.b64decode(token, validate=True): int(rank) for token, rank in (line.split() for line in decoded["cl100k_base.tiktoken.gz"].splitlines())}
        if len(ranks) != 100256 or set(ranks.values()) != set(range(100256)):
            raise AssetError("scanner token ranks are invalid")
        words = frozenset(decoded["words.txt.gz"].splitlines())
        _ranks, _words = ranks, words
        _word_lengths = tuple(sorted({len(word) for word in words}))
        _asset_key = key
        _count_cached.cache_clear()
        return hashes
    except AssetError:
        _asset_key = None
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError, EOFError) as exc:
        _asset_key = None
        raise AssetError("scanner assets are unavailable or malformed") from exc


def _ensure_assets() -> None:
    if _asset_key is None:
        verify_assets()


def entropy(value: str) -> float:
    data = utf8(value)
    if not data:
        return 0.0
    n = len(data)
    return -sum((count / n) * math.log2(count / n) for count in Counter(data).values())


def _category(char: str) -> str:
    return unicodedata.category(char)[0]


def _space(char: str) -> bool:
    # regexp2/.NET whitespace; Python isspace additionally includes U+001C..1F.
    return char in "\t\n\r\v\f\x85" or unicodedata.category(char) in ("Zs", "Zl", "Zp")


def _pieces(text: str):
    """Seven ordered cl100k regexp branches, without a third-party regex module."""
    i = 0
    while i < len(text):
        start = i
        if text[i] == "'":
            suffix = next((s for s in ("s", "t", "re", "ve", "m", "ll", "d") if text[i + 1:i + 1 + len(s)].lower() == s), None)
            if suffix:
                i += len(suffix) + 1
                yield text[start:i]
                continue
        j = i if _category(text[i]) == "L" else i + 1 if text[i] not in "\r\n" and _category(text[i]) not in "LN" else len(text)
        if j < len(text) and _category(text[j]) == "L":
            i = j + 1
            while i < len(text) and _category(text[i]) == "L":
                i += 1
            yield text[start:i]
            continue
        if _category(text[i]) == "N":
            i += 1
            while i < len(text) and i - start < 3 and _category(text[i]) == "N":
                i += 1
            yield text[start:i]
            continue
        j = i + 1 if text[i] == " " else i
        if j < len(text) and not _space(text[j]) and _category(text[j]) not in "LN":
            i = j + 1
            while i < len(text) and not _space(text[i]) and _category(text[i]) not in "LN":
                i += 1
            while i < len(text) and text[i] in "\r\n":
                i += 1
            yield text[start:i]
            continue
        j = i
        while j < len(text) and _space(text[j]):
            j += 1
        if j == i:
            raise TokenizerError("token splitter made no progress")
        last = max(text.rfind("\n", i, j), text.rfind("\r", i, j))
        i = last + 1 if last >= i else j - 1 if j < len(text) and j - i > 1 else j
        yield text[start:i]


def _count(value: str) -> int:
    work = 0
    count = 0
    for piece in _pieces(value):
        data = utf8(piece)
        if data in _ranks:
            count += 1
            continue
        parts = [bytes((byte,)) for byte in data]
        while len(parts) > 1:
            work += len(parts) - 1
            if work > MAX_MERGE_WORK:
                raise TokenizerError("token merge operation limit exceeded")
            rank, index = min((_ranks.get(parts[i] + parts[i + 1], 2**32 - 1), i) for i in range(len(parts) - 1))
            if rank == 2**32 - 1:
                break
            parts[index:index + 2] = [parts[index] + parts[index + 1]]
        count += len(parts)
    return count


@lru_cache(maxsize=1024)
def _count_cached(value: str) -> int:
    return _count(value)


def token_count(value: str) -> int:
    _ensure_assets()
    size = len(utf8(value))
    if size > MAX_TOKEN_BYTES:
        raise TokenizerError("token input size limit exceeded")
    return _count_cached(value) if size <= 512 else _count(value)


def _analyzed(value: str) -> str:
    return value.replace("\n", "").replace("\r", "") if len(utf8(value)) < 20 else value


def token_ratio(value: str) -> float:
    value = _analyzed(value)
    count = token_count(value)
    return len(utf8(value)) / count if count else 0.0


def _contains_word(value: str, minimum: int) -> bool:
    data = utf8(go_lower(value))
    for length in _word_lengths:
        if length < minimum:
            continue
        if length > len(data):
            break
        if any(data[i:i + length] in _words for i in range(len(data) - length + 1)):
            return True
    return False


def go_lower(value: str) -> str:
    """Go's simple lowercase mapping (Python expands dotted capital I)."""
    return "".join("i" if char == "İ" else char.lower() for char in value)


def fails_token_efficiency(value: str) -> bool:
    value = _analyzed(value)
    count = token_count(value)
    if not count:
        return False
    if _contains_word(value, 5):
        return True
    size = len(utf8(value))
    threshold = 2.1 if size < 12 and _contains_word(value, 4) else 2.5
    return size / count >= threshold
