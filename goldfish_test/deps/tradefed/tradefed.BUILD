load("@rules_java//java:java_import.bzl", "java_import")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_filegroup", "pkg_files")

package(default_visibility = ["//visibility:public"])

# These jars will be in the android-ets.zip file to support the tradefed built
# in scripts so do not link them into the host test jars as well as this will
# duplicate ~200MB.
java_import(
    name = "tradefed_jars",
    jars = glob(["*.jar"]),
    neverlink = 1,
)

# For unit tests, ensure the jars are linked as these are run from bazel.
java_import(
    name = "tradefed_test_jars",
    testonly = 1,
    jars = glob(["*.jar"]),
)

pkg_files(
    name = "android_ets_files",
    srcs = glob(
        ["*"],
        exclude = [
            "*.sh",
            "*bazel*",
        ],
    ),
    prefix = "android-ets/tools",
)

pkg_files(
    name = "android_ets_bin",
    srcs = glob(
        ["*.sh"],
        exclude = ["script_help.sh"],
    ),
    attributes = pkg_attributes(mode = "0777"),
    prefix = "android-ets/tools",
)

pkg_filegroup(
    name = "android_ets",
    srcs = [
        ":android_ets_bin",
        ":android_ets_files",
    ],
)
