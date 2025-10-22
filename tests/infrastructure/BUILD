load("@pip//:requirements.bzl", "requirement")

##### Unit tests #####
py_test(
    name = "influx_test_unit",
    srcs = ["test_runner.py"],
    main = "test_runner.py",
    data = ["influx_test.py"],
    deps = [
        "//infrastructure/influxdb:influxdb",
        requirement("requests"),
        requirement("pandas"),
        requirement("influxdb3-python"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
    args = ["influx_test.py", "-k", "TestInfluxDBClientUnit"],
    tags = [
        "infrastructure", 
        "unit",
    ],
    size = "small",
    visibility = ["//visibility:public"],
)

##### Integration tests #####
py_test(
    name = "influx_test_integration",
    srcs = ["test_runner.py"],
    main = "test_runner.py",
    data = ["influx_test.py"],
    deps = [
        "//infrastructure/influxdb:influxdb",
        requirement("requests"),
        requirement("pandas"),
        requirement("influxdb3-python"),
        requirement("pytest"),
        requirement("pytest-mock"),
    ],
    args = ["influx_test.py", "-k", "TestInfluxDBClientIntegration"],
    tags = [
        "infrastructure", 
        "integration",
    ],
    size = "medium",
    visibility = ["//visibility:public"],
)
