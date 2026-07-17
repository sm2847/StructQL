"""
Lexer: converts a raw query string into a flat list of Tokens.

Responsibility boundary: the lexer knows nothing about SQL grammar (it
doesn't know that SELECT must be followed by column names, or that WHERE
takes a condition). It only knows how to chop characters into meaningful
chunks. That separation is what lets us test tokenizing and parsing (M5)
completely independently - a lexer bug and a parser bug can never be
confused with each other.

Key design decision: quantities like "35MPa" are recognised as a SINGLE
token here, via maximal munch (consume digits, then immediately check for
adjacent letters with no whitespace). This keeps all "is this a quantity"
logic in one place, so the parser never has to reason about spacing or
reassemble a QUANTITY out of separate NUMBER/IDENTIFIER tokens.
"""

from __future__ import annotations

from structql.exceptions import LexerError
from structql.lexer.tokens import KEYWORDS, Token, TokenType

_TWO_CHAR_OPERATORS: dict[str, TokenType] = {
    "!=": TokenType.NEQ,
    "<=": TokenType.LE,
    ">=": TokenType.GE,
}

_ONE_CHAR_OPERATORS: dict[str, TokenType] = {
    "=": TokenType.EQ,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "*": TokenType.STAR,
    ",": TokenType.COMMA,
}


def tokenize(source: str) -> list[Token]:
    """Convert a query string into a list of Tokens, ending with an EOF token.

    Raises LexerError on any character sequence that can't be tokenised
    (an unrecognised symbol, or an unterminated string literal).
    """
    tokens: list[Token] = []
    pos = 0
    length = len(source)

    while pos < length:
        char = source[pos]

        if char.isspace():
            pos += 1
            continue

        if char == "'":
            token, pos = _scan_string(source, pos)
            tokens.append(token)
            continue

        if char.isdigit():
            token, pos = _scan_number_or_quantity(source, pos)
            tokens.append(token)
            continue

        if char.isalpha() or char == "_":
            token, pos = _scan_identifier_or_keyword(source, pos)
            tokens.append(token)
            continue

        two_char = source[pos : pos + 2]
        if two_char in _TWO_CHAR_OPERATORS:
            tokens.append(Token(_TWO_CHAR_OPERATORS[two_char], two_char, pos))
            pos += 2
            continue

        if char in _ONE_CHAR_OPERATORS:
            tokens.append(Token(_ONE_CHAR_OPERATORS[char], char, pos))
            pos += 1
            continue

        raise LexerError(f"Unexpected character {char!r} at position {pos} in query: {source!r}")

    tokens.append(Token(TokenType.EOF, "", pos))
    return tokens


def _scan_string(source: str, start: int) -> tuple[Token, int]:
    """Scan a single-quoted string literal, e.g. 'Cambridge'.

    The returned token's text is the UNQUOTED content, so the parser (and
    anything reading tokens) never has to strip quote characters itself.
    """
    pos = start + 1  # skip the opening quote
    length = len(source)
    while pos < length and source[pos] != "'":
        pos += 1

    if pos >= length:
        raise LexerError(f"Unterminated string literal starting at position {start}")

    text = source[start + 1 : pos]
    return Token(TokenType.STRING, text, start), pos + 1  # +1 to skip closing quote


def _scan_number_or_quantity(source: str, start: int) -> tuple[Token, int]:
    """Scan a numeric literal, then greedily check for an adjacent unit
    suffix (no whitespace) to decide NUMBER vs QUANTITY.

    This function only tokenises - it does NOT validate that a unit suffix
    is a real, known Unit (e.g. "35xyz" tokenises fine as a QUANTITY here).
    That validation happens later, in Quantity.parse (domain/quantity.py),
    when the parser builds an AST literal - keeping "is this valid SQL
    shape" (lexer/parser) separate from "is this a valid domain value"
    (Quantity).
    """
    length = len(source)
    pos = start

    while pos < length and source[pos].isdigit():
        pos += 1
    if pos < length and source[pos] == "." and pos + 1 < length and source[pos + 1].isdigit():
        pos += 1
        while pos < length and source[pos].isdigit():
            pos += 1

    number_end = pos

    # Maximal munch: if a letter immediately follows with no whitespace,
    # this is a QUANTITY, not a bare NUMBER. A space here means "unit" was
    # actually meant to be a separate token (which will fail to parse
    # sensibly later, correctly, rather than being silently glued on).
    if pos < length and (source[pos].isalpha()):
        while pos < length and source[pos].isalpha():
            pos += 1
        text = source[start:pos]
        return Token(TokenType.QUANTITY, text, start), pos

    text = source[start:number_end]
    return Token(TokenType.NUMBER, text, start), number_end


def _scan_identifier_or_keyword(source: str, start: int) -> tuple[Token, int]:
    """Scan a run of letters/digits/underscores, then classify it as a
    keyword (SELECT, FROM, ...) or a plain identifier (table/column name).

    Keyword matching is case-insensitive (SQL convention: `select` and
    `SELECT` are equivalent) but the token's stored text preserves the
    original casing, which matters for identifiers - table and column
    names ARE case-sensitive, since they come straight from CSV headers.
    """
    length = len(source)
    pos = start
    while pos < length and (source[pos].isalnum() or source[pos] == "_"):
        pos += 1

    text = source[start:pos]
    token_type = KEYWORDS.get(text.upper(), TokenType.IDENTIFIER)
    return Token(token_type, text, start), pos
