load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "redis_client",
    srcs = ["redis_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("redis"),
    ],
    visibility = ["//visibility:public"],
)

py_library(
    name = "schwab_client",
    srcs = ["schwab_client.py"],
    deps = [
        "//infrastructure:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("python-dotenv"),
    ],
    visibility = ["//visibility:public"],
)

py_binary(
    name = "authenticate",
    srcs = ["schwab_client.py"],
    main = "schwab_client.py",
    deps = [
        ":schwab_client",
    ],
    visibility = ["//visibility:public"],
)
