"""A tiny, safe evaluator for config eligibility predicates.

Rules in ``config.yaml`` carry expressions like
``country != 'US' and not credit_insured``. We must NOT use ``eval()`` on
client-supplied agreement text, so this evaluates a whitelisted subset of
Python via the ``ast`` module: boolean ops, ``not``, comparisons, field names
(resolved against an attribute dict), and literal constants. Anything else
raises :class:`PredicateError`.
"""

from __future__ import annotations

import ast
import operator
from typing import Any

_COMPARATORS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}


class PredicateError(ValueError):
    """Raised when a predicate uses an unsupported construct or unknown field."""


def evaluate(expr: str, attributes: dict[str, Any]) -> bool:
    tree = ast.parse(expr, mode="eval")
    return bool(_eval(tree.body, attributes))


def _eval(node: ast.AST, attrs: dict[str, Any]) -> Any:
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, attrs) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise PredicateError("unsupported boolean operator")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return not _eval(node.operand, attrs)
    if isinstance(node, ast.Compare):
        left = _eval(node.left, attrs)
        for op, comparator in zip(node.ops, node.comparators):
            fn = _COMPARATORS.get(type(op))
            if fn is None:
                raise PredicateError(f"unsupported comparator: {type(op).__name__}")
            right = _eval(comparator, attrs)
            if not fn(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Name):
        if node.id not in attrs:
            raise PredicateError(f"unknown field in predicate: {node.id}")
        return attrs[node.id]
    if isinstance(node, ast.Constant):
        return node.value
    raise PredicateError(f"unsupported expression: {ast.dump(node)}")
