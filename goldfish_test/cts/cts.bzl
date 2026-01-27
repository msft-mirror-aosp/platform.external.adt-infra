"""Creates a rule that runs CTS."""

load("//sequence:sequence.bzl", "run_sequence")

def deqp_tests(name, submodules = []):
    """Creates a set of rules that runs CTS deqp submodules.

    Args:
      name: The name of the rule
      submodules: A list of submodules to create rules for of the form
          <name>.<submodule>
    """
    test_specs = [
        struct(
            subname = smp,
            args = [
                "--deqp_submodule",
                smp,
            ],
        )
        for smp in submodules
    ]
    cts_test_specs(name, test_specs)

def cts_media_tests(name, modules = []):
    """Creates a set of rules that runs CTS media modules.

    Args:
      name: The name of the rule
      modules: A list of modules to create rules for of the form
          <name>.<module>
    """
    test_specs = [
        struct(
            subname = m,
            args = [
                "--module",
                m,
                "--media_extract_dir",
                "$(rlocationpath @cts-media-1.5//:BUILD.bazel)",
            ],
        )
        for m in modules
    ]
    additional_data = [
        "@cts-media-1.5//:BUILD.bazel",
        "@cts-media-1.5//:all_files",
    ]
    cts_test_specs(name, test_specs, additional_data = additional_data)

def cts_tests(name, modules = []):
    """Creates a set of rules that runs CTS modules.

    Args:
      name: The name of the rule
      modules: A list of modules to create rules for of the form
          <name>.<module>
    """
    test_specs = [struct(subname = m, args = ["--module", m]) for m in modules]
    cts_test_specs(name, test_specs)

def cts_plan(name, plan_glob):
    """Creates a set of rules that runs CTS modules.

    Args:
      name: The name of the rule
      plan_glob: A glob pattern of tests to include.  e.g.
          xts_test_plans/presubmit/**
    """
    additional_data = native.glob([plan_glob])
    test_specs = [
        struct(
            subname = plan_file.split("/")[-1],
            args = ["--plan_path", "$(rlocationpath %s)" % plan_file],
        )
        for plan_file in additional_data
    ]
    cts_test_specs(name, test_specs, additional_data = additional_data)

def cts_test_specs(name, test_specs = [], additional_data = []):
    """Creates a set of rules that runs CTS with a given test specification.

    Args:
      name: The name of the rule
      test_specs: The test spec struct that will be passed to the tradefed agent
      additional_data: Additional data files
    """
    tests = []
    for test_spec in test_specs:
        test = name + "." + test_spec.subname
        tests.append(test)
        run_sequence(
            name = test,
            srcs = ["cts_config.py"],
            main = "cts_config.py",
            args = [
                "--goldfish_zip",
                "$(rlocationpath @goldfish//emulator:release)",
            ] + test_spec.args + select({
                "@platforms//os:linux": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-linux//:BUILD.bazel)",
                    "--image_extract_dir",
                    "$(rlocationpath @android16k-x86_64//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-linux//:BUILD.bazel)",
                    "--tradefed_extract_dir",
                    "$(rlocationpath @cts-x86-64//:BUILD.bazel)",
                ],
                "@platforms//os:macos": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-mac//:BUILD.bazel)",
                    "--image_extract_dir",
                    "$(rlocationpath @android16k-arm64-v8a//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-mac//:BUILD.bazel)",
                    "--tradefed_extract_dir",
                    "$(rlocationpath @cts-arm64//:BUILD.bazel)",
                ],
            }),
            data = [
                "@goldfish//emulator:release",
            ] + additional_data + select({
                "@platforms//os:linux": [
                    "@android16k-x86_64//:BUILD.bazel",
                    "@android16k-x86_64//:all_files",
                    "@build-tools-linux//:BUILD.bazel",
                    "@build-tools-linux//:all_files",
                    "@cts-x86-64//:BUILD.bazel",
                    "@cts-x86-64//:all_files",
                    "@platform-tools-linux//:BUILD.bazel",
                    "@platform-tools-linux//:all_files",
                ],
                "@platforms//os:macos": [
                    "@android16k-arm64-v8a//:BUILD.bazel",
                    "@android16k-arm64-v8a//:all_files",
                    "@build-tools-mac//:BUILD.bazel",
                    "@build-tools-mac//:all_files",
                    "@cts-arm64//:BUILD.bazel",
                    "@cts-arm64//:all_files",
                    "@platform-tools-mac//:BUILD.bazel",
                    "@platform-tools-mac//:all_files",
                ],
            }),
            deps = [
                "//sequence:agent_common",
                "//sequence:config",
                "@test_seq//test_seq/proto:test_sequencer_pb2",
            ],
            size = "enormous",
            # Note: mac platforms may need requires-network for GRPC to work
            tags = ["manual"],
        )

    native.test_suite(
        name = name,
        tests = tests,
        tags = ["manual"],
    )
