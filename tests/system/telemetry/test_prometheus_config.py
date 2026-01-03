"""Unit tests for Prometheus configuration validation.

Tests validate that prometheus.yml parses correctly and contains required
scrape jobs and file_sd_configs.
"""

import os
import yaml
from pathlib import Path

import pytest


def get_repo_root():
    """Get the repository root directory."""
    current = Path(__file__).resolve()
    # Navigate up from tests/system/telemetry/test_prometheus_config.py
    # to repo root
    return current.parent.parent.parent.parent


def load_prometheus_config():
    """Load and parse prometheus.yml."""
    repo_root = get_repo_root()
    config_path = repo_root / "system" / "telemetry" / "prometheus" / "prometheus.yml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def load_target_file(filename):
    """Load and parse a Prometheus target file."""
    repo_root = get_repo_root()
    targets_dir = repo_root / "system" / "telemetry" / "prometheus" / "targets"
    target_path = targets_dir / filename
    with open(target_path) as f:
        return yaml.safe_load(f)


class TestPrometheusConfig:
    """Test Prometheus configuration file structure and content."""

    def test_prometheus_config_parses(self):
        """Test that prometheus.yml is valid YAML."""
        config = load_prometheus_config()
        assert config is not None
        assert isinstance(config, dict)

    def test_prometheus_config_has_global_section(self):
        """Test that prometheus.yml has global configuration."""
        config = load_prometheus_config()
        assert "global" in config
        assert "scrape_interval" in config["global"]
        assert "evaluation_interval" in config["global"]

    def test_prometheus_config_has_scrape_configs(self):
        """Test that prometheus.yml has scrape_configs section."""
        config = load_prometheus_config()
        assert "scrape_configs" in config
        assert isinstance(config["scrape_configs"], list)
        assert len(config["scrape_configs"]) > 0

    def test_node_exporter_scrape_config_exists(self):
        """Test that node-exporter scrape job exists."""
        config = load_prometheus_config()
        scrape_configs = config["scrape_configs"]
        node_exporter_jobs = [job for job in scrape_configs if job.get("job_name") == "node-exporter"]
        assert len(node_exporter_jobs) > 0, "node-exporter scrape job not found"

    def test_node_exporter_uses_file_sd(self):
        """Test that node-exporter job uses file-based service discovery."""
        config = load_prometheus_config()
        scrape_configs = config["scrape_configs"]
        node_exporter_job = next((job for job in scrape_configs if job.get("job_name") == "node-exporter"), None)
        assert node_exporter_job is not None
        assert "file_sd_configs" in node_exporter_job
        assert isinstance(node_exporter_job["file_sd_configs"], list)
        assert len(node_exporter_job["file_sd_configs"]) > 0

    def test_node_exporter_file_sd_has_files(self):
        """Test that file_sd_configs specifies target files."""
        config = load_prometheus_config()
        scrape_configs = config["scrape_configs"]
        node_exporter_job = next((job for job in scrape_configs if job.get("job_name") == "node-exporter"), None)
        assert node_exporter_job is not None
        file_sd_configs = node_exporter_job["file_sd_configs"]
        assert len(file_sd_configs) > 0
        file_sd_config = file_sd_configs[0]
        assert "files" in file_sd_config
        assert isinstance(file_sd_config["files"], list)
        assert len(file_sd_config["files"]) > 0

    def test_prometheus_scrape_config_exists(self):
        """Test that prometheus self-scrape job exists."""
        config = load_prometheus_config()
        scrape_configs = config["scrape_configs"]
        prometheus_jobs = [job for job in scrape_configs if job.get("job_name") == "prometheus"]
        assert len(prometheus_jobs) > 0, "prometheus scrape job not found"

    def test_prometheus_scrape_config_has_static_configs(self):
        """Test that prometheus job uses static_configs."""
        config = load_prometheus_config()
        scrape_configs = config["scrape_configs"]
        prometheus_job = next((job for job in scrape_configs if job.get("job_name") == "prometheus"), None)
        assert prometheus_job is not None
        assert "static_configs" in prometheus_job
        assert isinstance(prometheus_job["static_configs"], list)
        assert len(prometheus_job["static_configs"]) > 0


class TestPrometheusTargetFiles:
    """Test Prometheus file service discovery target files."""

    def test_node_exporters_yaml_parses(self):
        """Test that node-exporters.yaml is valid YAML."""
        targets = load_target_file("node-exporters.yaml")
        assert targets is not None
        assert isinstance(targets, list)

    def test_node_exporters_yaml_has_targets(self):
        """Test that node-exporters.yaml contains target entries."""
        targets = load_target_file("node-exporters.yaml")
        assert len(targets) > 0
        for target in targets:
            assert isinstance(target, dict)
            assert "targets" in target
            assert isinstance(target["targets"], list)
            assert len(target["targets"]) > 0

    def test_node_exporters_yaml_has_labels(self):
        """Test that node-exporters.yaml entries have labels."""
        targets = load_target_file("node-exporters.yaml")
        for target in targets:
            assert "labels" in target
            assert isinstance(target["labels"], dict)
            # Check for common labels
            assert "hostname" in target["labels"]

    def test_node_exporters_yaml_target_format(self):
        """Test that targets are in correct format (host:port)."""
        targets = load_target_file("node-exporters.yaml")
        for target in targets:
            for target_addr in target["targets"]:
                assert isinstance(target_addr, str)
                assert ":" in target_addr, f"Target {target_addr} should be in host:port format"

