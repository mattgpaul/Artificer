load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "stock",
    srcs = ["stock.py"],
    deps = [
        "//component/software/finance:financial_instrument", 
        requirement("yfinance"),
        requirement("pandas"),
    ],
    visibility = ["//component:__subpackages__"],
)

# py_binary()

load("//:pytest_test.bzl", "pytest_test")

pytest_test(
    name = "stock_test",
    srcs = ["stock_test.py"],
    deps = [
        ":stock",
        requirement("pytest"),
        requirement("pytest-mock"),
        requirement("pytest-cov"), 
        requirement("pytest-bazel"),
        requirement("pandas"),
    ],
)

