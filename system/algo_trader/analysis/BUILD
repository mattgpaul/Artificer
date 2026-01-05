load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary", "py_library")

py_library(
    name = "analysis_lib",
    srcs = [
        "dash_app.py",
        "queries.py",
    ],
    visibility = [
        "//system/algo_trader:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//infrastructure/postgres",
        "//system/algo_trader/adapters/redis:redis_adapters",
        "//system/algo_trader/adapters/timescale:timescale_adapters",
        requirement("dash"),
        requirement("pandas"),
        requirement("plotly"),
    ],
)

py_binary(
    name = "dash",
    srcs = ["dash_app.py"],
    main = "dash_app.py",
    visibility = ["//visibility:public"],
    deps = [
        ":analysis_lib",
    ],
)
