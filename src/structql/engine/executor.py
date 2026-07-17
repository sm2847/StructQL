"""
Executor: runs a validated AST against a StorageEngine and produces a
QueryResult.

This is the business-logic layer. It is the ONLY place unit-aware
comparisons happen (e.g. deciding that 35MPa < 40MPa). It depends on
storage.base.StorageEngine (an interface), never on a concrete storage
implementation - so it can be unit-tested against an in-memory fake with
zero disk I/O, and swapped to a file-backed store later with no changes here.

Implemented in Milestone M6.
"""
