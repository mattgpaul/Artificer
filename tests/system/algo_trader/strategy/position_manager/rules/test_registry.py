"""Unit tests for PositionRuleRegistry - Position Rule Discovery and Registration.

Tests cover rule discovery, registration, retrieval, and error handling.
All external dependencies are mocked via conftest.py.
"""

from system.algo_trader.strategy.position_manager.rules.registry import (
    PositionRuleRegistry,
    get_registry,
)


class TestPositionRuleRegistryDiscovery:
    """Test position rule discovery functionality."""

    def test_discover_rules_loads_rule_classes(self, mock_logger):
        """Test that rule discovery loads rule classes with rule_type."""
        registry = PositionRuleRegistry()
        rule_types = registry.get_all_rule_types()

        # Should discover at least scaling, stop_loss, and take_profit
        assert "scaling" in rule_types
        assert "stop_loss" in rule_types
        assert "take_profit" in rule_types

    def test_get_rule_class_existing(self, mock_logger):
        """Test getting an existing rule class."""
        registry = PositionRuleRegistry()
        rule_class = registry.get_rule_class("scaling")

        assert rule_class is not None
        assert hasattr(rule_class, "rule_type")
        assert rule_class.rule_type == "scaling"

    def test_get_rule_class_nonexistent(self, mock_logger):
        """Test getting a nonexistent rule class."""
        registry = PositionRuleRegistry()
        rule_class = registry.get_rule_class("nonexistent_rule")

        assert rule_class is None

    def test_get_all_rule_types(self, mock_logger):
        """Test getting all rule types."""
        registry = PositionRuleRegistry()
        rule_types = registry.get_all_rule_types()

        assert isinstance(rule_types, list)
        assert len(rule_types) > 0
        assert all(isinstance(rt, str) for rt in rule_types)


class TestGetRegistry:
    """Test get_registry function."""

    def test_get_registry_returns_singleton(self, mock_logger):
        """Test that get_registry returns a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2
        assert isinstance(registry1, PositionRuleRegistry)

    def test_get_registry_initialized(self, mock_logger):
        """Test that get_registry returns initialized registry."""
        registry = get_registry()

        assert len(registry.get_all_rule_types()) > 0
