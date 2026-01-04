load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")

oci_image(
    name = "prometheus_image_lib",
    base = "@prometheus//:prometheus",
)

oci_load(
    name = "prometheus_image",
    image = ":prometheus_image_lib",
    repo_tags = ["artificer-prometheus:latest"],
)

# Tarball for release distribution
genrule(
    name = "prometheus_tarball",
    srcs = [],
    outs = ["artificer-prometheus.tar"],
    cmd = "$(location :prometheus_image) && docker save artificer-prometheus:latest -o $@",
    local = 1,
    tags = ["release"],
    tools = [":prometheus_image"],
)
