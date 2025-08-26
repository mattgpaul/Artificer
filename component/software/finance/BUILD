py_library(
    name = "finance",
    srcs = [
        "financial_instrument.py",
        "timescale_enum.py",
    ],
    deps = [
        "//infrastructure/logging:logger",
    ],
    visibility = [
        "//component/software/finance:__subpackages__",
        "//infrastructure/client/schwab:__pkg__",
    ],
)

load("//:pytest_test.bzl", "pytest_test")
pytest_test(
    name = "finance_test",
    srcs = ["timescale_enum_test.py"],
    deps = [
        "//component/software/finance:finance",
    ],
)
