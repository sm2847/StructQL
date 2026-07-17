"""
Lexer: converts a raw query string into a flat list of Tokens.

Responsibility boundary: the lexer knows nothing about SQL grammar (it
doesn't know that SELECT must be followed by column names). It only knows
how to chop characters into meaningful chunks - keywords, identifiers,
quantities like "35MPa", numbers, strings, and operators. That separation
is what lets us test tokenising and parsing independently.

Implemented in Milestone M4.
"""
