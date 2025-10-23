load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")

compile_pip_requirements(
    name = "reqs",
    requirements_in = "requirements.in",
    requirements_txt = "requirements.txt",
    tags = ["unit"],
)

# Export pytest configuration for all tests
exports_files([
    "pytest.ini",
    "ruff.toml",
    "mypy.ini",
])
