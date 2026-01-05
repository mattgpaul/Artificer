load("@rules_python//python:defs.bzl", "py_binary", "py_library")

py_library(
    name = "cli",
    srcs = [
        "main.py",
        "override_cli.py",
    ],
    visibility = [
        "//system/algo_trader:__pkg__",
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//system/algo_trader/apps",
        "//system/algo_trader/adapters/redis:redis_adapters",
        "//system/algo_trader/domain",
    ],
)

py_binary(
    name = "algo_trader",
    srcs = ["main.py"],
    main = "main.py",
    visibility = ["//visibility:public"],
    deps = [
        ":cli",
    ],
)

py_binary(
    name = "override_cli",
    srcs = ["override_cli.py"],
    main = "override_cli.py",
    visibility = ["//visibility:public"],
    deps = [
        ":cli",
    ],
)
