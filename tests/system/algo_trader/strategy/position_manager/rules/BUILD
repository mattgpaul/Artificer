load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_library")
load("//:pytest_test.bzl", "pytest_test")

py_library(
    name = "test_base_lib",
    testonly = True,
    srcs = ["test_base.py"],
    visibility = ["//system/algo_trader/strategy/position_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        "//tests/system/algo_trader/strategy/position_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_pipeline_lib",
    testonly = True,
    srcs = ["test_pipeline.py"],
    visibility = ["//system/algo_trader/strategy/position_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        "//tests/system/algo_trader/strategy/position_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_registry_lib",
    testonly = True,
    srcs = ["test_registry.py"],
    visibility = ["//system/algo_trader/strategy/position_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        "//tests/system/algo_trader/strategy/position_manager:conftest_lib",
        requirement("pytest"),
    ],
)

py_library(
    name = "test_scaling_lib",
    testonly = True,
    srcs = ["test_scaling.py"],
    visibility = ["//system/algo_trader/strategy/position_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        "//tests/system/algo_trader/strategy/position_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_stop_loss_lib",
    testonly = True,
    srcs = ["test_stop_loss.py"],
    visibility = ["//system/algo_trader/strategy/position_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        "//tests/system/algo_trader/strategy/position_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

py_library(
    name = "test_take_profit_lib",
    testonly = True,
    srcs = ["test_take_profit.py"],
    visibility = ["//system/algo_trader/strategy/position_manager:__pkg__"],
    deps = [
        "//system/algo_trader/strategy/position_manager:position_manager_lib",
        "//tests/system/algo_trader/strategy/position_manager:conftest_lib",
        requirement("pandas"),
        requirement("pytest"),
    ],
)

pytest_test(
    name = "test_base",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.rules",
    tags = ["unit"],
    test_lib = ":test_base_lib",
)

pytest_test(
    name = "test_pipeline",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.rules",
    tags = ["unit"],
    test_lib = ":test_pipeline_lib",
)

pytest_test(
    name = "test_registry",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.rules",
    tags = ["unit"],
    test_lib = ":test_registry_lib",
)

pytest_test(
    name = "test_scaling",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.rules",
    tags = ["unit"],
    test_lib = ":test_scaling_lib",
)

pytest_test(
    name = "test_stop_loss",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.rules",
    tags = ["unit"],
    test_lib = ":test_stop_loss_lib",
)

pytest_test(
    name = "test_take_profit",
    size = "small",
    coverage_path = "system.algo_trader.strategy.position_manager.rules",
    tags = ["unit"],
    test_lib = ":test_take_profit_lib",
)

