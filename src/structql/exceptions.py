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


class IncompatibleUnitsError(StructQLError):
    """
    Raised when comparing two Quantity values whose units measure different
    things (e.g. comparing a pressure to a length: 35MPa vs 20m).

    This is its own exception rather than a generic SchemaError because it's
    raised at *comparison* time inside Quantity itself (domain/quantity.py),
    not at schema-validation time - the caller may want to handle "nonsense
    comparison" differently from "column doesn't exist".
    """


class ChartError(StructQLError):
    """
    Raised when a QueryResult can't be rendered as a chart: a requested
    axis column doesn't exist in the result, holds non-numeric TEXT
    values, mixes incompatible units within one column (e.g. some rows in
    metres, some in millimetres - plotting the raw numbers together would
    silently produce a misleading chart), or the image can't be written
    to disk.
    """
