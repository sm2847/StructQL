# StructQL

A domain-specific query language for structural engineering datasets.

## Why
Engineers store inspection, material, and geotechnical data in spreadsheets.
StructQL lets you query it like a database — with units built in.

## Example

SELECT * FROM Bridges
WHERE ConcreteStrength < 35MPa AND InspectionDate > 2023

## Status
Early development — see Roadmap below.

## Architecture
[diagram — added at M8]

## Roadmap
- [ ] CSV import
- [ ] Query lexer/parser
- [ ] Unit-aware execution engine
- [ ] CLI
- [ ] Chart export

