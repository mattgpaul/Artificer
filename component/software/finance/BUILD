load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "stock",
    srcs = ["stock.py"],
    deps = [
        requirement("pydantic"),
    ],
    visibility = ["//visibility:public"],
)

load("//:pytest_test.bzl", "pytest_test")
pytest_test(
    name = "finance_test",
    srcs = ["timescale_enum_test.py"],
    deps = [
        "//component/software/finance:finance",
    ],
)
