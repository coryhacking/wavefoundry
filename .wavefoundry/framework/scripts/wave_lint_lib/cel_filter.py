"""Minimal CEL filter evaluator for betterleaks scan-rule filter expressions.

Supports the subset of CEL used by betterleaks:
  - Logical: ||, &&, !
  - Comparison: <=, >=, <, >, ==, !=
  - Functions: entropy(), failsTokenEfficiency(), matchesAny(), containsAny(),
    jwtExpired(), jwtExp()
  - Member/index access: finding["secret"], attributes[?"path"].orValue("")
  - Literals: raw/triple-quoted strings, numbers, booleans, arrays

A filter that evaluates to True means the finding is a false positive and should
be suppressed (mirrors betterleaks semantics: filter = "exclude this match").
"""
from __future__ import annotations

import base64
import json
import math
import re
import time
from typing import Any

# ---------------------------------------------------------------------------
# Sentinel for optional/missing values (CEL "none")
# ---------------------------------------------------------------------------
_MISSING = object()


# ---------------------------------------------------------------------------
# Built-in CEL functions
# ---------------------------------------------------------------------------

def _entropy(s: str) -> float:
    if not s:
        return 0.0
    counts: dict[str, int] = {}
    for c in s:
        counts[c] = counts.get(c, 0) + 1
    n = len(s)
    return -sum((v / n) * math.log2(v / n) for v in counts.values())


def _fails_token_efficiency(s: str) -> bool:
    # Mirrors gitleaks: unique_chars / length < 0.40
    if not s or len(s) < 10:
        return True
    return len(set(s)) / len(s) < 0.40


def _matches_any(s: str, patterns: list) -> bool:
    for p in patterns:
        if not isinstance(p, str):
            continue
        try:
            if re.search(p, s):
                return True
        except re.error:
            pass
    return False


def _contains_any(s: str, substrings: list) -> bool:
    sl = s.lower()
    for sub in substrings:
        if isinstance(sub, str) and sub.lower() in sl:
            return True
    return False


