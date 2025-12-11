load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")

py_library(
    name = "conftest_lib",
    testonly = True,
    srcs = ["conftest.py"],
    visibility = [
        "//system/algo_trader/influx/publisher:__pkg__",
        "//tests/system/algo_trader/influx/publisher:__pkg__",
    ],
    deps = [
        "//system/algo_trader/influx/publisher:publisher_modules",
        "//tests/system/algo_trader/influx:conftest_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_queue_processor_lib",
    testonly = True,
    srcs = ["test_queue_processor.py"],
    visibility = ["//system/algo_trader/influx/publisher:__pkg__"],
    deps = [
        "//system/algo_trader/influx/publisher:publisher_modules",
        "//tests/system/algo_trader/influx:conftest_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_config_lib",
    testonly = True,
    srcs = ["test_config.py"],
    visibility = ["//system/algo_trader/influx/publisher:__pkg__"],
    deps = [
        ":conftest_lib",
        "//system/algo_trader/influx/publisher:publisher_modules",
        "//tests/system/algo_trader/influx:conftest_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_main_lib",
    testonly = True,
    srcs = ["test_main.py"],
    visibility = ["//system/algo_trader/influx/publisher:__pkg__"],
    deps = [
        "//system/algo_trader/influx/publisher:publisher_main",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_publisher_lib",
    testonly = True,
    srcs = ["test_publisher.py"],
    visibility = ["//system/algo_trader/influx/publisher:__pkg__"],
    deps = [
        "//system/algo_trader/influx/publisher:publisher_service",
        "//tests/system/algo_trader/influx:conftest_lib",
        requirement("pytest"),
    ],
)
