load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")

oci_image(
    name = "grafana_image_lib",
    base = "@grafana//:grafana",
)

oci_load(
    name = "grafana_image",
    image = ":grafana_image_lib",
    repo_tags = ["artificer-grafana:latest"],
)
