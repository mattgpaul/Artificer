load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "stock",
    srcs = ["stock.py"],
    deps = [
        "//component/software/finance:finance", 
    ],
    visibility = ["//component:__subpackages__"],
)

# py_binary()

load("//:pytest_test.bzl", "pytest_test")
pytest_test(
    name = "stock_test",
    srcs = ["stock_test.py"],
    deps = [
        "//component/software/finance/stock:stock",
        "//component/software/finance:finance",
    ],
)

