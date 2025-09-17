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

# Integration tests for algo-trader use tag filtering (cleanest, zero-maintenance solution)
# 
# Commands for your local-first workflow:
#   Unit tests:        bazel test //... --test_tag_filters=algo-trader --test_arg="-m" --test_arg="unit"  
#   Integration tests: bazel test //... --test_tag_filters=algo-trader --test_arg="-m" --test_arg="integration"
#   E2E tests:         bazel test //... --test_tag_filters=algo-trader --test_arg="-m" --test_arg="e2e"
#
# Discover tests:      bazel query "attr('tags', 'algo-trader', kind(py_test, //...))"