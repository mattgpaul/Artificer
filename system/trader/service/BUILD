load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "live_market_service_lib",
    srcs = [
        "live_market_service.py",
    ],
    deps = [
        "//system/trader/schwab:schwab_services",
        "//system/trader/redis:redis_services",
        "//component/software/finance:schema",
        "//infrastructure/logging:logger",
        requirement("pydantic"),
    ],
    visibility = [
        "//system/trader:__subpackages__",
    ],
)

py_binary(
    name = "live_market_service_bin",
    srcs = ["live_market_service.py"],
    deps = [":live_market_service_lib"],
    main = "live_market_service.py",
    visibility = ["//system/trader:__pkg__"],
)