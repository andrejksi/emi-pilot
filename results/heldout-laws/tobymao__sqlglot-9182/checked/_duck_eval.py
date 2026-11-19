"""Tiny evaluator of constant DuckDB expression trees, used by the rules (not a rule file)."""
import math
import re

import sqlglot
from sqlglot import exp


def _num(v):
    return v


def _anon(name, args):
    name = name.upper()
    if name in ("STRPOS", "INSTR", "POSITION"):
        s, sub = args
        return None if s is None or sub is None else s.find(sub) + 1
    if name == "SPLIT_PART":
        s, sep, i = args
        parts = s.split(sep) if sep else [s]
        return parts[i - 1] if 0 < i <= len(parts) else ""
    if name in ("STRLEN", "LENGTH", "LEN", "CHAR_LENGTH", "CHARACTER_LENGTH"):
        return None if args[0] is None else len(args[0])
    if name in ("CHR",):
        return chr(args[0])
    if name in ("LEFT",):
        return args[0][: args[1]]
    if name in ("STRING_SPLIT", "STR_SPLIT", "SPLIT", "STRING_TO_ARRAY"):
        return args[0].split(args[1])
    if name in ("REGEXP_EXTRACT",):
        m = re.search(args[1], args[0])
        return m.group(args[2] if len(args) > 2 else 0) if m else ""
    if name in ("REGEXP_REPLACE",):
        return re.sub(args[1], args[2], args[0], count=0 if len(args) > 3 and "g" in args[3] else 1)
    if name in ("IFNULL", "COALESCE"):
        return next((a for a in args if a is not None), None)
    raise AssertionError(f"unsupported function {name}")


def ev(node):
    if isinstance(node, exp.Paren):
        return ev(node.this)
    if isinstance(node, exp.Literal):
        if node.is_string:
            return node.this
        return int(node.this) if node.is_int else float(node.this)
    if isinstance(node, exp.Null):
        return None
    if isinstance(node, exp.Boolean):
        return node.this
    if isinstance(node, exp.Neg):
        return -ev(node.this)
    if isinstance(node, exp.Chr):
        return "".join(chr(ev(e)) for e in node.expressions)
    if isinstance(node, (exp.DPipe,)):
        a, b = ev(node.this), ev(node.expression)
        return None if a is None or b is None else a + b
    if isinstance(node, exp.Concat):
        vals = [ev(e) for e in node.expressions]
        return "".join(v for v in vals if v is not None)
    if isinstance(node, exp.Length):
        v = ev(node.this)
        return None if v is None else len(v)
    if isinstance(node, exp.StrPosition):
        s, sub = ev(node.this), ev(node.args["substr"])
        return None if s is None or sub is None else s.find(sub) + 1
    if isinstance(node, exp.Substring):
        s = ev(node.this)
        start = ev(node.args["start"]) if node.args.get("start") else 1
        length = ev(node.args["length"]) if node.args.get("length") else None
        begin = max(start - 1, 0)
        end = None if length is None else (start - 1 + length)
        return s[begin:end] if end is None or end > 0 else ""
    if isinstance(node, exp.Left):
        return ev(node.this)[: ev(node.expression)]
    if isinstance(node, exp.SplitPart):
        return _anon("SPLIT_PART", [ev(node.this), ev(node.args["delimiter"]), ev(node.args["part_index"])])
    if isinstance(node, exp.Split):
        return ev(node.this).split(ev(node.expression))
    if isinstance(node, exp.Bracket):
        arr = ev(node.this)
        i = ev(node.expressions[0])
        return arr[i - 1] if 0 < i <= len(arr) else None
    if isinstance(node, exp.RegexpExtract):
        return _anon("REGEXP_EXTRACT", [ev(node.this), ev(node.expression)] + ([ev(node.args["group"])] if node.args.get("group") else []))
    if isinstance(node, exp.Nullif):
        a, b = ev(node.this), ev(node.expression)
        return None if a == b else a
    if isinstance(node, exp.Coalesce):
        return next((v for v in (ev(e) for e in [node.this, *node.expressions]) if v is not None), None)
    if isinstance(node, (exp.Add, exp.Sub, exp.Mul)):
        a, b = ev(node.this), ev(node.expression)
        if a is None or b is None:
            return None
        return a + b if isinstance(node, exp.Add) else a - b if isinstance(node, exp.Sub) else a * b
    if isinstance(node, (exp.EQ, exp.NEQ, exp.GT, exp.GTE, exp.LT, exp.LTE)):
        a, b = ev(node.this), ev(node.expression)
        if a is None or b is None:
            return None
        return {exp.EQ: a == b, exp.NEQ: a != b, exp.GT: a > b, exp.GTE: a >= b, exp.LT: a < b, exp.LTE: a <= b}[type(node)]
    if isinstance(node, exp.Not):
        v = ev(node.this)
        return None if v is None else not v
    if isinstance(node, exp.If):
        return ev(node.args["true"]) if ev(node.this) else ev(node.args.get("false")) if node.args.get("false") else None
    if isinstance(node, exp.Case):
        for w in node.args.get("ifs") or []:
            if ev(w.this):
                return ev(w.args["true"])
        return ev(node.args["default"]) if node.args.get("default") else None
    if isinstance(node, (exp.Greatest, exp.Least)):
        vals = [ev(node.this), *(ev(e) for e in node.expressions)]
        return (max if isinstance(node, exp.Greatest) else min)(vals)
    if isinstance(node, exp.Cast):
        v = ev(node.this)
        if v is None:
            return None
        if node.to.is_type(*exp.DataType.INTEGER_TYPES):
            return int(v)
        if node.to.is_type(*exp.DataType.TEXT_TYPES):
            return str(v)
        return v
    if isinstance(node, exp.Anonymous):
        return _anon(node.name, [ev(e) for e in node.expressions])
    if isinstance(node, exp.Func) and node.sql_name():
        return _anon(node.sql_name(), [ev(a) for a in node.args.values() if isinstance(a, exp.Expr)])
    raise AssertionError(f"unsupported node {type(node).__name__}: {node.sql('duckdb')}")


def duckdb_value(sqlite_query):
    translated = sqlglot.transpile(sqlite_query, read="sqlite", write="duckdb")[0]
    return ev(sqlglot.parse_one(translated, read="duckdb").expressions[0])
