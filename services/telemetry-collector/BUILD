load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")

# Industry standard: Clean C++ library with modern standards
cc_library(
    name = "telemetry_collector_lib",
    srcs = glob([
        "src/**/*.cpp",
    ], exclude = ["src/main.cpp"]),
    hdrs = glob([
        "src/**/*.hpp",
    ]),
    # Start with no external dependencies - add only when needed
    includes = ["src"],  # Clean include paths
    visibility = ["//visibility:public"],
    copts = [
        "-std=c++20",        # Modern C++ features
        "-Wall",             # Enable warnings
        "-Wextra",           # Extra warnings  
        "-Werror",           # Treat warnings as errors (industry standard)
    ],
)

# Main executable binary
cc_binary(
    name = "telemetry-collector",
    srcs = ["src/main.cpp"],
    deps = [":telemetry_collector_lib"],
    copts = [
        "-std=c++20",
        "-Wall",
        "-Wextra", 
        "-Werror",
    ],
)