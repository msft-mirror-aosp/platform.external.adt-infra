"""Module to create a pytest which runs a test sequence."""

load("@rules_python//python:defs.bzl", "py_test")

def run_sequence(name, template, template_args = {}, template_path_args = {}):
    """Generates a py_test rule which will run a test sequence.

    Args:
      name: Name of the py_test rule to generate.
      template: Test sequence template file to run.
      template_args: dict of key/value to fill in the template.
      template_path_args: dict of key/value to fill in the template where the
        values are bazel labels to be converted to paths.
    """
    extra_args = []
    if template_args:
        extra_args.append("--template_args")
        for i in template_args.items():
            extra_args.extend(i)
    if template_path_args:
        extra_args.append("--template_path_args")
        for k, v in template_path_args.items():
            extra_args.append(k)
            extra_args.append("$(location " + v + ")")

    py_test(
        name = name,
        args = [
            "--test_seq_path",
            "$(location @test_seq_linux//:test_seq)",
            "--seq_path",
            "$(location " + template + ")",
        ] + extra_args,
        srcs = ["@goldfish_test//test_seq:run_sequence.py"],
        data = [
            "@test_seq_linux//:test_seq_files",
            "@test_seq_linux//:test_seq",
            template,
        ] + template_path_args.values(),
        main = "run_sequence.py",
        target_compatible_with = select({
            "@platforms//os:macos": ["@platforms//:incompatible"],
            "@platforms//os:windows": ["@platforms//:incompatible"],
            "//conditions:default": [],
        }),
    )
