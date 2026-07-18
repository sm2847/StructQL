"""
Parser: converts a token stream into an AST (ast_nodes.py).

Responsibility boundary: syntax only. The parser checks that a query is
*grammatically* well-formed (e.g. WHERE is followed by a valid condition).
It does NOT check that a referenced table or column actually exists - that
is a semantic concern, handled by the executor at execution time
(M6). This mirrors the lexer's boundary: each layer only validates what it
can know without looking further down the pipeline.

Implemented as recursive descent with one function per precedence level
(_parse_or, _parse_and, _parse_comparison). Precedence falls out of how
these functions call each other, not from explicit priority numbers - see
the module docstring in ast_nodes.py for the grammar this encodes.
"""

from __future__ import annotations

from structql.domain.quantity import Quantity
from structql.domain.row import Value
from structql.exceptions import ParserError
from structql.lexer.tokenizer import tokenize
from structql.lexer.tokens import Token, TokenType
from structql.parser.ast_nodes import (
    BinaryLogic,
    Comparison,
    ComparisonOperator,
    Expression,
    LogicalOperator,
    SelectStatement,
)

_COMPARISON_OPERATORS: dict[TokenType, ComparisonOperator] = {
    TokenType.EQ: ComparisonOperator.EQ,
    TokenType.NEQ: ComparisonOperator.NEQ,
    TokenType.LT: ComparisonOperator.LT,
    TokenType.GT: ComparisonOperator.GT,
    TokenType.LE: ComparisonOperator.LE,
    TokenType.GE: ComparisonOperator.GE,
}


def parse(source: str) -> SelectStatement:
    """Tokenize and parse a full query string. The main entry point other
    modules (executor, CLI) should use - they shouldn't need to call
    tokenize() and _Parser themselves."""
    tokens = tokenize(source)
    return _Parser(tokens).parse_select_statement()


class _Parser:
    """Holds parsing position over a fixed token list.

    Named with a leading underscore and kept out of parser/__init__'s
    public surface: callers should use the module-level parse() function
    above, not construct a _Parser directly - that keeps exactly one
    supported entry point into this module.
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # --- grammar rules, one per precedence level -------------------------

    def parse_select_statement(self) -> SelectStatement:
        self._expect(TokenType.SELECT)
        columns = self._parse_column_list()
        self._expect(TokenType.FROM)
        table_name = self._expect(TokenType.IDENTIFIER).text

        where: Expression | None = None
        if self._check(TokenType.WHERE):
            self._advance()
            where = self._parse_or()

        self._expect(TokenType.EOF)
        return SelectStatement(columns=columns, table_name=table_name, where=where)

    def _parse_column_list(self) -> list[str]:
        if self._check(TokenType.STAR):
            self._advance()
            return ["*"]

        columns = [self._expect(TokenType.IDENTIFIER).text]
        while self._check(TokenType.COMMA):
            self._advance()
            columns.append(self._expect(TokenType.IDENTIFIER).text)
        return columns

    def _parse_or(self) -> Expression:
        """or_expr := and_expr (OR and_expr)*  -- loosest precedence."""
        left = self._parse_and()
        while self._check(TokenType.OR):
            self._advance()
            right = self._parse_and()
            left = BinaryLogic(left=left, operator=LogicalOperator.OR, right=right)
        return left

    def _parse_and(self) -> Expression:
        """and_expr := comparison (AND comparison)*  -- binds tighter than OR,
        so nesting and_expr *inside* the OR loop above is what makes
        `A AND B OR C` parse as `(A AND B) OR C`."""
        left = self._parse_comparison()
        while self._check(TokenType.AND):
            self._advance()
            right = self._parse_comparison()
            left = BinaryLogic(left=left, operator=LogicalOperator.AND, right=right)
        return left

    def _parse_comparison(self) -> Expression:
        """comparison := IDENTIFIER comp_op literal  -- the leaf of the tree."""
        column = self._expect(TokenType.IDENTIFIER).text
        operator = self._parse_comparison_operator()
        value = self._parse_literal()
        return Comparison(column=column, operator=operator, value=value)

    def _parse_comparison_operator(self) -> ComparisonOperator:
        token = self._advance()
        operator = _COMPARISON_OPERATORS.get(token.type)
        if operator is None:
            raise ParserError(
                f"Expected a comparison operator (=, !=, <, >, <=, >=) at position "
                f"{token.position}, got {token.type.name} ({token.text!r})"
            )
        return operator

    def _parse_literal(self) -> Value:
        """Consume a QUANTITY, NUMBER, or STRING token and convert it to a
        typed Python value. Quantity parsing is delegated to
        Quantity.parse() (domain/quantity.py) - the single source of truth
        for string -> Quantity conversion, same one the CSV importer uses.
        This is also where an unknown unit (e.g. "35xyz") first surfaces as
        an error, since the lexer deliberately didn't validate units."""
        token = self._advance()
        if token.type == TokenType.QUANTITY:
            try:
                return Quantity.parse(token.text)
            except ValueError as exc:
                raise ParserError(f"Invalid quantity at position {token.position}: {exc}") from None
        if token.type == TokenType.NUMBER:
            return float(token.text)
        if token.type == TokenType.STRING:
            return token.text

        raise ParserError(
            f"Expected a value (quantity, number, or string) at position "
            f"{token.position}, got {token.type.name} ({token.text!r})"
        )

    # --- token stream helpers ---------------------------------------------

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _check(self, token_type: TokenType) -> bool:
        return self._peek().type == token_type

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        # EOF is never consumed past - repeatedly returning it means
        # running off the end of a malformed query surfaces as a normal
        # "unexpected EOF" ParserError rather than an IndexError.
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return token

    def _expect(self, token_type: TokenType) -> Token:
        token = self._peek()
        if token.type != token_type:
            raise ParserError(
                f"Expected {token_type.name} at position {token.position}, "
                f"got {token.type.name} ({token.text!r})"
            )
        return self._advance()
