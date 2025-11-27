"""Unit tests for PriceComparisonFilter - Price Comparison Filter.

Tests cover initialization, evaluation, comparison operators, and error handling.
All external dependencies are mocked via conftest.py.
"""

from system.algo_trader.strategy.filters.base import BaseComparisonFilter
from system.algo_trader.strategy.filters.price_comparison import PriceComparisonFilter


class TestPriceComparisonFilterInitialization:
    """Test PriceComparisonFilter initialization."""

    def test_initialization_success(self, mock_logger):
        """Test initialization with valid parameters."""
        filter_instance = PriceComparisonFilter(
            field="price", operator=">", value=100.0, logger=mock_logger
        )

        assert filter_instance.field == "price"
        assert filter_instance.operator == ">"
        assert filter_instance.value == 100.0
        assert filter_instance.logger == mock_logger

    def test_initialization_inherits_from_base(self, mock_logger):
        """Test that PriceComparisonFilter inherits from BaseComparisonFilter."""
        filter_instance = PriceComparisonFilter(
            field="price", operator=">", value=100.0, logger=mock_logger
        )

        assert isinstance(filter_instance, BaseComparisonFilter)

    def test_initialization_without_logger(self):
        """Test initialization without logger creates default logger."""
        filter_instance = PriceComparisonFilter(field="price", operator=">", value=100.0)

        assert filter_instance.logger is not None


class TestPriceComparisonFilterEvaluation:
    """Test PriceComparisonFilter evaluation logic."""

    def test_evaluate_greater_than_success(self, filter_context, mock_logger):
        """Test evaluation with > operator succeeds when field > value."""
        filter_instance = PriceComparisonFilter(
            field="price", operator=">", value=100.0, logger=mock_logger
        )
        filter_context.signal["price"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is True

    def test_evaluate_greater_than_failure(self, filter_context, mock_logger):
        """Test evaluation with > operator fails when field <= value."""
        filter_instance = PriceComparisonFilter(
            field="price", operator=">", value=200.0, logger=mock_logger
        )
        filter_context.signal["price"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is False

    def test_evaluate_less_than_success(self, filter_context, mock_logger):
        """Test evaluation with < operator succeeds when field < value."""
        filter_instance = PriceComparisonFilter(
            field="price", operator="<", value=200.0, logger=mock_logger
        )
        filter_context.signal["price"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is True

    def test_evaluate_less_than_failure(self, filter_context, mock_logger):
        """Test evaluation with < operator fails when field >= value."""
        filter_instance = PriceComparisonFilter(
            field="price", operator="<", value=100.0, logger=mock_logger
        )
        filter_context.signal["price"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is False

    def test_evaluate_equal_success(self, filter_context, mock_logger):
        """Test evaluation with == operator succeeds when field == value."""
        filter_instance = PriceComparisonFilter(
            field="price", operator="==", value=150.0, logger=mock_logger
        )
        filter_context.signal["price"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is True

    def test_evaluate_not_equal_success(self, filter_context, mock_logger):
        """Test evaluation with != operator succeeds when field != value."""
        filter_instance = PriceComparisonFilter(
            field="price", operator="!=", value=100.0, logger=mock_logger
        )
        filter_context.signal["price"] = 150.0

        result = filter_instance.evaluate(filter_context)

        assert result is True

    def test_evaluate_missing_field_returns_false(self, filter_context, mock_logger):
        """Test evaluation when field is missing returns False."""
        filter_instance = PriceComparisonFilter(
            field="missing_field", operator=">", value=100.0, logger=mock_logger
        )

        result = filter_instance.evaluate(filter_context)

        assert result is False
        mock_logger.debug.assert_called()

    def test_evaluate_non_numeric_field_returns_false(self, filter_context, mock_logger):
        """Test evaluation when field value is not numeric returns False."""
        filter_instance = PriceComparisonFilter(
            field="price", operator=">", value=100.0, logger=mock_logger
        )
        filter_context.signal["price"] = "not_a_number"

        result = filter_instance.evaluate(filter_context)

        assert result is False
        mock_logger.debug.assert_called()

    def test_evaluate_none_field_returns_false(self, filter_context, mock_logger):
        """Test evaluation when field value is None returns False."""
        filter_instance = PriceComparisonFilter(
            field="price", operator=">", value=100.0, logger=mock_logger
        )
        filter_context.signal["price"] = None

        result = filter_instance.evaluate(filter_context)

        assert result is False


class TestPriceComparisonFilterFromConfig:
    """Test PriceComparisonFilter.from_config class method."""

    def test_from_config_success(self, mock_logger):
        """Test creating filter from valid config."""
        params = {"field": "price", "operator": ">", "value": 100.0}
        result = PriceComparisonFilter.from_config(params, mock_logger)

        assert result is not None
        assert isinstance(result, PriceComparisonFilter)
        assert result.field == "price"
        assert result.operator == ">"
        assert result.value == 100.0

    def test_from_config_missing_field(self, mock_logger):
        """Test from_config with missing field parameter."""
        params = {"operator": ">", "value": 100.0}
        result = PriceComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_missing_operator(self, mock_logger):
        """Test from_config with missing operator parameter."""
        params = {"field": "price", "value": 100.0}
        result = PriceComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_missing_value(self, mock_logger):
        """Test from_config with missing value parameter."""
        params = {"field": "price", "operator": ">"}
        result = PriceComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_non_numeric_value(self, mock_logger):
        """Test from_config with non-numeric value."""
        params = {"field": "price", "operator": ">", "value": "not_a_number"}
        result = PriceComparisonFilter.from_config(params, mock_logger)

        assert result is None
        mock_logger.error.assert_called()

    def test_from_config_string_numeric_value(self, mock_logger):
        """Test from_config with string numeric value converts to float."""
        params = {"field": "price", "operator": ">", "value": "100.5"}
        result = PriceComparisonFilter.from_config(params, mock_logger)

        assert result is not None
        assert result.value == 100.5
