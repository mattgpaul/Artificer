load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library", "rust_test")

rust_library(
    name = "telemetry_collector_lib",
    srcs = glob(["src/**/*.rs"], exclude = ["src/main.rs"]),
    deps = [
        "@crates//:anyhow",
        "@crates//:async-trait",
        "@crates//:chrono", 
        "@crates//:config",
        "@crates//:redis",
        "@crates//:serde",
        "@crates//:serde_json",
        "@crates//:sysinfo",
        "@crates//:thiserror",
        "@crates//:tokio",
        "@crates//:tracing",
        "@crates//:tracing-subscriber",
        "@crates//:uuid",
    ],
    visibility = ["//visibility:public"],
)

rust_binary(
    name = "telemetry-collector",
    srcs = ["src/main.rs"],
    deps = [":telemetry_collector_lib"],
)

rust_test(
    name = "telemetry_collector_test",
    crate = ":telemetry_collector_lib",
)