def _jwt_exp_claim(token: Any) -> int | None:
    """Return a JWT's payload `exp` claim as an int epoch, or None (wave 1p44w).

    Fail-safe by contract: wrong segment count, non-base64url payload, invalid
    JSON, a non-dict payload, or a missing/non-numeric `exp` all return None and
    NEVER raise — the scan gate must not crash on malformed real-world tokens.
    """
    if not isinstance(token, str):
        return None
    parts = token.split(".")
    if len(parts) < 2:
        return None
    seg = parts[1]
    try:
        padded = seg + "=" * (-len(seg) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    exp = payload.get("exp")
    # bool is an int subclass — exclude it explicitly.
    if isinstance(exp, bool) or not isinstance(exp, (int, float)):
        return None
    return int(exp)


def _jwt_expired(token: Any) -> bool:
    """True iff *token* is a JWT whose `exp` is in the past (fail-safe → False)."""
    exp = _jwt_exp_claim(token)
    return exp is not None and exp < time.time()


_FUNCTIONS: dict[str, Any] = {
    "entropy": _entropy,
    "failsTokenEfficiency": _fails_token_efficiency,
    "matchesAny": _matches_any,
    "containsAny": _contains_any,
    # Wave 1p44w — JWT expiry awareness (fail-safe; never raises).
    "jwtExpired": _jwt_expired,
    "jwtExp": lambda t: (_jwt_exp_claim(t) or 0),
}


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_T_EOF = "EOF"
_T_NUM = "NUM"
_T_STR = "STR"
_T_BOOL = "BOOL"
_T_IDENT = "IDENT"
_T_OP = "OP"
_T_LPAREN = "LP"
_T_RPAREN = "RP"
_T_LBRACKET = "LB"
_T_RBRACKET = "RB"
_T_DOT = "DOT"
_T_COMMA = "COM"
_T_QUESTION = "Q"


class _Token:
    __slots__ = ("type", "value")

    def __init__(self, type_: str, value: Any = None) -> None:
        self.type = type_
        self.value = value

    def __repr__(self) -> str:
        return f"Token({self.type}, {self.value!r})"


def _tokenize(expr: str) -> list[_Token]:
    toks: list[_Token] = []
    i = 0
    n = len(expr)

    while i < n:
        c = expr[i]

        # Whitespace
        if c.isspace():
            i += 1
            continue

        # Raw triple-quoted strings: r"""...""" or r'''...'''
        if c == "r" and i + 3 < n and expr[i + 1 : i + 4] in ('"""', "'''"):
            delim = expr[i + 1 : i + 4]
            j = i + 4
            while j + 2 < n and expr[j : j + 3] != delim:
                j += 1
            toks.append(_Token(_T_STR, expr[i + 4 : j]))
            i = j + 3
            continue

        # Triple-quoted strings: """...""" or '''...'''
        if i + 2 < n and expr[i : i + 3] in ('"""', "'''"):
            delim = expr[i : i + 3]
            j = i + 3
            parts: list[str] = []
            while j + 2 < n and expr[j : j + 3] != delim:
                if expr[j] == "\\" and j + 1 < n:
                    esc = expr[j + 1]
                    parts.append({"n": "\n", "t": "\t", "r": "\r"}.get(esc, esc))
                    j += 2
                else:
                    parts.append(expr[j])
                    j += 1
            toks.append(_Token(_T_STR, "".join(parts)))
            i = j + 3
            continue

        # Raw single-quoted strings: r"..." or r'...'
        if c == "r" and i + 1 < n and expr[i + 1] in ('"', "'"):
            q = expr[i + 1]
            j = i + 2
            while j < n and expr[j] != q:
                j += 1
            toks.append(_Token(_T_STR, expr[i + 2 : j]))
            i = j + 1
            continue

        # Single-quoted strings: "..." or '...'
        if c in ('"', "'"):
            q = c
            j = i + 1
            parts = []
            while j < n and expr[j] != q:
                if expr[j] == "\\" and j + 1 < n:
                    esc = expr[j + 1]
                    parts.append({"n": "\n", "t": "\t", "r": "\r"}.get(esc, esc))
                    j += 2
                else:
                    parts.append(expr[j])
                    j += 1
            toks.append(_Token(_T_STR, "".join(parts)))
            i = j + 1
            continue

        # Numbers (positive only — betterleaks filters use no arithmetic)
        if c.isdigit():
            j = i
            while j < n and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            toks.append(_Token(_T_NUM, float(expr[i:j])))
            i = j
            continue

        # Two-char operators
        two = expr[i : i + 2]
        if two in ("||", "&&", "<=", ">=", "==", "!="):
            toks.append(_Token(_T_OP, two))
            i += 2
            continue

        # Single-char operators
        if c in ("<", ">", "!"):
            toks.append(_Token(_T_OP, c))
            i += 1
            continue

        # Punctuation
        if c == "(":
            toks.append(_Token(_T_LPAREN))
        elif c == ")":
            toks.append(_Token(_T_RPAREN))
        elif c == "[":
            toks.append(_Token(_T_LBRACKET))
        elif c == "]":
            toks.append(_Token(_T_RBRACKET))
        elif c == ".":
            toks.append(_Token(_T_DOT))
        elif c == ",":
            toks.append(_Token(_T_COMMA))
        elif c == "?":
            toks.append(_Token(_T_QUESTION))
        elif c.isalpha() or c == "_":
            j = i
            while j < n and (expr[j].isalnum() or expr[j] == "_"):
                j += 1
            word = expr[i:j]
            if word == "true":
                toks.append(_Token(_T_BOOL, True))
            elif word == "false":
                toks.append(_Token(_T_BOOL, False))
            else:
                toks.append(_Token(_T_IDENT, word))
            i = j
            continue
        # Unknown character: skip silently
        i += 1

    toks.append(_Token(_T_EOF))
    return toks


# ---------------------------------------------------------------------------
# Recursive descent parser — produces an AST as nested tuples
# ---------------------------------------------------------------------------

class _Parser:
    def __init__(self, tokens: list[_Token]) -> None:
        self._toks = tokens
        self._pos = 0

    def _peek(self) -> _Token:
        return self._toks[self._pos]

    def _advance(self) -> _Token:
        tok = self._toks[self._pos]
        self._pos += 1
        return tok

    def _expect(self, type_: str) -> _Token:
        tok = self._advance()
        if tok.type != type_:
            raise ValueError(f"CEL parse: expected {type_}, got {tok}")
        return tok

    # Grammar:
    #   expr     = or_expr
    #   or_expr  = and_expr ("||" and_expr)*
    #   and_expr = not_expr ("&&" not_expr)*
    #   not_expr = "!" not_expr | cmp_expr
    #   cmp_expr = primary (CMP_OP primary)?
    #   primary  = "(" expr ")" | array | literal | call_or_access

    def parse(self) -> Any:
        ast = self._or()
        self._expect(_T_EOF)
        return ast

    def _or(self) -> Any:
        left = self._and()
        while self._peek().type == _T_OP and self._peek().value == "||":
            self._advance()
            left = ("||", left, self._and())
        return left

    def _and(self) -> Any:
        left = self._not()
        while self._peek().type == _T_OP and self._peek().value == "&&":
            self._advance()
            left = ("&&", left, self._not())
        return left

    def _not(self) -> Any:
        if self._peek().type == _T_OP and self._peek().value == "!":
            self._advance()
            return ("!", self._not())
        return self._cmp()

    def _cmp(self) -> Any:
        left = self._primary()
        if self._peek().type == _T_OP and self._peek().value in (
            "<=", ">=", "<", ">", "==", "!="
        ):
            op = self._advance().value
            return (op, left, self._primary())
        return left

    def _primary(self) -> Any:
        tok = self._peek()

        if tok.type == _T_LPAREN:
            self._advance()
            inner = self._or()
            self._expect(_T_RPAREN)
            return inner

        if tok.type == _T_LBRACKET:
            return self._array()

        if tok.type in (_T_NUM, _T_STR, _T_BOOL):
            self._advance()
            return ("lit", tok.value)

        if tok.type == _T_IDENT:
            return self._call_or_access()

        raise ValueError(f"CEL parse: unexpected token {tok}")

    def _array(self) -> Any:
        self._expect(_T_LBRACKET)
        items: list[Any] = []
        while self._peek().type != _T_RBRACKET and self._peek().type != _T_EOF:
            items.append(self._or())
            if self._peek().type == _T_COMMA:
                self._advance()
        self._expect(_T_RBRACKET)
        return ("array", items)

    def _call_or_access(self) -> Any:
        name = self._advance().value  # IDENT

        # Function call: name(...)
        if self._peek().type == _T_LPAREN:
            self._advance()
            args = self._arglist()
            self._expect(_T_RPAREN)
            node: Any = ("call", name, args)
        else:
            node = ("var", name)

        # Chained member/index access
        while self._peek().type in (_T_DOT, _T_LBRACKET):
            if self._peek().type == _T_DOT:
                self._advance()
                member = self._expect(_T_IDENT).value
                if self._peek().type == _T_LPAREN:
                    self._advance()
                    args = self._arglist()
                    self._expect(_T_RPAREN)
                    node = ("method", node, member, args)
                else:
                    node = ("attr", node, member)
            else:
                self._advance()  # consume [
                optional = False
                if self._peek().type == _T_QUESTION:
                    optional = True
                    self._advance()
                key = self._or()
                self._expect(_T_RBRACKET)
                node = ("index", node, key, optional)

        return node

    def _arglist(self) -> list[Any]:
        args: list[Any] = []
        while self._peek().type != _T_RPAREN and self._peek().type != _T_EOF:
            args.append(self._or())
            if self._peek().type == _T_COMMA:
                self._advance()
        return args


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

def _eval(node: Any, finding: dict, attributes: dict) -> Any:
    if not isinstance(node, tuple):
        return node

    kind = node[0]

    if kind == "lit":
        return node[1]

    if kind == "array":
        return [_eval(item, finding, attributes) for item in node[1]]

    if kind == "||":
        left = _eval(node[1], finding, attributes)
        if left is True or left is _MISSING:
            return bool(left) if left is not _MISSING else False
        # Short-circuit
        if left:
            return True
        return bool(_eval(node[2], finding, attributes))

    if kind == "&&":
        left = _eval(node[1], finding, attributes)
        if not left:
            return False
        return bool(_eval(node[2], finding, attributes))

    if kind == "!":
        return not _eval(node[1], finding, attributes)

    if kind in ("<=", ">=", "<", ">", "==", "!="):
        left = _eval(node[1], finding, attributes)
        right = _eval(node[2], finding, attributes)
        if left is _MISSING or right is _MISSING:
            return False
        try:
            if kind == "<=":
                return left <= right
            if kind == ">=":
                return left >= right
            if kind == "<":
                return left < right
            if kind == ">":
                return left > right
            if kind == "==":
                return left == right
            if kind == "!=":
                return left != right
        except TypeError:
            return False

    if kind == "var":
        name = node[1]
        if name == "finding":
            return finding
        if name == "attributes":
            return attributes
        return _MISSING

    if kind == "index":
        obj = _eval(node[1], finding, attributes)
        key = _eval(node[2], finding, attributes)
        optional = node[3]
        if obj is _MISSING or not isinstance(obj, dict):
            return _MISSING
        val = obj.get(key, _MISSING)
        return val if val is not _MISSING else (_MISSING if optional else None)

    if kind == "attr":
        # Simple attribute access (not needed beyond .orValue chaining)
        return _eval(node[1], finding, attributes)

    if kind == "method":
        obj = _eval(node[1], finding, attributes)
        method = node[2]
        args = [_eval(a, finding, attributes) for a in node[3]]
        if method == "orValue":
            default = args[0] if args else None
            return default if obj is _MISSING else obj
        return _MISSING

    if kind == "call":
        fn_name = node[1]
        args = [_eval(a, finding, attributes) for a in node[2]]
        fn = _FUNCTIONS.get(fn_name)
        if fn is None:
            return False  # unknown function — don't suppress
        try:
            return fn(*args)
        except Exception:
            return False

    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_AST_CACHE: dict[str, Any] = {}


def compile_filter(expr: str) -> Any:
    """Parse a CEL filter expression and return the cached AST."""
    if expr not in _AST_CACHE:
        tokens = _tokenize(expr)
        _AST_CACHE[expr] = _Parser(tokens).parse()
    return _AST_CACHE[expr]


def eval_filter(
    expr: str,
    secret: str,
    match: str,
    path: str,
    line: str = "",
    attrs: dict | None = None,
) -> bool:
    """Evaluate a CEL filter expression against a scanner finding.

    Returns True when the finding is a false positive and should be suppressed.

    Args:
        expr:   CEL filter string from the scan rule.
        secret: Captured secret value — regex capture group 1 (finding["secret"]).
        match:  Full regex match — group 0 (finding["match"]).
        path:   Relative file path (attributes["path"]).
        line:   the full source line text (finding["line"]) — betterleaks semantic,
                used by line-shape value-exclusion clauses (matchesAny(finding["line"], …)).
        attrs:  Optional extra ``attributes`` entries merged over ``{"path": path}``
                — e.g. policy flags a rule filter can read (wave 1p44w).
    """
    if not expr:
        return False
    try:
        ast = compile_filter(expr)
        finding = {"secret": secret, "match": match, "line": str(line)}
        attributes = {"path": path}
        if attrs:
            attributes.update(attrs)
        return bool(_eval(ast, finding, attributes))
    except Exception:
        return False  # evaluation error → don't suppress
