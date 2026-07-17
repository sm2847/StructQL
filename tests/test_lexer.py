"""
Tests for tokenize().

Several tests here specifically pin down the maximal-munch design decision
for quantities: "35MPa" must tokenize as ONE token, "2023" as a bare NUMBER,
and "35 MPa" (with a space) must NOT be glued into a quantity - that
distinction is the whole reason the lexer, not the parser, owns
unit-awareness.
"""

import pytest

from structql.exceptions import LexerError
from structql.lexer.tokenizer import tokenize
from structql.lexer.tokens import TokenType


def _types(source: str) -> list[TokenType]:
    return [t.type for t in tokenize(source)]


def test_keywords_are_case_insensitive() -> None:
    assert _types("SELECT") == [TokenType.SELECT, TokenType.EOF]
    assert _types("select") == [TokenType.SELECT, TokenType.EOF]
    assert _types("SeLeCt") == [TokenType.SELECT, TokenType.EOF]


def test_identifier_preserves_original_casing() -> None:
    tokens = tokenize("Bridges")
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].text == "Bridges"  # not lowercased/uppercased


def test_star_and_comma() -> None:
    assert _types("*") == [TokenType.STAR, TokenType.EOF]
    assert _types(",") == [TokenType.COMMA, TokenType.EOF]


def test_all_comparison_operators() -> None:
    assert _types("=") == [TokenType.EQ, TokenType.EOF]
    assert _types("!=") == [TokenType.NEQ, TokenType.EOF]
    assert _types("<") == [TokenType.LT, TokenType.EOF]
    assert _types(">") == [TokenType.GT, TokenType.EOF]
    assert _types("<=") == [TokenType.LE, TokenType.EOF]
    assert _types(">=") == [TokenType.GE, TokenType.EOF]


def test_bare_number_is_not_a_quantity() -> None:
    tokens = tokenize("2023")
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].text == "2023"


def test_number_immediately_followed_by_letters_is_a_quantity() -> None:
    tokens = tokenize("35MPa")
    assert tokens[0].type == TokenType.QUANTITY
    assert tokens[0].text == "35MPa"


def test_number_and_unit_separated_by_space_are_two_tokens() -> None:
    # Deliberately NOT glued into a quantity - this is invalid syntax that
    # the parser (M5) will reject, not something the lexer silently fixes.
    tokens = tokenize("35 MPa")
    assert tokens[0].type == TokenType.NUMBER
    assert tokens[0].text == "35"
    assert tokens[1].type == TokenType.IDENTIFIER
    assert tokens[1].text == "MPa"


def test_quantity_disambiguates_m_from_mm() -> None:
    assert tokenize("20m")[0].text == "20m"
    assert tokenize("500mm")[0].text == "500mm"


def test_decimal_quantity() -> None:
    tokens = tokenize("4.5kN")
    assert tokens[0].type == TokenType.QUANTITY
    assert tokens[0].text == "4.5kN"


def test_string_literal_is_unquoted_in_token_text() -> None:
    tokens = tokenize("'Cambridge'")
    assert tokens[0].type == TokenType.STRING
    assert tokens[0].text == "Cambridge"


def test_unterminated_string_raises_lexer_error() -> None:
    with pytest.raises(LexerError, match="Unterminated string"):
        tokenize("'Cambridge")


def test_unexpected_character_raises_lexer_error() -> None:
    with pytest.raises(LexerError, match="Unexpected character"):
        tokenize("@")


def test_full_query_tokenizes_correctly() -> None:
    source = "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023"
    types = _types(source)
    assert types == [
        TokenType.SELECT,
        TokenType.STAR,
        TokenType.FROM,
        TokenType.IDENTIFIER,
        TokenType.WHERE,
        TokenType.IDENTIFIER,
        TokenType.LT,
        TokenType.QUANTITY,
        TokenType.AND,
        TokenType.IDENTIFIER,
        TokenType.GT,
        TokenType.NUMBER,
        TokenType.EOF,
    ]


def test_query_with_column_list_and_multiline_whitespace() -> None:
    # Mirrors the loosely-formatted, multi-line style from the original
    # spec examples (blank lines between clauses are legal whitespace).
    source = """
    SELECT Name, ConcreteStrength

    FROM Bridges

    WHERE
    Depth > 20m
    """
    types = _types(source)
    assert types == [
        TokenType.SELECT,
        TokenType.IDENTIFIER,
        TokenType.COMMA,
        TokenType.IDENTIFIER,
        TokenType.FROM,
        TokenType.IDENTIFIER,
        TokenType.WHERE,
        TokenType.IDENTIFIER,
        TokenType.GT,
        TokenType.QUANTITY,
        TokenType.EOF,
    ]


def test_eof_token_position_is_end_of_source() -> None:
    tokens = tokenize("*")
    assert tokens[-1].type == TokenType.EOF
    assert tokens[-1].position == 1
