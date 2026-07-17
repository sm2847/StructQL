"""
Chart export: turns a QueryResult into a saved chart image (matplotlib).

Depends only on QueryResult, not on storage or the executor - it doesn't
care whether the data came from CSV or an in-memory table. This keeps
charting swappable (e.g. adding a plotly backend later) without touching
query logic.

Implemented in Milestone M8.
"""
