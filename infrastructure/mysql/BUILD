load("@pip//:requirements.bzl", "requirement")
load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "mysql",
    srcs = ["mysql.py"],
    visibility = [
        "//tests/infrastructure/mysql:__pkg__",
        "//visibility:public",
    ],
    deps = [
        "//infrastructure:client",
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        requirement("pymysql"),
    ],
)

# Test target
pytest_test(
    name = "test_mysql",
    coverage_path = "infrastructure.mysql",
    tags = ["unit"],
    test_lib = "//tests/infrastructure/mysql:test_mysql_lib",
)

oci_image(
    name = "mysql_image_lib",
    base = "@mysql//:mysql",
)

oci_load(
    name = "mysql_image",
    image = ":mysql_image_lib",
    repo_tags = ["artificer-mysql:latest"],
)

# Tarball for release distribution
genrule(
    name = "mysql_tarball",
    srcs = [],
    outs = ["artificer-mysql.tar"],
    cmd = "$(location :mysql_image) && docker save artificer-mysql:latest -o $@",
    local = 1,
    tags = ["release"],
    tools = [":mysql_image"],
)
