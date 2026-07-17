"""
Parser: converts a token stream into an AST (ast_nodes.py).

Responsibility boundary: syntax only. The parser checks that a query is
*grammatically* well-formed (e.g. WHERE is followed by a valid condition).
It does not check that a referenced table or column actually exists - that's
a semantic concern, handled by the executor/catalog at execution time.

Implemented in Milestone M5.
"""
