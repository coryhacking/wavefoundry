"""Bounded interpreter for the pinned Betterleaks offline Expr profile.

This is deliberately not Python eval, CEL, or a general Expr implementation.
Unsupported syntax fails compilation before the scanner handles any input.
"""
from __future__ import annotations

import base64
import binascii
import math
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from . import secret_tokenizer as tokenizer

MAX_SOURCE_BYTES = 32768
MAX_TOKENS = 8192
MAX_DEPTH = 64
MAX_OPERATIONS = 100000
MAX_VALUE_BYTES = 16 * 1024 * 1024


class CompileError(ValueError):
    """A rule cannot be interpreted by the pinned offline profile."""


class EvaluationError(ValueError):
    """A filter could not finish; the caller must retain the finding."""


_PERL = {"d": "0-9", "w": "A-Za-z0-9_", "s": " \\t\\n\\f\\r"}
_POSIX = {"alnum": "A-Za-z0-9", "alpha": "A-Za-z", "ascii": "\\x00-\\x7f", "blank": " \\t", "cntrl": "\\x00-\\x1f\\x7f", "digit": "0-9", "graph": "!-~", "lower": "a-z", "print": " -~", "punct": "!-/:-@\\[-`{-~", "space": " \\t\\n\\v\\f\\r", "upper": "A-Z", "word": "A-Za-z0-9_", "xdigit": "A-Fa-f0-9"}
_WORD = "A-Za-z0-9_"


def _complement_class(body: str) -> str:
    excluded = [n for n in [*range(128), ord("ſ"), ord("K")] if re.fullmatch("[" + body + "]", chr(n))]
    result = []
    start = 0
    for end in excluded + [0x110000]:
        if start < end:
            lo, hi = f"\\U{start:08x}", f"\\U{end - 1:08x}"
            result.append(lo if start == end - 1 else lo + "-" + hi)
        start = end + 1
    return "".join(result)


def _fold_literal(char: str) -> str:
    # Go SimpleFold adds Kelvin K and long s, but not Python's Turkish I variants.
    if char in "kKK":
        return "[kKK]"
    if char in "sSſ":
        return "[sSſ]"
    if char.isascii() and char.isalpha():
        return "[" + char.lower() + char.upper() + "]"
    if not char.isascii() and char.isalpha():
        raise CompileError("unsupported non-ASCII folded regex literal")
    return re.escape(char)


