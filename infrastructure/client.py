"""Abstract base class for all client implementations.

This module provides the Client ABC that serves as a marker interface for
all client implementations in the infrastructure layer, ensuring consistent
client abstraction patterns across the codebase.
"""

from abc import ABC


class Client(ABC):  # noqa: B024
    """Abstract base class for client implementations.

    This ABC serves as a marker interface for all client classes, providing
    a common type for dependency injection and type checking. Concrete
    implementations should inherit from this class.

    Note: This is intentionally a marker interface with no abstract methods.
    """

    ...
