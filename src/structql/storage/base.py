"""
StorageEngine interface (Protocol).

This is the Dependency Inversion boundary of the whole project: the
executor and importer depend on this abstract interface, never on a
concrete storage implementation. That means:
  - Tests use InMemoryStorageEngine (storage/memory.py) - fast, no cleanup.
  - A future file-backed engine can be dropped in without touching the
    executor, importer, or CLI (Open/Closed Principle).

Implemented in Milestone M3.
"""
