# Project aggregation target - collects all algo_trader components
py_library(
    name = "library",
    tags = [
        "algo_trader",
        "system",
    ],
    visibility = [
        "//system:__pkg__",  # Available to system package
    ],
    deps = [
        "//system/algo_trader/redis:redis_services",
        "//system/algo_trader/schwab:schwab_services",
        "//system/algo_trader/service:historical_market_service",
        "//system/algo_trader/service:live_market_service",
        "//system/algo_trader/service:market_service_lib",
        "//system/algo_trader/utils:schema",
    ],
)
