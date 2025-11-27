"""Unit tests for PortfolioManager config loader.

Tests cover config file loading, rule creation, and error handling.
All external dependencies are mocked via conftest.py.
"""

from unittest.mock import MagicMock, patch

import yaml

from system.algo_trader.strategy.portfolio_manager.config_loader import (
    load_portfolio_manager_config,
)


class TestLoadPortfolioManagerConfig:
    """Test load_portfolio_manager_config function."""

    def test_load_config_none_returns_none(self):
        """Test loading None config returns None."""
        result = load_portfolio_manager_config(None)
        assert result is None

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file returns None."""
        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
        ) as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            result = load_portfolio_manager_config("nonexistent_config", mock_logger)

            assert result is None
            mock_logger.error.assert_called()

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML file returns None."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("invalid: yaml: content: [unclosed")

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("invalid", mock_logger)

                assert result is None
                mock_logger.error.assert_called()

    def test_load_config_not_dict(self, tmp_path):
        """Test loading config that is not a dictionary returns None."""
        config_file = tmp_path / "not_dict.yaml"
        config_file.write_text("- item1\n- item2\n")

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("not_dict", mock_logger)

                assert result is None
                mock_logger.error.assert_called()

    def test_load_config_rules_not_list(self, tmp_path):
        """Test loading config with rules not a list returns None."""
        config_file = tmp_path / "rules_not_list.yaml"
        config_file.write_text("rules: not a list\n")

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("rules_not_list", mock_logger)

                assert result is None
                mock_logger.error.assert_called()

    def test_load_config_valid_max_capital_deployed(self, tmp_path):
        """Test loading valid config with max_capital_deployed rule."""
        config_file = tmp_path / "valid_max_capital.yaml"
        config_dict = {
            "rules": [
                {
                    "max_capital_deployed": {
                        "max_deployed_pct": 0.5,
                    },
                },
            ],
        }
        config_file.write_text(yaml.dump(config_dict))

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("valid_max_capital", mock_logger)

                assert result is not None
                assert len(result.rules) == 1
                assert result.rules[0].max_deployed_pct == 0.5
                mock_logger.info.assert_called()

    def test_load_config_valid_fractional_position_size(self, tmp_path):
        """Test loading valid config with fractional_position_size rule."""
        config_file = tmp_path / "valid_fractional.yaml"
        config_dict = {
            "rules": [
                {
                    "fractional_position_size": {
                        "fraction_of_equity": 0.01,
                    },
                },
            ],
        }
        config_file.write_text(yaml.dump(config_dict))

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("valid_fractional", mock_logger)

                assert result is not None
                assert len(result.rules) == 1
                assert result.rules[0].fraction_of_equity == 0.01
                mock_logger.info.assert_called()

    def test_load_config_multiple_rules(self, tmp_path):
        """Test loading config with multiple rules."""
        config_file = tmp_path / "multiple_rules.yaml"
        config_dict = {
            "rules": [
                {
                    "max_capital_deployed": {
                        "max_deployed_pct": 0.5,
                    },
                },
                {
                    "fractional_position_size": {
                        "fraction_of_equity": 0.01,
                    },
                },
            ],
        }
        config_file.write_text(yaml.dump(config_dict))

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("multiple_rules", mock_logger)

                assert result is not None
                assert len(result.rules) == 2
                mock_logger.info.assert_called()

    def test_load_config_unknown_rule_type(self, tmp_path):
        """Test loading config with unknown rule type."""
        config_file = tmp_path / "unknown_rule.yaml"
        config_dict = {
            "rules": [
                {
                    "unknown_rule": {
                        "param": "value",
                    },
                },
            ],
        }
        config_file.write_text(yaml.dump(config_dict))

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("unknown_rule", mock_logger)

                assert result is None
                mock_logger.warning.assert_called()

    def test_load_config_empty_rules_list(self, tmp_path):
        """Test loading config with empty rules list."""
        config_file = tmp_path / "empty_rules.yaml"
        config_dict = {"rules": []}
        config_file.write_text(yaml.dump(config_dict))

        with patch(
            "system.algo_trader.strategy.portfolio_manager.config_loader._resolve_config_path"
        ) as mock_resolve:
            mock_resolve.return_value = config_file
            with patch(
                "system.algo_trader.strategy.portfolio_manager.config_loader.get_logger"
            ) as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = load_portfolio_manager_config("empty_rules", mock_logger)

                assert result is None
                mock_logger.warning.assert_called()

