"""
Token and TokenType definitions.

Kept in their own module (separate from tokenizer.py) because both the
lexer and parser need to import Token/TokenType, but only the lexer needs
the tokenizing logic - this avoids the parser importing tokenizer
internals it has no business touching.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Keywords
    SELECT = auto()
    FROM = auto()
    WHERE = auto()
    AND = auto()
    OR = auto()

    # Literals
    IDENTIFIER = auto()  # table/column names, e.g. Bridges, ConcreteStrength
    QUANTITY = auto()  # e.g. 35MPa, 20m - number+unit, no space
    NUMBER = auto()  # e.g. 2023 - a bare number, no unit
    STRING = auto()  # e.g. 'Cambridge' - a quoted string literal

    # Symbols
    STAR = auto()  # *
    COMMA = auto()  # ,
    EQ = auto()  # =
    NEQ = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LE = auto()  # <=
    GE = auto()  # >=

    EOF = auto()  # sentinel marking end of input, so the parser never
    # needs to special-case "ran out of tokens" separately
    # from "saw an unexpected token"


# Case-insensitive keyword lookup. A bare dict rather than branching in the
# tokenizer keeps "what counts as a keyword" a single, greppable place -
# adding NOT or ORDER later is a one-line change here, not a new if-branch.
KEYWORDS: dict[str, TokenType] = {
    "SELECT": TokenType.SELECT,
    "FROM": TokenType.FROM,
    "WHERE": TokenType.WHERE,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
}


@dataclass(frozen=True)
class Token:
    type: TokenType
    text: str  # the raw source text this token was scanned from, e.g.
    # "35MPa", "ConcreteStrength", "Cambridge" (unquoted for STRING)
    position: int  # character offset in the source query, for error messages

    def __repr__(self) -> str:  # pragma: no cover - cosmetic only
        return f"Token({self.type.name}, {self.text!r})"