class _Regex:
    def __init__(self, source: str):
        self.source, self.pos = source, 0

    def escaped(self, flags: set[str], in_class: bool = False) -> str:
        self.pos += 1
        if self.pos >= len(self.source):
            raise CompileError("unfinished regex escape")
        c = self.source[self.pos]
        self.pos += 1
        if c.lower() in _PERL:
            body = _PERL[c.lower()]
            if c.lower() == "w" and "i" in flags:
                body += "ſK"
            if in_class and c.isupper():
                return _complement_class(body)
            return body if in_class else "[" + ("^" if c.isupper() else "") + body + "]"
        if c in "bB" and not in_class:
            boundary = rf"(?:(?<![{_WORD}])(?=[{_WORD}])|(?<=[{_WORD}])(?![{_WORD}]))"
            return boundary if c == "b" else rf"(?:(?<=[{_WORD}])(?=[{_WORD}])|(?<![{_WORD}])(?![{_WORD}]))"
        if c == "z" and not in_class:
            return r"\Z"
        if c == "A" and not in_class:
            return r"\A"
        if c in "pPQ" or c.isdigit():
            raise CompileError("unsupported regex escape")
        if c in "xuU":
            size = {"x": 2, "u": 4, "U": 8}[c]
            if c == "x" and self.source[self.pos:self.pos + 1] == "{":
                end = self.source.find("}", self.pos + 1)
                if end < 0:
                    raise CompileError("unfinished regex codepoint")
                digits = self.source[self.pos + 1:end]
                self.pos = end + 1
            else:
                digits = self.source[self.pos:self.pos + size]
                self.pos += size
            try:
                char = chr(int(digits, 16))
            except (ValueError, OverflowError) as exc:
                raise CompileError("invalid regex codepoint") from exc
            if "i" in flags and char.isalpha():
                folded = _fold_literal(char)
                return folded[1:-1] if in_class and folded.startswith("[") else folded
            return re.escape(char)
        if c.isalpha() and c not in "nrtfav":
            raise CompileError("unsupported regex escape")
        return "\\" + c

    def char_class(self, flags: set[str]) -> str:
        self.pos += 1
        negated = self.source[self.pos:self.pos + 1] == "^"
        if negated:
            self.pos += 1
        pieces = []
        first = True
        while self.pos < len(self.source):
            c = self.source[self.pos]
            if c == "]" and not first:
                self.pos += 1
                body = "".join(pieces)
                if body.endswith("-") and not body.endswith("\\-"):
                    body = body[:-1] + r"\-"
                if "i" in flags:
                    # Expand ASCII class membership under case folding, without
                    # re.IGNORECASE's extra dotted/dotless-I matches.
                    try:
                        probe = re.compile("[" + body + "]")
                        extras = "".join(ch.swapcase() for ch in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" if probe.fullmatch(ch))
                        if probe.fullmatch("k") or probe.fullmatch("K"):
                            extras += "K"
                        if probe.fullmatch("s") or probe.fullmatch("S"):
                            extras += "ſ"
                        body += extras
                    except re.error as exc:
                        raise CompileError("invalid regex character class") from exc
                return "[" + ("^" if negated else "") + body + "]"
            first = False
            if self.source.startswith("[:", self.pos):
                end = self.source.find(":]", self.pos)
                name = self.source[self.pos + 2:end]
                if end < 0 or name not in _POSIX:
                    raise CompileError("unsupported POSIX character class")
                pieces.append(_POSIX[name])
                self.pos = end + 2
            elif c == "\\":
                # Complement shorthand only after applying its Go fold closure.
                # Escaped range endpoints remain single codepoints until the
                # completed character class is expanded above.
                shorthand = self.source[self.pos + 1:self.pos + 2] in "dDwWsS"
                pieces.append(self.escaped(flags if shorthand else set(), True))
            else:
                pieces.append("\\]" if c == "]" else c)
                self.pos += 1
        raise CompileError("unfinished regex character class")

    def group(self, flags: set[str], depth: int = 0) -> str:
        if depth > MAX_DEPTH:
            raise CompileError("regex nesting limit exceeded")
        out = []
        while self.pos < len(self.source):
            c = self.source[self.pos]
            if c == ")":
                if not depth:
                    raise CompileError("unmatched regex closing group")
                self.pos += 1
                return "".join(out)
            if c == "(":
                self.pos += 1
                prefix = "("
                child_flags = set(flags)
                if self.source[self.pos:self.pos + 1] == "?":
                    self.pos += 1
                    m = re.match(r"([imsU]*)(?:-([imsU]+))?([:)])", self.source[self.pos:])
                    if m:
                        child_flags.update(m[1])
                        child_flags.difference_update(m[2] or "")
                        self.pos += len(m[0])
                        if m[3] == ")":
                            flags = child_flags
                            continue
                        prefix = "(?:"
                    else:
                        named = re.match(r"(?:P<|<)([A-Za-z_][A-Za-z0-9_]*)>", self.source[self.pos:])
                        if not named:
                            raise CompileError("unsupported regex group")
                        prefix = "(?P<" + named[1] + ">"
                        self.pos += len(named[0])
                out.append(prefix + self.group(child_flags, depth + 1) + ")")
            elif c == "[":
                out.append(self.char_class(flags))
            elif c == "\\":
                out.append(self.escaped(flags))
            elif c == ".":
                out.append("(?s:.)" if "s" in flags else ".")
                self.pos += 1
            elif c in "^$":
                out.append("(?m:" + c + ")" if "m" in flags else r"\A" if c == "^" else r"\Z")
                self.pos += 1
            elif c in "*+?" or (c == "{" and re.match(r"\{\d+(?:,\d*)?\}", self.source[self.pos:])):
                m = re.match(r"\{\d+(?:,\d*)?\}|[+*?]", self.source[self.pos:])
                quantifier = m[0]
                if quantifier.startswith("{") and any(int(n) > 1000 for n in re.findall(r"\d+", quantifier)):
                    raise CompileError("Go regex repetition limit exceeded")
                self.pos += len(quantifier)
                lazy = self.source[self.pos:self.pos + 1] == "?"
                if lazy:
                    self.pos += 1
                out.append(quantifier + ("?" if lazy != ("U" in flags) else ""))
            elif c == "|":
                out.append(c)
                self.pos += 1
            else:
                out.append(_fold_literal(c) if "i" in flags else re.escape(c))
                self.pos += 1
        if depth:
            raise CompileError("unfinished regex group")
        return "".join(out)


def compile_regex(pattern: str) -> re.Pattern[str]:
    """Compile the supported Go-regexp profile, including flags and ASCII classes."""
    try:
        if not isinstance(pattern, str) or len(tokenizer.utf8(pattern)) > MAX_SOURCE_BYTES:
            raise CompileError("regex source size limit exceeded")
        return _compile_regex_cached(pattern)
    except CompileError:
        raise
    except (ValueError, TypeError, RecursionError, OverflowError) as exc:
        raise CompileError("invalid or excessive regex") from exc


@lru_cache(maxsize=1024)
def _compile_regex_cached(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(_Regex(pattern).group(set()))
    except re.error as exc:
        raise CompileError("invalid regex") from exc


def _tokens(source: str) -> list[tuple[str, Any]]:
    tokens = []
    i = 0
    while i < len(source):
        c = source[i]
        if c.isspace():
            i += 1
            continue
        if source.startswith("//", i):
            end = source.find("\n", i)
            i = len(source) if end < 0 else end + 1
            continue
        if source.startswith("/*", i):
            end = source.find("*/", i + 2)
            if end < 0:
                raise CompileError("unfinished expression comment")
            i = end + 2
            continue
        if c in "'\"`":
            quote = c
            i += 1
            chars = []
            while i < len(source) and source[i] != quote:
                if source[i] == "\\" and quote != "`":
                    i += 1
                    if i >= len(source):
                        raise CompileError("unfinished string escape")
                    esc = source[i]
                    values = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "a": "\a", "\\": "\\", "'": "'", '"': '"'}
                    if esc in values:
                        chars.append(values[esc])
                    elif esc in "xuU":
                        count = {"x": 2, "u": 4, "U": 8}[esc]
                        digits = source[i + 1:i + count + 1]
                        try:
                            if len(digits) != count:
                                raise ValueError
                            chars.append(chr(int(digits, 16)))
                        except (ValueError, OverflowError) as exc:
                            raise CompileError("invalid string escape") from exc
                        i += count
                    else:
                        raise CompileError("unsupported string escape")
                else:
                    chars.append(source[i])
                i += 1
            if i == len(source):
                raise CompileError("unfinished expression string")
            i += 1
            tokens.append(("literal", "".join(chars)))
        elif c.isdigit():
            m = re.match(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", source[i:])
            raw = m[0]
            tokens.append(("literal", float(raw) if any(x in raw for x in ".eE") else int(raw)))
            i += len(raw)
        elif c.isascii() and (c.isalpha() or c == "_"):
            m = re.match(r"[A-Za-z_]\w*", source[i:], re.ASCII)
            raw = m[0]
            tokens.append((raw, raw))
            i += len(raw)
        else:
            op = next((x for x in ("||", "&&", "<=", ">=", "==", "!=") if source.startswith(x, i)), c)
            if op not in ("||", "&&", "<=", ">=", "==", "!=", "<", ">", "+", "-", "%", "!", "(", ")", "[", "]", "{", "}", ",", ";", "=", "?", ":", ".", "#"):
                raise CompileError("unsupported expression token")
            tokens.append((op, op))
            i += len(op)
        if len(tokens) > MAX_TOKENS:
            raise CompileError("expression token limit exceeded")
    return tokens + [("EOF", None)]


_ARITY = {"entropy": (1,), "tokenRatio": (1,), "failsTokenEfficiency": (1,), "matchesAny": (2,), "containsAny": (2,), "startsWithAny": (2,), "findMatch": (2,), "setConfidence": (1,), "lower": (1,), "split": (2, 3), "replace": (3, 4), "join": (1, 2), "len": (1,), "map": (2,), "min": (2,), "max": (2,), "repeat": (2,), "fromBase64": (1,)}
_PRECEDENCE = {"||": 10, "&&": 15, "==": 20, "!=": 20, "<": 20, ">": 20, "<=": 20, ">=": 20, "contains": 20, "matches": 20, "+": 30, "-": 30, "%": 60}
_FINDING_FIELDS = {"secret", "match", "line", "rule_id", "description", "confidence", "context", "captures", "entropy", "fragment_raw", "match_start_idx", "match_end_idx", "match_line_start_idx", "match_line_end_idx"}


class _Parser:
    def __init__(self, source: str, prefilter: bool):
        self.tokens, self.pos, self.prefilter = _tokens(source), 0, prefilter
        self.names = {"attributes"} if prefilter else {"attributes", "finding"}
        self.depth = 0
        self.predicate = 0

    def take(self, value: str | None = None):
        token = self.tokens[self.pos]
        if value is not None and token[0] != value:
            raise CompileError("unexpected expression token")
        self.pos += 1
        return token

    def peek(self, value: str) -> bool:
        return self.tokens[self.pos][0] == value

    def expr(self, minimum: int = 0):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise CompileError("expression nesting limit exceeded")
        try:
            if self.peek("let"):
                if minimum:
                    raise CompileError("misplaced variable declaration")
                self.take()
                name = self.take()[0]
                if not re.fullmatch(r"[A-Za-z_]\w*", name) or name in self.names or name in _ARITY:
                    raise CompileError("invalid or shadowed expression variable")
                self.take("=")
                value = self.expr()
                self.take(";")
                self.names.add(name)
                body = self.expr()
                self.names.remove(name)
                return ("let", name, value, body)
            if self.peek("!") or self.peek("-"):
                op = self.take()[0]
                node = ("unary", op, self.expr(50 if op == "!" else 90))
            else:
                node = self.primary()
            while self.tokens[self.pos][0] in _PRECEDENCE and _PRECEDENCE[self.tokens[self.pos][0]] >= minimum:
                op = self.take()[0]
                node = ("binary", op, node, self.expr(_PRECEDENCE[op] + 1))
            if minimum == 0 and self.peek("?"):
                self.take()
                yes = self.expr()
                self.take(":")
                node = ("if", node, yes, self.expr())
            return node
        finally:
            self.depth -= 1

    def primary(self):
        kind, value = self.take()
        if kind == "literal":
            node = ("literal", value)
        elif kind in ("true", "false", "nil"):
            node = ("literal", {"true": True, "false": False, "nil": None}[kind])
        elif kind == "(":
            node = self.expr()
            self.take(")")
        elif kind == "[":
            values = []
            while not self.peek("]"):
                values.append(self.expr())
                if not self.peek(","):
                    break
                self.take()
            self.take("]")
            node = ("array", tuple(values))
        elif kind == "#":
            if not self.predicate:
                raise CompileError("predicate pointer outside map")
            node = ("var", "#")
        elif kind in _ARITY and self.peek("("):
            if self.prefilter and kind not in {"matchesAny", "containsAny", "startsWithAny"}:
                raise CompileError("function unavailable in prefilter")
            self.take()
            args = []
            while not self.peek(")"):
                if kind == "map" and len(args) == 1:
                    self.take("{")
                    self.predicate += 1
                    args.append(self.expr())
                    self.predicate -= 1
                    self.take("}")
                else:
                    args.append(self.expr())
                if not self.peek(","):
                    break
                self.take()
            self.take(")")
            if len(args) not in _ARITY[kind]:
                raise CompileError("unsupported function arity")
            node = ("call", kind, tuple(args))
        elif kind in self.names:
            node = ("var", kind)
        else:
            raise CompileError("unknown expression variable or function")
        while self.peek("[") or self.peek("."):
            if self.peek("."):
                self.take()
                member = self.take()[0]
                if not re.fullmatch(r"[A-Za-z_]\w*", member):
                    raise CompileError("invalid expression member")
                node = ("index", node, ("literal", member))
            else:
                self.take()
                left = None if self.peek(":") else self.expr()
                if self.peek(":"):
                    self.take()
                    right = None if self.peek("]") else self.expr()
                    node = ("slice", node, left, right)
                else:
                    if node == ("var", "finding") and left[0] == "literal" and left[1] not in _FINDING_FIELDS:
                        raise CompileError("unknown finding field")
                    node = ("index", node, left)
                self.take("]")
        return node


@dataclass(frozen=True)
class Program:
    tree: tuple
    prefilter: bool = False


def _validate_tree(tree: tuple) -> None:
    pending = [tree]
    while pending:
        node = pending.pop()
        kind = node[0]
        if kind in {"literal", "var"}:
            continue
        if kind == "call":
            name, args = node[1], node[2]
            pending.extend(args)
            patterns = []
            if name == "matchesAny" and args[1][0] == "array":
                patterns = args[1][1]
            elif name == "findMatch":
                patterns = [args[1]]
            for pattern in patterns:
                if pattern[0] == "literal" and isinstance(pattern[1], str):
                    compile_regex(pattern[1])
        elif kind == "array":
            pending.extend(node[1])
        else:
            pending.extend(part for part in node[1:] if isinstance(part, tuple))
            if kind == "binary" and node[1] == "matches" and node[3][0] == "literal":
                compile_regex(node[3][1])
            if kind == "index" and node[1] == ("var", "finding") and node[2][0] == "literal" and node[2][1] not in _FINDING_FIELDS:
                raise CompileError("unknown finding field")


def compile_filter(source: str, prefilter: bool = False) -> Program:
    try:
        if not isinstance(source, str) or len(tokenizer.utf8(source)) > MAX_SOURCE_BYTES:
            raise CompileError("expression source size limit exceeded")
        return _compile_filter_cached(source, prefilter)
    except CompileError:
        raise
    except (ValueError, TypeError, IndexError, RecursionError, OverflowError) as exc:
        raise CompileError("malformed or excessive expression") from exc


@lru_cache(maxsize=512)
def _compile_filter_cached(source: str, prefilter: bool) -> Program:
    try:
        parser = _Parser(source, prefilter)
        tree = parser.expr()
        parser.take("EOF")
        _validate_tree(tree)
        return Program(tree, prefilter)
    except (IndexError, RecursionError) as exc:
        raise CompileError("malformed or excessive expression") from exc


def _bool(value):
    if type(value) is not bool:
        raise EvaluationError("boolean expression required")
    return value


def _strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(x, str) for x in value):
        return value
    return []


class _Evaluator:
    def __init__(self, finding: dict, attributes: dict):
        self.env = {"finding": finding, "attributes": attributes}
        self.operations = 0
        self.allocated = 0

    def account(self, value):
        if isinstance(value, str):
            self.allocated += len(tokenizer.utf8(value))
        elif isinstance(value, list):
            self.allocated += len(value) * 16
        if self.allocated > MAX_VALUE_BYTES:
            raise EvaluationError("expression allocation limit exceeded")
        return value

    def reserve(self, size: int) -> None:
        if size < 0 or size + self.allocated > MAX_VALUE_BYTES:
            raise EvaluationError("expression allocation limit exceeded")

    def eval(self, node, env=None):
        self.operations += 1
        if self.operations > MAX_OPERATIONS:
            raise EvaluationError("expression operation limit exceeded")
        env = self.env if env is None else env
        kind = node[0]
        if kind == "literal":
            return node[1]
        if kind == "var":
            return env[node[1]]
        if kind == "array":
            return self.account([self.eval(x, env) for x in node[1]])
        if kind == "let":
            local = dict(env)
            local[node[1]] = self.eval(node[2], env)
            return self.eval(node[3], local)
        if kind == "if":
            return self.eval(node[2] if _bool(self.eval(node[1], env)) else node[3], env)
        if kind == "unary":
            value = self.eval(node[2], env)
            return not _bool(value) if node[1] == "!" else -value
        if kind == "binary":
            op = node[1]
            left = self.eval(node[2], env)
            if op == "||":
                return _bool(left) or _bool(self.eval(node[3], env))
            if op == "&&":
                return _bool(left) and _bool(self.eval(node[3], env))
            right = self.eval(node[3], env)
            if op == "+":
                if isinstance(left, str) and isinstance(right, str):
                    self.reserve(len(tokenizer.utf8(left)) + len(tokenizer.utf8(right)))
                return self.account(left + right)
            if op == "-":
                return left - right
            if op == "%":
                if type(left) is not int or type(right) is not int or right == 0:
                    raise EvaluationError("integer remainder operands required")
                return left - math.trunc(left / right) * right
            if op == "contains":
                return False if left is None or right is None else right in left
            if op == "matches":
                return False if left is None or right is None else bool(compile_regex(right).search(left))
            if op == "==":
                return left == right
            if op == "!=":
                return left != right
            if op == "<":
                return left < right
            if op == "<=":
                return left <= right
            if op == ">":
                return left > right
            if op == ">=":
                return left >= right
        if kind == "index":
            obj, key = self.eval(node[1], env), self.eval(node[2], env)
            if isinstance(obj, dict):
                if key not in obj:
                    # Go map[string]string yields its zero value on absent keys.
                    return "" if node[1] == ("var", "attributes") else None
                return obj[key]
            if isinstance(obj, str):
                return tokenizer.utf8(obj)[key]
            return obj[key]
        if kind == "slice":
            obj = self.eval(node[1], env)
            data = tokenizer.utf8(obj) if isinstance(obj, str) else obj
            length = len(data)
            start = self.eval(node[2], env) if node[2] is not None else 0
            end = self.eval(node[3], env) if node[3] is not None else length
            if type(start) is not int or type(end) is not int:
                raise EvaluationError("integer slice indexes required")
            start = max(0, length + start if start < 0 else start)
            end = min(length, max(0, length + end if end < 0 else end))
            result = data[min(start, end):end]
            return self.account(result.decode("utf-8", "surrogateescape") if isinstance(obj, str) else result)
        if kind == "call":
            name, nodes = node[1], node[2]
            if name == "map":
                values = self.eval(nodes[0], env)
                if not isinstance(values, list):
                    raise EvaluationError("map requires an array")
                return self.account([self.eval(nodes[1], dict(env, **{"#": value})) for value in values])
            args = [self.eval(n, env) for n in nodes]
            return self.account(self.call(name, args))
        raise EvaluationError("unknown expression node")

    def call(self, name: str, a: list):
        if name == "entropy":
            return tokenizer.entropy(a[0])
        if name == "tokenRatio":
            return tokenizer.token_ratio(a[0])
        if name == "failsTokenEfficiency":
            return tokenizer.fails_token_efficiency(a[0])
        if name in {"matchesAny", "containsAny", "startsWithAny"}:
            values, terms = _strings(a[0]), _strings(a[1])
            if name == "matchesAny":
                patterns = [compile_regex(p) for p in terms]
                return any(p.search(v) for p in patterns for v in values)
            if name == "containsAny":
                return any(tokenizer.go_lower(t) in tokenizer.go_lower(v) for t in terms for v in values)
            return any(v.startswith(t) for t in terms for v in values)
        if name == "findMatch":
            found = compile_regex(a[1]).search(a[0])
            return found.group() if found else ""
        if name == "setConfidence":
            if a[0] not in {"low", "medium", "high"}:
                raise EvaluationError("invalid confidence")
            self.env["attributes"]["confidence"] = a[0]
            return a[0]
        if name == "lower":
            return tokenizer.go_lower(a[0])
        if name == "len":
            return len(a[0])
        if name in {"min", "max"}:
            return min(a) if name == "min" else max(a)
        if name == "join":
            glue = a[1] if len(a) == 2 else ""
            self.reserve(sum(len(tokenizer.utf8(value)) for value in a[0]) + max(0, len(a[0]) - 1) * len(tokenizer.utf8(glue)))
            return glue.join(a[0])
        if name == "split":
            if len(a) == 3 and a[2] == 0:
                return []
            count = a[2] - 1 if len(a) == 3 and a[2] > 0 else -1
            pieces = len(a[0]) if a[1] == "" else a[0].count(a[1]) + 1
            self.reserve((pieces if count < 0 else min(pieces, count + 1)) * 16)
            if a[1] == "":
                chars = list(a[0])
                return chars if count < 0 else chars[:count] + (["".join(chars[count:])] if chars[count:] else [])
            return a[0].split(a[1], count)
        if name == "replace":
            count = a[0].count(a[1]) if len(a) == 3 or a[3] < 0 else min(a[0].count(a[1]), a[3])
            self.reserve(len(tokenizer.utf8(a[0])) + count * (len(tokenizer.utf8(a[2])) - len(tokenizer.utf8(a[1]))))
            return a[0].replace(a[1], a[2], a[3] if len(a) == 4 else -1)
        if name == "repeat":
            if type(a[1]) is not int or a[1] < 0 or a[1] > 1_000_000 or len(tokenizer.utf8(a[0])) * a[1] > MAX_VALUE_BYTES:
                raise EvaluationError("repeat limit exceeded")
            return a[0] * a[1]
        if name == "fromBase64":
            raw = base64.b64decode(a[0].replace("\r", "").replace("\n", ""), validate=True)
            return raw.decode("utf-8", "surrogateescape")
        raise EvaluationError("unknown filter function")


def evaluate_filter(program: Program, finding: dict, attributes: dict) -> bool:
    try:
        return _bool(_Evaluator(finding, attributes).eval(program.tree))
    except EvaluationError:
        raise
    except (ValueError, TypeError, KeyError, IndexError, RecursionError, OverflowError, UnicodeError, binascii.Error) as exc:
        raise EvaluationError("filter evaluation failed") from exc
