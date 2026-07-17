"""
Catalog: tracks table schemas (table name -> column name -> type).

Separated from the executor because "what tables/columns exist" is a
different concern from "how do I evaluate a WHERE clause" - the catalog is
consulted by both the importer (to validate incoming CSV columns) and the
executor (to validate query columns), so it earns its own module.

Implemented in Milestone M2/M6.
"""
