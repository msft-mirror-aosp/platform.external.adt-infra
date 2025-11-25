"""Module to create a pytest which runs a test sequence."""

load("@rules_python//python:defs.bzl", "py_test")

def run_sequence(name, template, template_args = {}):
    """Generates a py_test rule which will run a test sequence.

    Args:
      name: Name of the py_test rule to generate.
      template: Test sequence template file to run.
      template_args: dict of key/value to fill in the template. Values must be a
        tuple (kind, value) where kind is one of str, path, dir, symdir.
    """
    extra_args = []
    extra_deps = []
    if template_args:
        extra_args.append("--template_args")
        for key, (kind, value) in template_args.items():
            extra_args.append(key)
            extra_args.append(kind)
            if kind == "str":
                # NOTE: Despite being a list of strings bazel post processes these
                # arguments so they must be quoted to avoid issues with spaces.
                extra_args.append("'" + value + "'")
            else:
                extra_args.append("$(location " + value + ")")
                extra_deps.append(value)
                if kind != "path":
                    # NOTE: The target of v will refer to a single file, but all must
                    # be present so depend explicitly on the all_files filegroup.
                    extra_deps.append(value.rsplit(":", 1)[0] + ":all_files")

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
        ] + extra_deps,
        main = "run_sequence.py",
        target_compatible_with = select({
            "@platforms//os:macos": ["@platforms//:incompatible"],
            "@platforms//os:windows": ["@platforms//:incompatible"],
            "//conditions:default": [],
        }),
        # TODO(kmagic): Make this configurable.
        size = "large",
    )
