"""Unit tests for FilterRegistry - Filter Discovery and Registration.

Tests cover filter discovery, registration, retrieval, and error handling.
All external dependencies are mocked via conftest.py.
"""

import importlib
from unittest.mock import MagicMock, patch

import pytest

from system.algo_trader.strategy.filters.registry import FilterRegistry, get_registry


class TestFilterRegistryDiscovery:
    """Test filter discovery functionality."""

    def test_discover_filters_loads_filter_classes(self, mock_logger):
        """Test that filter discovery loads filter classes with filter_type."""
        registry = FilterRegistry()
        filter_types = registry.get_all_filter_types()

        # Should discover at least price_comparison and sma_comparison
        assert "price_comparison" in filter_types
        assert "sma_comparison" in filter_types

    def test_discover_filters_handles_import_error(self, mock_logger):
        """Test that discovery handles import errors gracefully."""
        with patch("importlib.import_module", side_effect=ImportError("Module not found")):
            registry = FilterRegistry()
            # Should not raise, just have empty registry
            assert registry.get_all_filter_types() == []

    def test_discover_filters_skips_strategies_module(self, mock_logger):
        """Test that discovery skips .strategies modules."""
        registry = FilterRegistry()
        filter_types = registry.get_all_filter_types()

        # Should not include any .strategies modules
        assert not any(".strategies" in ft for ft in filter_types)

    def test_discover_filters_only_registers_classes_with_filter_type(self, mock_logger):
        """Test that only classes with filter_type attribute are registered."""
        registry = FilterRegistry()

        # All registered filters should have filter_type
        for filter_type in registry.get_all_filter_types():
            filter_class = registry.get_filter_class(filter_type)
            assert hasattr(filter_class, "filter_type")
            assert filter_class.filter_type == filter_type


class TestFilterRegistryRetrieval:
    """Test filter retrieval functionality."""

    def test_get_filter_class_returns_registered_class(self, mock_logger):
        """Test getting a registered filter class."""
        registry = FilterRegistry()
        filter_class = registry.get_filter_class("price_comparison")

        assert filter_class is not None
        assert hasattr(filter_class, "filter_type")
        assert filter_class.filter_type == "price_comparison"

    def test_get_filter_class_returns_none_for_unknown_type(self, mock_logger):
        """Test getting an unknown filter type returns None."""
        registry = FilterRegistry()
        filter_class = registry.get_filter_class("unknown_filter_type")

        assert filter_class is None

    def test_get_all_filter_types_returns_sorted_list(self, mock_logger):
        """Test that get_all_filter_types returns sorted list."""
        registry = FilterRegistry()
        filter_types = registry.get_all_filter_types()

        assert isinstance(filter_types, list)
        # Check that it's sorted
        assert filter_types == sorted(filter_types)


class TestGetRegistry:
    """Test get_registry singleton function."""

    def test_get_registry_returns_singleton(self, mock_logger):
        """Test that get_registry returns the same instance."""
        registry1 = get_registry()
        registry2 = get_registry()

        assert registry1 is registry2

    def test_get_registry_returns_filter_registry_instance(self, mock_logger):
        """Test that get_registry returns FilterRegistry instance."""
        registry = get_registry()

        assert isinstance(registry, FilterRegistry)

    def test_get_registry_has_discovered_filters(self, mock_logger):
        """Test that registry from get_registry has discovered filters."""
        registry = get_registry()
        filter_types = registry.get_all_filter_types()

        assert len(filter_types) > 0

