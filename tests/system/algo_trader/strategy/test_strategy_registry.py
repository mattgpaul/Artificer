"""Unit tests for StrategyRegistry - Strategy Discovery and Registration.

Tests cover strategy discovery, registration, retrieval, CLI argument registration,
and strategy creation. All external dependencies are mocked via conftest.py.
"""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.strategy.strategy import Side, Strategy
from system.algo_trader.strategy.strategy_registry import (
    StrategyRegistry,
    _class_name_to_cli_name,
    get_registry,
)


class TestClassNameToCLIName:
    """Test _class_name_to_cli_name function."""

    def test_sma_crossover(self):
        """Test converting SMACrossover to sma-crossover."""
        assert _class_name_to_cli_name("SMACrossover") == "sma-crossover"

    def test_ema_crossover(self):
        """Test converting EMACrossover to ema-crossover."""
        assert _class_name_to_cli_name("EMACrossover") == "ema-crossover"

    def test_my_custom_strategy(self):
        """Test converting MyCustomStrategy to my-custom-strategy."""
        assert _class_name_to_cli_name("MyCustomStrategy") == "my-custom-strategy"

    def test_rsi_strategy(self):
        """Test converting RSIStrategy to rsi-strategy."""
        assert _class_name_to_cli_name("RSIStrategy") == "rsi-strategy"

    def test_single_word(self):
        """Test converting single word class name."""
        assert _class_name_to_cli_name("Strategy") == "strategy"


class TestStrategyRegistryDiscovery:
    """Test strategy discovery functionality."""

    def test_discover_strategies_loads_strategy_classes(self):
        """Test that strategy discovery loads strategy classes."""
        registry = StrategyRegistry()
        strategy_names = registry.get_all_strategy_names()

        # Should discover at least sma-crossover and ema-crossover
        assert "sma-crossover" in strategy_names
        assert "ema-crossover" in strategy_names

    def test_get_strategy_class_existing(self):
        """Test getting an existing strategy class."""
        registry = StrategyRegistry()
        strategy_class = registry.get_strategy_class("sma-crossover")

        assert strategy_class is not None
        assert issubclass(strategy_class, Strategy)

    def test_get_strategy_class_nonexistent(self):
        """Test getting a nonexistent strategy class."""
        registry = StrategyRegistry()
        strategy_class = registry.get_strategy_class("nonexistent-strategy")

        assert strategy_class is None

    def test_get_all_strategy_names(self):
        """Test getting all strategy names."""
        registry = StrategyRegistry()
        strategy_names = registry.get_all_strategy_names()

        assert isinstance(strategy_names, list)
        assert len(strategy_names) > 0
        assert all(isinstance(name, str) for name in strategy_names)


class TestStrategyRegistryCreation:
    """Test strategy creation functionality."""

    def test_create_strategy_from_args(self):
        """Test create_strategy from CLI arguments."""
        registry = StrategyRegistry()

        args = argparse.Namespace(side="LONG", window=60, short=5, long=15)
        strategy = registry.create_strategy("sma-crossover", args)

        assert strategy is not None
        assert strategy.side == Side.LONG
        assert strategy.window == 60

    def test_create_strategy_unknown_raises(self):
        """Test create_strategy with unknown strategy raises ValueError."""
        registry = StrategyRegistry()

        args = argparse.Namespace()
        with pytest.raises(ValueError, match="Unknown strategy"):
            registry.create_strategy("nonexistent-strategy", args)

    def test_create_strategy_from_params(self):
        """Test create_strategy_from_params."""
        registry = StrategyRegistry()

        strategy = registry.create_strategy_from_params(
            "sma-crossover", {"side": "LONG", "window": 60, "short": 5, "long": 15}
        )

        assert strategy is not None
        assert strategy.side == Side.LONG
        assert strategy.window == 60

    def test_create_strategy_from_params_class_name(self):
        """Test create_strategy_from_params with class name."""
        registry = StrategyRegistry()

        strategy = registry.create_strategy_from_params(
            "SMACrossover", {"side": "LONG", "window": 60, "short": 5, "long": 15}
        )

        assert strategy is not None
        assert strategy.side == Side.LONG

    def test_create_strategy_from_params_side_string(self):
        """Test create_strategy_from_params converts side string to enum."""
        registry = StrategyRegistry()

        strategy = registry.create_strategy_from_params(
            "sma-crossover", {"side": "SHORT", "short": 5, "long": 15}
        )

        assert strategy is not None
        assert strategy.side == Side.SHORT

    def test_create_strategy_from_params_unknown_raises(self):
        """Test create_strategy_from_params with unknown strategy raises ValueError."""
        registry = StrategyRegistry()

        with pytest.raises(ValueError, match="Unknown strategy type"):
            registry.create_strategy_from_params("nonexistent-strategy", {})


class TestStrategyRegistryCLI:
    """Test CLI argument registration."""

    def test_register_cli_arguments(self):
        """Test register_cli_arguments registers arguments for all strategies."""
        registry = StrategyRegistry()

        subparsers = argparse.ArgumentParser().add_subparsers(dest="strategy")
        parser_factory = subparsers.add_parser

        registry.register_cli_arguments(subparsers, parser_factory)

        # Should have created parsers for all strategies
        assert len(subparsers._name_parser_map) > 0

    def test_registered_parser_has_strategy_args(self):
        """Test registered parser has strategy-specific arguments."""
        registry = StrategyRegistry()

        subparsers = argparse.ArgumentParser().add_subparsers(dest="strategy")
        parser_factory = subparsers.add_parser

        registry.register_cli_arguments(subparsers, parser_factory)

        # Parse arguments for a known strategy
        parser = subparsers._name_parser_map.get("sma-crossover")
        if parser:
            args = parser.parse_args(["--short", "5", "--long", "15"])
            assert args.short == 5
            assert args.long == 15


class TestGetRegistry:
    """Test get_registry function."""

    def test_get_registry_returns_singleton(self):
        """Test that get_registry returns a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2
        assert isinstance(registry1, StrategyRegistry)

    def test_get_registry_initialized(self):
        """Test that get_registry returns initialized registry."""
        registry = get_registry()

        assert len(registry.get_all_strategy_names()) > 0

