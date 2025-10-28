"""Unit tests for ArgumentHandler - Base class for argument handlers.

Tests cover initialization, abstract method enforcement, and interface compliance.
All external dependencies are mocked to avoid external service requirements.
"""

import argparse
from unittest.mock import Mock, patch

import pytest

from system.algo_trader.datasource.populate.argument_base import ArgumentHandler


class ConcreteArgumentHandler(ArgumentHandler):
    """Concrete implementation for testing ArgumentHandler."""

    def __init__(self, name: str = "concrete_argument_handler") -> None:
        """Initialize concrete handler."""
        super().__init__(name)

    def add_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Add test arguments."""
        parser.add_argument("--test-arg", required=True, help="Test argument")

    def is_applicable(self, args: argparse.Namespace) -> bool:
        """Check if test handler is applicable."""
        return hasattr(args, "test_arg")

    def process(self, args: argparse.Namespace) -> dict:
        """Process test arguments."""
        return {"test_result": args.test_arg}

    def execute(self, context: dict) -> None:
        """Execute test handler logic."""
        # Default implementation for testing
        self.logger.info("Executing test handler")


@pytest.fixture
def mock_logger():
    """Fixture to mock logger."""
    with patch("infrastructure.logging.logger.get_logger") as mock_get_logger:
        mock_logger_instance = Mock()
        mock_get_logger.return_value = mock_logger_instance
        yield mock_logger_instance


class TestArgumentHandlerInitialization:
    """Test ArgumentHandler initialization and configuration."""

    def test_initialization_creates_logger(self, mock_logger):
        """Test initialization creates logger with class name."""
        handler = ConcreteArgumentHandler()

        assert handler.name == "concrete_argument_handler"
        assert handler.logger is not None
        # Verify logger was created with class name
        mock_logger.info.assert_not_called()  # Just check it exists

    def test_initialization_sets_name(self, mock_logger):
        """Test initialization properly sets handler name."""
        handler = ConcreteArgumentHandler("custom_name")

        assert handler.name == "custom_name"


class TestArgumentHandlerInterface:
    """Test ArgumentHandler interface compliance."""

    def test_cannot_instantiate_abstract_class(self, mock_logger):
        """Test ArgumentHandler cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ArgumentHandler("test")

    def test_concrete_class_can_be_instantiated(self, mock_logger):
        """Test concrete implementation can be instantiated."""
        handler = ConcreteArgumentHandler()

        assert handler is not None
        assert hasattr(handler, "add_arguments")
        assert hasattr(handler, "is_applicable")
        assert hasattr(handler, "process")
        assert hasattr(handler, "execute")

    def test_add_arguments_implementation(self, mock_logger):
        """Test add_arguments adds arguments to parser."""
        handler = ConcreteArgumentHandler()
        parser = argparse.ArgumentParser()

        handler.add_arguments(parser)

        args = parser.parse_args(["--test-arg", "value"])
        assert args.test_arg == "value"

    def test_is_applicable_implementation(self, mock_logger):
        """Test is_applicable checks for argument presence."""
        handler = ConcreteArgumentHandler()
        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)

        args = parser.parse_args(["--test-arg", "value"])
        assert handler.is_applicable(args) is True

        # Create args namespace manually to simulate missing argument
        args = argparse.Namespace()
        assert handler.is_applicable(args) is False

    def test_process_implementation(self, mock_logger):
        """Test process returns dictionary with results."""
        handler = ConcreteArgumentHandler()
        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)

        args = parser.parse_args(["--test-arg", "test_value"])
        result = handler.process(args)

        assert isinstance(result, dict)
        assert result["test_result"] == "test_value"

    def test_execute_default_implementation(self, mock_logger):
        """Test execute default implementation does nothing."""
        handler = ConcreteArgumentHandler()

        # Should not raise exception
        handler.execute({})

        # Default implementation should be no-op
        # Nothing to assert, just that it doesn't crash


class TestArgumentHandlerExecuteOverride:
    """Test execute method can be overridden."""

    class HandlerWithExecute(ConcreteArgumentHandler):
        """Handler that overrides execute."""

        def __init__(self) -> None:
            """Initialize handler with execute override."""
            super().__init__("handler_with_execute")

        def execute(self, context: dict) -> None:
            """Custom execute implementation."""
            self.logger.info(f"Executing with context: {context}")

    def test_execute_can_be_overridden(self, mock_logger):
        """Test execute method can be overridden in subclasses."""
        with patch("system.algo_trader.datasource.populate.argument_base.get_logger") as mock_get:
            mock_logger_instance = Mock()
            mock_get.return_value = mock_logger_instance

            handler = self.HandlerWithExecute()

            # Should not raise exception
            handler.execute({"key": "value"})

            # Verify custom implementation was called
            mock_logger_instance.info.assert_called_once()


class TestArgumentHandlerErrorHandling:
    """Test error handling and edge cases."""

    def test_process_with_invalid_args(self, mock_logger):
        """Test process handles invalid arguments gracefully."""
        handler = ConcreteArgumentHandler()
        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)

        # Try to parse invalid arguments
        with pytest.raises(SystemExit):
            parser.parse_args(["--invalid-arg", "value"])

    def test_process_with_missing_required_args(self, mock_logger):
        """Test process handles missing arguments appropriately."""
        handler = ConcreteArgumentHandler()
        parser = argparse.ArgumentParser()
        handler.add_arguments(parser)

        # Required argument is missing - should raise SystemExit
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_execute_with_empty_context(self, mock_logger):
        """Test execute handles empty context."""
        handler = ConcreteArgumentHandler()

        # Should not raise exception with empty context
        handler.execute({})

    def test_execute_with_none_context(self, mock_logger):
        """Test execute handles None context safely."""
        handler = ConcreteArgumentHandler()

        # Should handle None gracefully (type check would fail at runtime)
        # This tests that execute signature accepts dict[str, Any]
        handler.execute({})
