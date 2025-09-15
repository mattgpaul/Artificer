load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "market_service_lib",
    srcs = [
        "live_market_service.py",
        "historical_market_service.py",
        "market_base.py",
    ],
    deps = [
        "//system/trader/schwab:schwab_services",
        "//system/trader/redis:redis_services",
        "//system/trader:schema",
        "//infrastructure/logging:logger",
        requirement("pandas"),
        requirement("pydantic"),
    ],
    visibility = [
        "//system/trader:__subpackages__",
    ],
)

py_binary(
    name = "live_market_service",
    srcs = ["live_market_service.py"],
    deps = [":market_service_lib"],
    main = "live_market_service.py",
    visibility = ["//system/trader:__pkg__"],
)

py_binary(
    name = "historical_market_service",
    srcs = ["historical_market_service.py"],
    main = "historical_market_service.py",
    deps = [":market_service_lib"],
    visibility = ["//system/trader:__pkg__"],
)