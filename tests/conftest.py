"""
Shared test fixtures and utilities.
Provides MockSession for database abstraction in tests.
"""

from __future__ import annotations

import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional


class MockSession:
    """
    In-memory mock database session for testing.

    Mimics SQLAlchemy session behavior without requiring a real database.
    Supports add(), query-like filtering, and basic CRUD operations.
    """

    def __init__(self):
        self._storage: Dict[str, List[Dict[str, Any]]] = {}
        self._objects: Dict[str, Any] = {}

    def add(self, obj: Any) -> None:
        """Add an object to the mock session."""
        if not hasattr(obj, "id"):
            raise ValueError("Object must have an 'id' attribute")

        table_name = obj.__class__.__tablename__ if hasattr(obj, "__tablename__") else obj.__class__.__name__.lower()

        if table_name not in self._storage:
            self._storage[table_name] = []

        # Convert object to dict for storage
        obj_dict = {}
        for attr in dir(obj):
            if not attr.startswith("_") and not callable(getattr(obj, attr)):
                value = getattr(obj, attr)
                if isinstance(value, datetime):
                    obj_dict[attr] = value.isoformat()
                else:
                    obj_dict[attr] = value

        self._storage[table_name].append(obj_dict)
        self._objects[str(obj.id)] = obj

    def query(self, model_class: Any):
        """Return a MockQuery for the given model class."""
        table_name = (
            model_class.__tablename__ if hasattr(model_class, "__tablename__") else model_class.__name__.lower()
        )
        return MockQuery(self, table_name, model_class)

    def commit(self) -> None:
        """Mock commit - no-op for in-memory storage."""
        pass

    def rollback(self) -> None:
        """Mock rollback - no-op for in-memory storage."""
        pass

    def close(self) -> None:
        """Mock close - no-op for in-memory storage."""
        pass

    def get(self, model_class: Any, obj_id: str) -> Optional[Any]:
        """Get an object by ID."""
        return self._objects.get(str(obj_id))

    def delete(self, obj: Any) -> None:
        """Delete an object from the mock session."""
        if not hasattr(obj, "id"):
            raise ValueError("Object must have an 'id' attribute")

        table_name = obj.__class__.__tablename__ if hasattr(obj, "__tablename__") else obj.__class__.__name__.lower()

        if table_name in self._storage:
            self._storage[table_name] = [item for item in self._storage[table_name] if item.get("id") != str(obj.id)]

        if str(obj.id) in self._objects:
            del self._objects[str(obj.id)]

    def refresh(self, obj: Any) -> None:
        """Mock refresh - no-op for in-memory storage."""
        pass


class MockQuery:
    """
    Mock query builder for filtering in-memory data.
    """

    def __init__(self, session: MockSession, table_name: str, model_class: Any):
        self._session = session
        self._table_name = table_name
        self._model_class = model_class
        self._filters: List[tuple] = []

    def filter_by(self, **kwargs: Any) -> MockQuery:
        """Add filter conditions."""
        for key, value in kwargs.items():
            self._filters.append((key, value))
        return self

    def filter(self, *conditions: Any) -> MockQuery:
        """Add filter conditions (SQLAlchemy-style)."""
        # Simplified - just store conditions for now
        self._filters.extend(conditions)
        return self

    def all(self) -> List[Any]:
        """Return all matching objects."""
        data = self._session._storage.get(self._table_name, [])

        results = []
        for item in data:
            match = True
            for key, value in self._filters:
                if item.get(key) != value:
                    match = False
                    break

            if match:
                # Convert back to model instance if possible
                try:
                    obj = self._model_class(**item)
                    results.append(obj)
                except Exception:
                    results.append(item)

        return results

    def first(self) -> Optional[Any]:
        """Return the first matching object."""
        results = self.all()
        return results[0] if results else None

    def one(self) -> Any:
        """Return exactly one matching object."""
        results = self.all()
        if len(results) == 0:
            raise Exception("No results found")
        if len(results) > 1:
            raise Exception("Multiple results found")
        return results[0]

    def count(self) -> int:
        """Return the count of matching objects."""
        return len(self.all())


@pytest.fixture
def mock_session():
    """Provide a fresh MockSession for each test."""
    session = MockSession()
    return session
