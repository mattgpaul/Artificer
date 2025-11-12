load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")
load("@rules_python//python:defs.bzl", "py_binary")

py_library(
    name = "bad_ticker_client",
    srcs = ["bad_ticker_client.py"],
    visibility = [
        "//system:__pkg__",
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        "//infrastructure:config",
        "//infrastructure/logging:logger",
        "//infrastructure/sqlite",
    ],
)

py_binary(
    name = "bad_ticker_daemon",
    srcs = ["bad_ticker_daemon.py"],
    main = "bad_ticker_daemon.py",
    visibility = ["//visibility:public"],
    deps = [
        ":bad_ticker_client",
        "//infrastructure/logging:logger",
        "//system/algo_trader/redis:redis_services",
    ],
)

oci_image(
    name = "sqlite_daemon_image_lib",
    base = "@python//:python",
)

oci_load(
    name = "sqlite_daemon_image",
    image = ":sqlite_daemon_image_lib",
    repo_tags = ["artificer-sqlite-daemon:latest"],
)
