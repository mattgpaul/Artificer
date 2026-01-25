load("@rules_python//python:defs.bzl", "py_library")

# Port interfaces library
py_library(
    name = "ports",
    srcs = [
        "account_port.py",
        "controller_port.py",
        "event_port.py",
        "historical_port.py",
        "journal_port.py",
        "order_port.py",
        "portfolio_manager_port.py",
        "quote_port.py",
        "strategy_port.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests/system/algo_trader/domain:__pkg__",
        "//tests/system/algo_trader:__pkg__",
    ],
    deps = [
        "//system/algo_trader/domain:domain_models",
    ],
)

