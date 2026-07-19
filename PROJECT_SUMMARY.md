# StructQL — Project Summary

*A plain-English overview of what this project is, why it exists, and what
it can actually do. See [README.md](README.md) for the technical
documentation (installation, CLI usage, architecture diagrams).*

---

## What it is

StructQL is a small query language — a mini version of SQL — built
specifically for engineering data, where numbers with units (`35MPa`,
`20m`) are treated as first-class values instead of plain numbers with a
unit stapled on afterwards.

## The problem it solves

Structural engineers store inspection, material, and geotechnical data in
spreadsheets. Answering a question like *"which bridges have concrete
strength under 35MPa and were inspected after 2023?"* usually means manual
Excel filtering, or a throwaway script that strips the units off the data
and hopes nothing goes wrong.

StructQL lets you ask that question directly, as a query, and the language
itself understands that `35MPa` is a pressure and `20m` is a length — and
will stop you from comparing the wrong two, rather than silently giving a
meaningless answer:

```sql
SELECT * FROM Bridges
WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023
```

```sql
SELECT * FROM Piles
WHERE Depth > 20m
```

## What you can actually do with it

**1. Query any CSV of engineering (or similar) data.**
Give it a CSV plus a small JSON schema file describing the columns, and
filter it with real logic (`AND`, `OR`, `<`, `>`, `=`, `!=`, `<=`, `>=`)
instead of opening Excel:

```bash
structql query Bridges.csv \
  "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023" \
  --schema Bridges.schema.json
```

**2. Generate charts straight from a query**, with no matplotlib code of
your own to write:

```bash
structql chart Piles.csv "SELECT * FROM Piles WHERE Depth > 20m" \
  --schema Piles.schema.json --x Depth --y CutoffLoad --out piles.png
```

**3. Use it as a real, installed command-line tool** (`structql query`,
`structql chart`) on your own machine, against any dataset that fits the
pattern — it isn't hardcoded to bridges or piles, only to "a CSV of typed
rows, where some columns carry units."

**4. Point to it as a portfolio piece.** This is its main practical purpose
right now: not a tool other engineers are using day-to-day, but a project
that demonstrates real software engineering judgement — designing a small
language, structuring a multi-layer system, making and justifying
trade-offs, and backing it with tests — in a domain (structural
engineering) that only makes sense as a project idea because of your own
background.

## What it deliberately does *not* do (yet)

Being upfront about scope is part of the engineering, not a weakness to
hide:

- No persistence between commands — each `query`/`chart` call re-reads the
  CSV fresh, since v1 storage is in-memory only
- No `JOIN`, `UPDATE`, `DELETE`, or subqueries
- No automatic unit conversion (`20mm` and `20m` won't compare directly)
- No indexing — every query does a full table scan (fine at this data
  scale)

All of these are recorded as "Future Work" in the README, not forgotten
edge cases.

## How the pipeline works, end to end

```
CSV file  +  schema JSON
      │
      ▼
CSV Importer  →  turns "35MPa" into a real Quantity value (not a string)
      │
      ▼
Storage  →  typed rows, held behind a swappable interface
      │
Query string  →  Lexer  →  Parser  →  AST
                                        │
                                        ▼
                                   Executor  →  unit-aware WHERE filtering
                                        │
                                   QueryResult
                                        │
                         ┌──────────────┴──────────────┐
                         ▼                              ▼
                        CLI                          Charts
                  (prints a table)             (saves a PNG via matplotlib)
```

## What's genuinely engineered here, not boilerplate

- **A hand-written parser** (recursive descent) with correct operator
  precedence for `AND`/`OR` — `A AND B OR C` parses as `(A AND B) OR C`,
  the same convention real SQL uses.
- **A type system decision specific to the domain**: `Quantity` and
  `Dimension` exist because generic SQL has no concept of "you can't
  compare a pressure to a length," and this problem does.
- **Deliberate, documented trade-offs**: explicit schemas over
  auto-inference, in-memory storage with an honestly-stated limitation
  instead of a fake persistence layer, no silent unit conversion. The kind
  of judgement call that's easy to skip if you're following a tutorial,
  and worth being able to explain out loud.
- **102 tests** that pin those decisions down — including a test proving
  `20m` and `500mm` can't be compared without an explicit conversion step,
  and one proving a chart refuses to plot a column that secretly mixes
  units.

## How to verify it actually works

```bash
pip install -e ".[dev]"
pytest                    # should show 102 passed, ~98% coverage
ruff check .               # lint
black --check .             # formatting
```

Then run it for real:

```bash
structql query examples/Bridges.csv \
  "SELECT * FROM Bridges WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023" \
  --schema examples/Bridges.schema.json
```

On GitHub, the **Actions** tab should show a green check on the latest
commit — that's the same test suite running independently of your own
machine, which is the actual proof of quality a reviewer trusts.

## The three files worth being able to explain line-by-line

If someone (a recruiter, an interviewer, a curious engineer) asks you to
walk through the code, these three tell the whole story:

1. **`src/structql/domain/quantity.py`** — the core idea: a value that
   knows its own unit and refuses nonsensical comparisons.
2. **`src/structql/parser/parser.py`** — the precedence trick: how nesting
   grammar rules encodes `AND`/`OR` priority without explicit numbers.
3. **`src/structql/engine/executor.py`** — where everything composes:
   parsed query + typed storage + unit-aware comparison, all meeting in
   one place.

## Project history

Built as a milestone-by-milestone project (M0–M9), each with its own git
commit explaining the design decision behind it — see the commit log for
the full story, or the Roadmap section in [README.md](README.md) for the
milestone list.
