"""
CSV importer: reads a CSV file + column type declarations and produces
typed rows in a StorageEngine.

This is where the string "35MPa" first becomes a Quantity value - type
conversion happens once, at the boundary where untyped external data enters
the system. Nothing downstream ever has to re-parse a raw string.

Implemented in Milestone M2.
"""
