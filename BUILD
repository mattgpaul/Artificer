load("@pip//:requirements.bzl", "requirement")
load("@rules_python//python:defs.bzl", "py_binary")
load("@rules_python//python:pip.bzl", "compile_pip_requirements")

compile_pip_requirements(
    name = "reqs",
    requirements_in = "requirements.in",
    requirements_txt = "requirements.txt",
    tags = ["unit"],
)

# Export pytest configuration for all tests
exports_files([
    "pytest.ini",
    "ruff.toml",
    "mypy.ini",
])

# Development tools
genrule(
    name = "ruff-gen-osx",
    srcs = ["@ruff-osx-tar//file"],
    outs = ["ruff-osx"],
    cmd = "tar -xzf $< && mv ruff-aarch64-apple-darwin/ruff $@",
    executable = True,
    target_compatible_with = [
        "@platforms//os:osx",
        "@platforms//cpu:arm64",
    ],
)

alias(
    name = "ruff",
    actual = select({
        "@bazel_tools//src/conditions:linux_x86_64": "@ruff-linux//:ruff",
        "@bazel_tools//src/conditions:darwin_arm64": ":ruff-gen-osx",
    }),
    visibility = ["//visibility:public"],
)

genrule(
    name = "buildifier-gen-linux",
    srcs = ["@buildifier-linux//file"],
    outs = ["buildifier-linux-bin"],
    cmd = "cp $< $@ && chmod +x $@",
    executable = True,
    target_compatible_with = [
        "@platforms//os:linux",
        "@platforms//cpu:x86_64",
    ],
)

genrule(
    name = "buildifier-gen-osx",
    srcs = ["@buildifier-osx//file"],
    outs = ["buildifier-osx-bin"],
    cmd = "cp $< $@ && chmod +x $@",
    executable = True,
    target_compatible_with = [
        "@platforms//os:osx",
        "@platforms//cpu:arm64",
    ],
)

alias(
    name = "buildifier",
    actual = select({
        "@bazel_tools//src/conditions:linux_x86_64": ":buildifier-gen-linux",
        "@bazel_tools//src/conditions:darwin_arm64": ":buildifier-gen-osx",
    }),
    visibility = ["//visibility:public"],
)

# Development workflow scripts
sh_binary(
    name = "format",
    srcs = ["scripts/format.sh"],
    data = [
        ":buildifier",
        ":ruff",
    ],
    visibility = ["//visibility:public"],
)

sh_binary(
    name = "lint",
    srcs = ["scripts/lint.sh"],
    data = [
        ":buildifier",
        ":ruff",
    ],
    visibility = ["//visibility:public"],
)
