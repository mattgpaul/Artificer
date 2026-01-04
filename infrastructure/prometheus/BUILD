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
