load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")

oci_image(
    name = "node_exporter_image_lib",
    base = "@node_exporter//:node_exporter",
)

oci_load(
    name = "node_exporter_image",
    image = ":node_exporter_image_lib",
    repo_tags = ["artificer-node-exporter:latest"],
)

# Tarball for release distribution
genrule(
    name = "node_exporter_tarball",
    srcs = [],
    outs = ["artificer-node-exporter.tar"],
    cmd = "$(location :node_exporter_image) && docker save artificer-node-exporter:latest -o $@",
    tags = ["release"],
    tools = [":node_exporter_image"],
)
