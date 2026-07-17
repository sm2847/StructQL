"""
AST node definitions - the query's domain model.

These are deliberately plain dataclasses with no behaviour. A SelectStatement
doesn't know how to execute itself; that would couple parsing to execution
and make both harder to test in isolation. The executor is the only thing
that interprets these nodes.

Implemented in Milestone M5.
"""
