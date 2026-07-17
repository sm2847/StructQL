"""
Command-line interface.

Deliberately thin: this module's only job is argument parsing and wiring
together the importer / storage / executor / chart modules. No business
logic lives here — if you're tempted to write an if/else about query
semantics in this file, it belongs in engine/executor.py instead.

Implemented in Milestone M7.
"""

import typer

app = typer.Typer(help="StructQL: query structural engineering CSVs like a database.")


if __name__ == "__main__":
    app()
