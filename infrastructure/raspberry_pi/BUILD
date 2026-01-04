load("@rules_oci//oci:defs.bzl", "oci_image", "oci_load")

oci_image(
    name = "pi3_base_image_lib",
    base = "@debian_bookworm_slim//:debian_bookworm_slim",
)

oci_load(
    name = "pi3_base_image",
    image = ":pi3_base_image_lib",
    repo_tags = ["artificer-pi3-base:latest"],
)
