load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "schwab_client",
    srcs = [
        "schwab_client.py",
    ],
    deps = [
        "//infrastructure/client:client",
        "//infrastructure/logging:logger",
        requirement("requests"),
        requirement("python-dotenv"),
    ],
    visibility = [
        "//infrastructure/client:__subpackages__",
        "//component/software/finance:__subpackages__",
        "//system:__subpackages__",
    ],
)

py_binary(
    name = "schwab_client_main",
    srcs = ["schwab_client.py"],
    deps = [":schwab_client"],
    main = "schwab_client.py",
)

