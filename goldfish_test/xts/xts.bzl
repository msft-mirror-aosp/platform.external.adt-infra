"""Creates a rule that runs XTS."""

load("//sequence:sequence.bzl", "run_sequence")

def module_subtests(name, suite, module_name, submodules = []):
    """Creates a set of rules that runs submodules for a test module.

    Args:
      name: The name of the rule
      suite: The name of the suite to run
      module_name: The name of the module
      submodules: A list of submodules to create rules for of the form
          <name>.<submodule>
    """
    test_specs = [
        struct(
            subname = smp,
            args = [
                "--module",
                module_name,
                "--submodule",
                smp,
            ],
        )
        for smp in submodules
    ]
    xts_test_specs(name, suite, test_specs)

def deqp_tests(name, submodules = []):
    """Creates a set of rules that runs CTS deqp submodules.

    Args:
      name: The name of the rule
      submodules: A list of submodules to create rules for of the form
          <name>.<submodule>
    """
    module_subtests(name, "cts", "CtsDeqpTestCases", submodules)

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
    xts_test_specs(name, "cts", test_specs, additional_data = additional_data)

def xts_tests(name, suite, modules = []):
    """Creates a set of rules that runs XTS modules.

    Args:
      name: The name of the rule
      suite: The name of the suite to run
      modules: A list of modules to create rules for of the form
          <name>.<module>
    """
    test_specs = [struct(subname = m, args = ["--module", m]) for m in modules]
    xts_test_specs(name, suite, test_specs)

def xts_plan(name, suite, plan_glob):
    """Creates a set of rules that runs XTS modules.

    Args:
      name: The name of the rule
      suite: The name of the suite to run
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
    xts_test_specs(name, suite, test_specs, additional_data = additional_data)

def xts_test_specs(name, suite, test_specs = [], additional_data = []):
    """Creates a set of rules that runs XTS with a given test specification.

    Args:
      name: The name of the rule
      suite: The name of the suite to run
      test_specs: The test spec struct that will be passed to the tradefed agent
      additional_data: Additional data files
    """
    # GTS is does not have two separate builds.
    if suite == "gts":
        linux_suite_repo = "gts"
        mac_suite_repo = "gts"
    else:
        linux_suite_repo = suite + "-x86-64"
        mac_suite_repo = suite + "-arm64"

    tests = []
    for test_spec in test_specs:
        test = name + "." + test_spec.subname
        tests.append(test)
        run_sequence(
            name = test,
            srcs = ["xts_config.py"],
            main = "xts_config.py",
            args = [
                "--suite",
                suite,
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
                    "$(rlocationpath @" + linux_suite_repo +"//:BUILD.bazel)",
                ],
                "@platforms//os:macos": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-mac//:BUILD.bazel)",
                    "--image_extract_dir",
                    "$(rlocationpath @android16k-arm64-v8a//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-mac//:BUILD.bazel)",
                    "--tradefed_extract_dir",
                    "$(rlocationpath @" + mac_suite_repo +"//:BUILD.bazel)",
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
                    "@" + linux_suite_repo + "//:BUILD.bazel",
                    "@" + linux_suite_repo + "//:all_files",
                    "@platform-tools-linux//:BUILD.bazel",
                    "@platform-tools-linux//:all_files",
                ],
                "@platforms//os:macos": [
                    "@android16k-arm64-v8a//:BUILD.bazel",
                    "@android16k-arm64-v8a//:all_files",
                    "@build-tools-mac//:BUILD.bazel",
                    "@build-tools-mac//:all_files",
                    "@" + mac_suite_repo + "//:BUILD.bazel",
                    "@" + mac_suite_repo + "//:all_files",
                    "@platform-tools-mac//:BUILD.bazel",
                    "@platform-tools-mac//:all_files",
                ],
            }),
            deps = [
                "//sequence:agent_common",
                "//sequence:config",
                "@test_seq//test_seq/proto:test_sequencer_pb2",
            ],
            exec_properties = {
                "dockerNetwork": "standard",
            },
            size = "enormous",
            tags = [
                "manual",
                "requires-network",
            ],
        )

        # Version of the tests supporting local overrides.
        run_sequence(
            name = "local_" + test,
            srcs = ["xts_config.py"],
            main = "xts_config.py",
            args = [
                "--goldfish_zip",
                "$(rlocationpath @local//goldfish:release)",
                "--image_extract_dir",
                "$(rlocationpath @local//image:BUILD.bazel)",
                "--tradefed_extract_dir",
                "$(rlocationpath @local//xts:BUILD.bazel)",
            ] + test_spec.args + select({
                "@platforms//os:linux": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-linux//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-linux//:BUILD.bazel)",
                ],
                "@platforms//os:macos": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-mac//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-mac//:BUILD.bazel)",
                ],
            }),
            data = [
                "@local//xts:BUILD.bazel",
                "@local//xts:all_files",
                "@local//goldfish:release",
                "@local//image:BUILD.bazel",
                "@local//image:all_files",
            ] + additional_data + select({
                "@platforms//os:linux": [
                    "@build-tools-linux//:BUILD.bazel",
                    "@build-tools-linux//:all_files",
                    "@platform-tools-linux//:BUILD.bazel",
                    "@platform-tools-linux//:all_files",
                ],
                "@platforms//os:macos": [
                    "@build-tools-mac//:BUILD.bazel",
                    "@build-tools-mac//:all_files",
                    "@platform-tools-mac//:BUILD.bazel",
                    "@platform-tools-mac//:all_files",
                ],
            }),
            deps = [
                "//sequence:agent_common",
                "//sequence:config",
                "@test_seq//test_seq/proto:test_sequencer_pb2",
            ],
            exec_properties = {
                "dockerNetwork": "standard",
            },
            size = "enormous",
            # Note: mac platforms may need requires-network for GRPC to work
            tags = ["manual"],
        )

    native.test_suite(
        name = name,
        tests = tests,
        tags = ["manual"],
    )
    native.test_suite(
        name = "local_" + name,
        tests = ["local_" + t for t in tests],
        tags = ["manual"],
    )

