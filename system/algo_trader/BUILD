load("@rules_pkg//:pkg.bzl", "pkg_tar")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

# Project aggregation target - collects all algo_trader components (clean slate)
py_library(
    name = "library",
    tags = [
        "algo_trader",
        "system",
    ],
    visibility = [
        "//system:__pkg__",  # Available to system package
    ],
    deps = [
        "//system/algo_trader/apps",
        "//system/algo_trader/cli",
        "//system/algo_trader/domain",
        "//system/algo_trader/ports",
        "//system/algo_trader/infra/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
    ],
)

pytest_test(
    name = "test_sma_e2e",
    size = "small",
    coverage_path = "system.algo_trader",
    tags = [
        "e2e",
        "integration",
    ],
    test_lib = "//tests/system/algo_trader:test_sma_e2e_lib",
)

# Release images: all OCI image tarballs for this system.
# algo_trader currently has no Bazel-built OCI images; keep this target present
# so the repo's release workflow stays uniform across systems.
filegroup(
    name = "release_images",
    srcs = [],
    visibility = ["//visibility:public"],
)

# Release bundle: a lightweight deploy bundle + manifest template.
genrule(
    name = "release_manifest_template",
    srcs = [],
    outs = ["release_manifest.json.template"],
    cmd = """cat > $@ <<'EOF'
{
  "system": "algo_trader",
  "version": "$${VERSION}",
  "images": [],
  "deploy_files": []
}
EOF""",
)

pkg_tar(
    name = "release_bundle_files",
    srcs = [
        "algo_trader.env",
    ],
    package_dir = "algo_trader",
    strip_prefix = "system/algo_trader",
    visibility = ["//visibility:private"],
)

pkg_tar(
    name = "release_bundle",
    srcs = [":release_manifest_template"],
    package_dir = "algo_trader",
    visibility = ["//visibility:public"],
    deps = [":release_bundle_files"],
)

filegroup(
    name = "release",
    srcs = [
        ":release_bundle",
        ":release_images",
    ],
    visibility = ["//visibility:public"],
)
