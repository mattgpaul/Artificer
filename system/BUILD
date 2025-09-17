# system/BUILD

py_library(
    name = "algo-trader",
    deps = [
        "//system/algo-trader:schema",
        "//system/algo-trader/redis:redis_services", 
        "//system/algo-trader/schwab:schwab_services",
        "//system/algo-trader/service:historical_market_service",
        "//system/algo-trader/service:live_market_service",
        "//system/algo-trader/service:market_service_lib",
    ],
    visibility = ["//visibility:private"],
)