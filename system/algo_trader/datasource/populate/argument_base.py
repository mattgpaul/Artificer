"""Base class for argument handlers in populate scripts.

This module provides an abstract base class that enforces a consistent
interface for all argument handling modules.
"""

import argparse
from abc import ABC, abstractmethod
from typing import Any

from infrastructure.logging.logger import get_logger


class ArgumentHandler(ABC):
    """Abstract base class for argument handlers.

    Provides a consistent interface for argument parsing and processing.
    Each handler is responsible for:
    1. Adding its arguments to the parser
    2. Determining if it should process based on parsed args
    3. Processing and validating its arguments

    Attributes:
        name: Display name for this argument handler.

    Example:
        >>> class MyHandler(ArgumentHandler):
        ...     def add_arguments(self, parser):
        ...         parser.add_argument("--my-arg")
        ...     def is_applicable(self, args):
        ...         return hasattr(args, "my_arg")
        ...     def process(self, args):
        ...         return {"my_result": args.my_arg}
    """

    def __init__(self, name: str) -> None:
        """Initialize argument handler with a name and logger.

        Args:
            name: Display name for this handler (for logging/debugging).
        """
        self.name = name
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add arguments to the argument parser.

        This method should add the specific arguments this handler
        is responsible for to the parser.

        Args:
            parser: argparse.ArgumentParser instance to add arguments to.
        """
        pass

    @abstractmethod
    def is_applicable(self, args: argparse.Namespace) -> bool:
        """Check if this handler should process the parsed arguments.

        Args:
            args: Parsed arguments from argparse.

        Returns:
            True if this handler should run, False otherwise.
        """
        pass

    @abstractmethod
    def process(self, args: argparse.Namespace) -> dict[str, Any]:
        """Process and validate arguments.

        Args:
            args: Parsed arguments from argparse.

        Returns:
            Dictionary containing processed results. Each key should be
            a unique identifier for the data this handler produces.

        Raises:
            ValueError: If arguments are invalid or processing fails.
        """
        pass

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> None:
        """Execute handler-specific logic with processed arguments.

        This method is called after process() to perform the actual work.
        Default implementation does nothing. Override in subclasses to
        implement specific behavior.

        Args:
            context: Dictionary containing processed results from all handlers.

        Raises:
            ValueError: If execution fails.
        """
        pass
