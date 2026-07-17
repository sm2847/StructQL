"""
Centralised exception hierarchy.

Why a single module for this: every layer (lexer, parser, executor, storage)
raises errors that are meaningful to a *user* running a query, not just to a
developer reading a stack trace. Keeping them in one place makes it obvious
what the CLI needs to catch and present nicely, and stops each module from
inventing its own ad-hoc error conventions.
"""


class StructQLError(Exception):
    """Base class for all StructQL errors. Catch this in the CLI's top-level handler."""


class LexerError(StructQLError):
    """Raised when the raw query string contains characters that can't be tokenised."""


class ParserError(StructQLError):
    """Raised when the token stream doesn't form a valid query (syntax error)."""


class SchemaError(StructQLError):
    """Raised when a query or import references a table/column that doesn't exist,
    or a value that doesn't match the declared column type."""


class StorageError(StructQLError):
    """Raised for storage-layer failures (e.g. reading/writing table data)."""
