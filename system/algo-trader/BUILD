# Project aggregation target - collects all algo-trader components
py_library(
    name = "library",
    deps = [
        "//system/algo-trader/utils:schema",
        "//system/algo-trader/redis:redis_services", 
        "//system/algo-trader/schwab:schwab_services",
        "//system/algo-trader/service:historical_market_service",
        "//system/algo-trader/service:live_market_service",
        "//system/algo-trader/service:market_service_lib",
    ],
    tags = ["algo-trader", "system"],
    visibility = [
        "//system:__pkg__",  # Available to system package
    ],
)
