load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "bullish",
    srcs = [
        "near_support.py",
    ],
    deps = [
        "//component/software/finance/stock:stock",
        "//infrastructure/logging:logging",
        "//system/trader/strategy:strategy",
        requirement("pandas"),
        requirement("scipy"),
        requirement("numpy"),
    ],
)