"""Module to create a pytest which runs a test sequence."""

load("@rules_python//python:defs.bzl", "py_test")

def run_sequence(name, srcs, args = [], data = [], **kwargs):
    """Generates py_test rules to print and run a test sequence.

    The printed sequence is meant for manual inspection only, due to sandboxing
    the paths only exist while the rule is running.

    Args:
      name: Name of the py_test rule to generate.
      srcs: List of src files.
      args: List of args to pass to the test.
      data: List of data dependencies. NOTE: If you are using pre-extracted
        directories, both the :BUILD.bazel and :all_files rules must be here.
      **kwargs: Passed directly to the pytest rules.
    """

    py_test(
        name = name,
        args = args + [
            "--mode=run",
            "--test_seq_path",
            "$(rlocationpath @test_seq//:test_seq)",
            "--java_path",
            "$(rlocationpaths @rules_java//toolchains:remotejdk_21)",
        ],
        srcs = srcs,
        data = data + [
            "@test_seq//:test_seq",
            "@test_seq//:test_seq_files",
            "@rules_java//toolchains:remotejdk_21",
        ],
        toolchains = ["@rules_java//toolchains:remotejdk_21"],
        target_compatible_with = select({
            "//conditions:default": [],
            "@platforms//os:windows": ["@platforms//:incompatible"],
        }),
        **kwargs
    )

    # NOTE: The print test below just prints the config, so manually set the
    # size to small.
    kwargs["size"] = "small"

    # NOTE: name has the suffix _print added, which will break the test if main
    # isn't specified.
    kwargs.setdefault("main", name + ".py")
    py_test(
        name = name + "_print",
        args = args + [
            "--mode=print",
            "--test_seq_path",
            "$(rlocationpath @test_seq//:test_seq)",
        ],
        srcs = srcs,
        data = data + [
            "@test_seq//:test_seq",
            "@test_seq//:test_seq_files",
        ],
        target_compatible_with = select({
            "//conditions:default": [],
            "@platforms//os:windows": ["@platforms//:incompatible"],
        }),
        **kwargs
    )
