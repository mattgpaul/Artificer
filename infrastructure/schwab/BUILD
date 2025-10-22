load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab",
    srcs = ["schwab.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "schwab_authenticate",
    srcs = ["schwab.py"],
    main = "schwab.py",
    deps = [
        ":schwab",
    ],
    visibility = ["//visibility:public"],
)
