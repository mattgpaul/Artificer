"""Unit tests for Grafana provisioning assets validation.

Tests validate that Grafana provisioning YAML files parse correctly
and dashboard JSON files are valid.
"""

import json
from pathlib import Path

import pytest
import yaml


def get_repo_root():
    """Get the repository root directory."""
    current = Path(__file__).resolve()
    # Navigate up from tests/system/telemetry/test_grafana_assets.py
    # to repo root
    return current.parent.parent.parent.parent


def load_grafana_yaml(relative_path):
    """Load and parse a Grafana YAML provisioning file."""
    repo_root = get_repo_root()
    file_path = repo_root / "system" / "telemetry" / "grafana" / "provisioning" / relative_path
    with open(file_path) as f:
        return yaml.safe_load(f)


def load_grafana_dashboard(filename):
    """Load and parse a Grafana dashboard JSON file."""
    repo_root = get_repo_root()
    dashboards_dir = repo_root / "system" / "telemetry" / "grafana" / "provisioning" / "dashboards"
    dashboard_path = dashboards_dir / filename
    with open(dashboard_path) as f:
        return json.load(f)


class TestGrafanaDatasources:
    """Test Grafana datasource provisioning configuration."""

    def test_prometheus_datasource_yaml_parses(self):
        """Test that prometheus.yaml datasource config is valid YAML."""
        config = load_grafana_yaml("datasources/prometheus.yaml")
        assert config is not None
        assert isinstance(config, dict)

    def test_prometheus_datasource_has_api_version(self):
        """Test that datasource config has apiVersion."""
        config = load_grafana_yaml("datasources/prometheus.yaml")
        assert "apiVersion" in config

    def test_prometheus_datasource_has_datasources_list(self):
        """Test that datasource config has datasources list."""
        config = load_grafana_yaml("datasources/prometheus.yaml")
        assert "datasources" in config
        assert isinstance(config["datasources"], list)
        assert len(config["datasources"]) > 0

    def test_prometheus_datasource_config(self):
        """Test that Prometheus datasource is correctly configured."""
        config = load_grafana_yaml("datasources/prometheus.yaml")
        datasources = config["datasources"]
        prometheus_ds = next((ds for ds in datasources if ds.get("name") == "Prometheus"), None)
        assert prometheus_ds is not None
        assert prometheus_ds["type"] == "prometheus"
        assert prometheus_ds["access"] == "proxy"
        assert "url" in prometheus_ds
        assert prometheus_ds.get("isDefault") is True


class TestGrafanaDashboards:
    """Test Grafana dashboard provisioning configuration."""

    def test_dashboard_provider_yaml_parses(self):
        """Test that dashboard-provider.yaml is valid YAML."""
        config = load_grafana_yaml("dashboards/dashboard-provider.yaml")
        assert config is not None
        assert isinstance(config, dict)

    def test_dashboard_provider_has_api_version(self):
        """Test that dashboard provider config has apiVersion."""
        config = load_grafana_yaml("dashboards/dashboard-provider.yaml")
        assert "apiVersion" in config

    def test_dashboard_provider_has_providers_list(self):
        """Test that dashboard provider config has providers list."""
        config = load_grafana_yaml("dashboards/dashboard-provider.yaml")
        assert "providers" in config
        assert isinstance(config["providers"], list)
        assert len(config["providers"]) > 0

    def test_dashboard_provider_config(self):
        """Test that dashboard provider is correctly configured."""
        config = load_grafana_yaml("dashboards/dashboard-provider.yaml")
        providers = config["providers"]
        assert len(providers) > 0
        provider = providers[0]
        assert "name" in provider
        assert "type" in provider
        assert provider["type"] == "file"
        assert "options" in provider
        assert "path" in provider["options"]


class TestGrafanaDashboardJSON:
    """Test Grafana dashboard JSON files."""

    def test_telemetry_overview_dashboard_parses(self):
        """Test that telemetry-overview.json is valid JSON."""
        dashboard = load_grafana_dashboard("telemetry-overview.json")
        assert dashboard is not None
        assert isinstance(dashboard, dict)

    def test_telemetry_overview_dashboard_has_required_fields(self):
        """Test that telemetry-overview.json has required dashboard fields."""
        dashboard = load_grafana_dashboard("telemetry-overview.json")
        assert "title" in dashboard
        assert "panels" in dashboard
        assert isinstance(dashboard["panels"], list)
        assert len(dashboard["panels"]) > 0

    def test_telemetry_overview_dashboard_has_panels(self):
        """Test that telemetry-overview.json has dashboard panels."""
        dashboard = load_grafana_dashboard("telemetry-overview.json")
        panels = dashboard["panels"]
        assert len(panels) > 0
        for panel in panels:
            assert "id" in panel
            assert "type" in panel
            # Not all panel types have targets (e.g., row/text panels).
            if panel["type"] not in {"row", "text"}:
                assert "targets" in panel

    def test_dashboard_panels_have_datasource(self):
        """Test that dashboard panels reference the Prometheus datasource."""
        dashboard = load_grafana_dashboard("telemetry-overview.json")
        for panel in dashboard["panels"]:
            if "targets" in panel and len(panel["targets"]) > 0:
                target = panel["targets"][0]
                if "datasource" in target:
                    datasource = target["datasource"]
                    if isinstance(datasource, dict) and "uid" in datasource:
                        # Should reference prometheus-telemetry datasource
                        assert datasource["uid"] == "prometheus-telemetry"

    def test_telemetry_overview_has_conky_like_sections(self):
        """Test that the dashboard includes Conky-inspired section rows."""
        dashboard = load_grafana_dashboard("telemetry-overview.json")
        row_titles = {p.get("title") for p in dashboard.get("panels", []) if p.get("type") == "row"}
        assert "STATUS" in row_titles
        assert "SYSTEM" in row_titles
        assert "CPU" in row_titles
        assert "GPU" in row_titles
        assert "MEMORY + DISK" in row_titles
        assert "NETWORK" in row_titles
        assert "PROCESSES (optional)" in row_titles

    def test_telemetry_overview_has_process_panels(self):
        """Test that the dashboard includes the top-process tables."""
        dashboard = load_grafana_dashboard("telemetry-overview.json")
        titles = {p.get("title") for p in dashboard.get("panels", [])}
        assert "Top CPU processes (requires processes profile)" in titles
        assert "Top memory processes (requires processes profile)" in titles

