load("@rules_python//python:pip.bzl", "compile_pip_requirements")

compile_pip_requirements(
    name = "reqs",
    requirements_in = "requirements.in",
    requirements_txt = "requirements.txt",
)

# Export pytest configuration for all tests
exports_files([
    "pytest.ini",
])