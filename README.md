# StructQL

A domain-specific query language for structural engineering datasets — query
CSV exports of bridges, piles, and inspection records the way you'd query a
database, with **engineering units built into the language itself**.

## Why

Structural engineers store inspection, material, and geotechnical data in
spreadsheets. Filtering that data ("find every bridge with concrete strength
below 35MPa") usually means manual Excel filtering or ad-hoc scripts that
throw units away. StructQL treats a quantity like `35MPa` as a first-class
value — not a number that happens to have a unit stapled on afterwards.

## Example

```sql
SELECT * FROM Bridges
WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023
```

```sql
SELECT * FROM Piles
WHERE Depth > 20m
```

```bash
structql import Bridges.csv --table Bridges
structql query "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa"
structql chart "SELECT * FROM Piles" --x Depth --y CutoffLoad --out piles.png
```

## Status

🚧 Early development. See [Roadmap](#roadmap).

## Architecture

```
CSV file (Bridges.csv, Piles.csv)
      │
      ▼
┌──────────────┐   Reads raw strings, applies the table's schema,
│ CSV Importer │   converts "35" + "MPa" into a typed Quantity value.
└──────┬───────┘
       ▼
┌──────────────┐   Typed row storage (in-memory now, file-backed later).
│   Storage    │   The rest of the system depends on this as an
└──────┬───────┘   interface (Protocol), not a concrete implementation.
       ▼
Query string ──▶ Lexer ──▶ Parser ──▶ AST
                                        │
                                        ▼
                                  ┌───────────┐
                                  │  Executor │  Unit-aware WHERE evaluation
                                  └─────┬─────┘  happens here, nowhere else.
                                        ▼
                                  QueryResult
                                        │
                        ┌───────────────┴────────────────┐
                        ▼                                 ▼
                 ┌────────────┐                    ┌────────────┐
                 │    CLI     │                    │   Charts   │
                 └────────────┘                    └────────────┘
```

**Design principle:** parsing, execution, and storage are separate modules
that only talk to each other through small interfaces. The CLI and charting
layer both consume a plain `QueryResult` — neither knows or cares whether the
data came from CSV, an in-memory table, or (eventually) a file-backed store.

## In scope (v1)

- `CREATE`-free schema: schema is inferred/declared at CSV import time
- `SELECT ... FROM ... WHERE ...` with `=, !=, <, >, <=, >=` and `AND`/`OR`
- Typed values: quantities (`35MPa`, `20m`), bare numbers, quoted strings
- CSV import into typed, queryable tables
- CLI (`import`, `query`, `chart`)
- Chart export from query results

## Explicitly out of scope (v1) — Future Work

- JOINs, UPDATE/DELETE, subqueries
- Indexing (v1 does full table scans — fine at this data scale)
- Full date arithmetic (dates are compared as plain years for now)
- Unit conversion between compatible units (e.g. `mm` ↔ `m`) — the type
  system is built to support this later without a redesign

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest
```

## Roadmap

- [x] M0 — Repo scaffolding, README spec, CI, pre-commit
- [ ] M1 — Domain types (`Quantity`, `Unit`, `Row`, `Schema`)
- [ ] M2 — CSV importer
- [ ] M3 — Storage layer
- [ ] M4 — Lexer
- [ ] M5 — Parser
- [ ] M6 — Executor
- [ ] M7 — CLI
- [ ] M8 — Charts
- [ ] M9 — Polish, v1.0.0

## License

MIT
