load("@pip//:requirements.bzl", "requirement")

py_library(
    name = "market_service_lib",
    srcs = [
        "live_market_service.py",
        "historical_market_service.py",
        "market_base.py",
    ],
    deps = [
        "//system/algo-trader/schwab:schwab_services",
        "//system/algo-trader/redis:redis_services",
        "//system/algo-trader:schema",
        "//infrastructure/logging:logger",
        requirement("pandas"),
        requirement("pydantic"),
    ],
    visibility = [
        "//system/algo-trader:__subpackages__",
        "//system:__pkg__",  # Allow system package access
    ],
)

py_binary(
    name = "live_market_service",
    srcs = ["live_market_service.py"],
    deps = [":market_service_lib"],
    main = "live_market_service.py",
    visibility = [
        "//system/algo-trader:__pkg__",
        "//system:__pkg__",  # Allow system package access
    ],
)

py_binary(
    name = "historical_market_service",
    srcs = ["historical_market_service.py"],
    main = "historical_market_service.py",
    deps = [":market_service_lib"],
    visibility = [
        "//system/algo-trader:__pkg__",
        "//system:__pkg__",  # Allow system package access
    ],
)