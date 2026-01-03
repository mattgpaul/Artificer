load("@rules_python//python:defs.bzl", "py_library")

# Test library for Schema models
py_library(
    name = "test_schema_lib",
    testonly = True,
    srcs = ["test_schema.py"],
    visibility = ["//system/algo_trader/utils:__pkg__"],
    deps = [
        "//system/algo_trader/utils:schema",
    ],
)
