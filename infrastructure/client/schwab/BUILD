load("@pip//:requirements.bzl", "requirement")
py_library(
    name = "schwab_client",
    srcs = [
        "schwab_client.py",
    ],
    deps = [
        "//component/software/finance:finance",
        "//infrastructure/client:client",
        "//infrastructure/logging:logger",
        requirement("yfinance"),
        requirement("pandas"),
    ],
)