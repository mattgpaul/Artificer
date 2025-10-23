load("@rules_python//python:defs.bzl", "py_library")

# Test library for Schema models
py_library(
    name = "test_schema_lib",
    srcs = ["test_schema.py"],
    deps = [
        "//system/algo_trader/utils:schema",
    ],
    testonly = True,
    visibility = ["//system/algo_trader/utils:__pkg__"],
)

