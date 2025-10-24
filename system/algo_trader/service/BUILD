load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "market_service_lib",
    srcs = [
        "historical_market_service.py",
        "live_market_service.py",
        "market_base.py",
    ],
    visibility = [
        "//system:__pkg__",  # Allow system package access
        "//system/algo_trader:__subpackages__",
    ],
    deps = [
        "//infrastructure/logging:logger",
        "//system/algo_trader:config",
        "//system/algo_trader/influx:influx_services",
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
        "//system/algo_trader/utils:schema",
        requirement("pandas"),
        requirement("pydantic"),
    ],
)

py_binary(
    name = "live_market_service",
    srcs = ["live_market_service.py"],
    main = "live_market_service.py",
    visibility = [
        "//system:__pkg__",  # Allow system package access
        "//system/algo_trader:__pkg__",
    ],
    deps = [":market_service_lib"],
)

py_binary(
    name = "historical_market_service",
    srcs = ["historical_market_service.py"],
    main = "historical_market_service.py",
    visibility = [
        "//system:__pkg__",  # Allow system package access
        "//system/algo_trader:__pkg__",
    ],
    deps = [":market_service_lib"],
)
