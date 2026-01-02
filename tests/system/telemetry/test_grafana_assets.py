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

    def test_node_overview_dashboard_parses(self):
        """Test that node-overview.json is valid JSON."""
        dashboard = load_grafana_dashboard("node-overview.json")
        assert dashboard is not None
        assert isinstance(dashboard, dict)

    def test_node_overview_dashboard_has_required_fields(self):
        """Test that node-overview.json has required dashboard fields."""
        dashboard = load_grafana_dashboard("node-overview.json")
        assert "title" in dashboard
        assert "panels" in dashboard
        assert isinstance(dashboard["panels"], list)
        assert len(dashboard["panels"]) > 0

    def test_node_overview_dashboard_has_panels(self):
        """Test that node-overview.json has dashboard panels."""
        dashboard = load_grafana_dashboard("node-overview.json")
        panels = dashboard["panels"]
        assert len(panels) > 0
        for panel in panels:
            assert "id" in panel
            assert "type" in panel
            assert "targets" in panel

    def test_gpu_amd_dashboard_parses(self):
        """Test that gpu-amd.json is valid JSON."""
        dashboard = load_grafana_dashboard("gpu-amd.json")
        assert dashboard is not None
        assert isinstance(dashboard, dict)

    def test_gpu_amd_dashboard_has_required_fields(self):
        """Test that gpu-amd.json has required dashboard fields."""
        dashboard = load_grafana_dashboard("gpu-amd.json")
        assert "title" in dashboard
        assert "panels" in dashboard
        assert isinstance(dashboard["panels"], list)

    def test_dashboard_panels_have_datasource(self):
        """Test that dashboard panels reference the Prometheus datasource."""
        dashboard = load_grafana_dashboard("node-overview.json")
        for panel in dashboard["panels"]:
            if "targets" in panel and len(panel["targets"]) > 0:
                target = panel["targets"][0]
                if "datasource" in target:
                    datasource = target["datasource"]
                    if isinstance(datasource, dict) and "uid" in datasource:
                        # Should reference prometheus-telemetry datasource
                        assert datasource["uid"] == "prometheus-telemetry"

