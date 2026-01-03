filegroup(
    name = "provisioning",
    srcs = glob([
        "provisioning/**/*.yaml",
        "provisioning/**/*.json",
    ]),
    visibility = ["//visibility:public"],
)

# buildifier: disable=native-sh-binary
sh_binary(
    name = "exec",
    srcs = ["grafana_cli.sh"],
    visibility = ["//visibility:public"],
)
