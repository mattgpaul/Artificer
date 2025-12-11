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
        "//system/algo_trader/config:config",
        "//system/algo_trader/infra/database/redis:redis_services",
        "//system/algo_trader/infra/broker/schwab:schwab_services",
        "//system/algo_trader/service/market_data:market_data_lib",
        "//system/algo_trader/utils:schema",
    ],
)
