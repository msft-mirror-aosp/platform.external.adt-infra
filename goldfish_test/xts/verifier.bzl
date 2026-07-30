load("//sequence:sequence.bzl", "run_sequence")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")

_KOTLIN_MODULES = [
    "ClockTest",
]

def cts_verifier_tests(name):
    """Creates a set of rules that runs CTS verifier."""
    if not native.existing_rule("use_emu_main_dev_linux_x64"):
        native.config_setting(
            name = "use_emu_main_dev_linux_x64",
            values = {"define": "use_emu_main_dev_linux_x64=true"},
        )

    scripts = native.glob(["verifier/run_*.sh"], allow_empty = True)
    if not scripts:
        # Depending on where the macro is called from, the path might need to be adjusted
        scripts = native.glob(["run_*.sh"], allow_empty = True)
        if scripts:
            # If found without 'verifier/' prefix, prepend it for consistent handling
            scripts = ["verifier/" + s for s in scripts]

    if not scripts:
        fail("Could not find any run_*.sh scripts for CTS Verifier")

    test_specs = []
    for script in scripts:
        script_name = script.split("/")[-1]
        subname = script_name.replace("run_", "").replace(".sh", "")
        test_specs.append(
            struct(
                subname = subname,
                script = script_name,
            ),
        )

    additional_data = [
        "@cts-verifier//:BUILD.bazel",
        "@cts-verifier//:all_files",
    ]

    tests = []
    for test_spec in test_specs:
        test = name + "." + test_spec.subname
        tests.append(test)
        run_sequence(
            name = test,
            srcs = ["verifier_config.py"],
            main = "verifier_config.py",
            args = [
                "--suite",
                "cts-verifier",
                "--apk_dir",
                "$(rlocationpath @cts-verifier//:BUILD.bazel)",
                "--script",
                test_spec.script,
            ] + select({
                ":use_emu_main_dev_linux_x64": [
                    "--goldfish_zip",
                    "$(rlocationpath @emu-main-dev-linux-x64//file)",
                    "--is_prebuilt_emulator",
                ],
                "//conditions:default": [
                    "--goldfish_zip",
                    "$(rlocationpath @goldfish//emulator:release)",
                ],
            }) + select({
                "@platforms//os:linux": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-linux//:BUILD.bazel)",
                    "--image_extract_dir",
                    "$(rlocationpath @android16k-x86_64-user//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-linux//:BUILD.bazel)",
                ],
                "@platforms//os:macos": [
                    "--build_tools_extract_dir",
                    "$(rlocationpath @build-tools-mac//:BUILD.bazel)",
                    "--image_extract_dir",
                    "$(rlocationpath @android16k-arm64-v8a//:BUILD.bazel)",
                    "--platform_tools_extract_dir",
                    "$(rlocationpath @platform-tools-mac//:BUILD.bazel)",
                ],
            }),
            data = select({
                ":use_emu_main_dev_linux_x64": [
                    "@emu-main-dev-linux-x64//file",
                ],
                "//conditions:default": [
                    "@goldfish//emulator:release",
                ],
            }) + native.glob(["verifier/*.py", "verifier/*.sh"], allow_empty = True) + additional_data + select({
                "@platforms//os:linux": [
                    "@android16k-x86_64-user//:BUILD.bazel",
                    "@android16k-x86_64-user//:all_files",
                    "@build-tools-linux//:BUILD.bazel",
                    "@build-tools-linux//:all_files",
                    "@platform-tools-linux//:BUILD.bazel",
                    "@platform-tools-linux//:all_files",
                ],
                "@platforms//os:macos": [
                    "@android16k-arm64-v8a//:BUILD.bazel",
                    "@android16k-arm64-v8a//:all_files",
                    "@build-tools-mac//:BUILD.bazel",
                    "@build-tools-mac//:all_files",
                    "@platform-tools-mac//:BUILD.bazel",
                    "@platform-tools-mac//:all_files",
                ],
            }),
            exec_properties = {
                "dockerNetwork": "standard",
            },
            size = "enormous",
            tags = [
                "manual",
                "requires-network",
            ],
            deps = [
                "//sequence:agent_common",
                "//sequence:config",
                "@test_seq//test_seq/proto:test_sequencer_pb2",
                "@rules_python//python/runfiles",
            ],
        )

    native.test_suite(
        name = name,
        tests = tests,
        tags = ["manual"],
    )


def _ets_verifier_config_impl(ctx):
    config = """
<configuration description="A basic Tradefed test configuration">

  <test class="com.android.tools.testlib.tradefed.ScriptTestRunner">
    <option name="script_args" value="{}" />
  </test>
</configuration>
  """

    ctx.actions.write(
        output = ctx.outputs.output_file,
        content = config.format(ctx.attr.script_path),
    )

_ets_verifier_config = rule(
    implementation = _ets_verifier_config_impl,
    attrs = {
        "script_path": attr.string(mandatory = True),
        "output_file": attr.output(mandatory = True),
    },
)


def ets_verifier(name):
    """Creates a set of rules to generate ETS verifier configs.

    This will create one .config file for each run_*.sh script in the verifier/
    directory, a test rule to run each config, and a test suite to run all
    tests.

    Args:
        name: The name of the overall test suite rule.
    """
    if not native.existing_rule("use_emu_main_dev_linux_x64"):
        native.config_setting(
            name = "use_emu_main_dev_linux_x64",
            values = {"define": "use_emu_main_dev_linux_x64=true"},
        )

    config_rules = []
    test_rules = []
    for script in native.glob(["verifier/run_*.sh"]):
        script_name = script.split("/")[-1]
        base_name = script_name.replace("run_", "").replace(".sh", "")

        _ets_verifier_config(
            name = base_name + "_gen_config",
            script_path = "testcases/" + script_name,
            output_file = base_name + ".config",
        )
        config_rules.append(base_name + ".config")

        test_rules.append(
            ets_verifier_test(
                name = name,
                module = base_name,
            )
        )

    for module in _KOTLIN_MODULES:
        test_rules.append(
            ets_verifier_test(
                name = name,
                module = module,
            )
        )

    pkg_files(
        name = "verifier_ets_configs",
        srcs = config_rules,
    )
    native.test_suite(
        name = name,
        tests = test_rules,
        tags = ["manual"],
    )

def ets_verifier_test(name, module):
    test_name = name + "." + module
    run_sequence(
        name = test_name,
        srcs = ["ets_verifier_config.py"],
        main = "ets_verifier_config.py",
        args = [
            "--module",
            module,
            "--tradefed_zip",
            "$(rlocationpath :android_ets_verifier_zip)",
            "--cts_verifier_extract_dir",
            "$(rlocationpath @cts-verifier//:BUILD.bazel)",
            "--emulator_access_json",
            "$(rlocationpath @goldfish//emulator/libs/grpc_security:unsecure-emulator-access)",
        ] + select({
            ":use_emu_main_dev_linux_x64": [
                "--goldfish_zip",
                "$(rlocationpath @emu-main-dev-linux-x64//file)",
                "--is_prebuilt_emulator",
            ],
            "//conditions:default": [
                "--goldfish_zip",
                "$(rlocationpath @goldfish//emulator:release)",
            ],
        }) + select({
            "@platforms//os:linux": [
                "--abi",
                "x86_64",
                "--build_tools_extract_dir",
                "$(rlocationpath @build-tools-linux//:BUILD.bazel)",
                "--image_extract_dir",
                "$(rlocationpath @android16k-x86_64-user//:BUILD.bazel)",
                "--platform_tools_extract_dir",
                "$(rlocationpath @platform-tools-linux//:BUILD.bazel)",
            ],
            "@platforms//os:macos": [
                "--abi",
                "arm64-v8a",
                "--build_tools_extract_dir",
                "$(rlocationpath @build-tools-mac//:BUILD.bazel)",
                "--image_extract_dir",
                "$(rlocationpath @android16k-arm64-v8a//:BUILD.bazel)",
                "--platform_tools_extract_dir",
                "$(rlocationpath @platform-tools-mac//:BUILD.bazel)",
            ],
        }),
        data = [
            ":android_ets_verifier_zip",
            "@cts-verifier//:BUILD.bazel",
            "@cts-verifier//:all_files",
            "@goldfish//emulator/libs/grpc_security:unsecure-emulator-access",
        ] + select({
            ":use_emu_main_dev_linux_x64": [
                "@emu-main-dev-linux-x64//file",
            ],
            "//conditions:default": [
                "@goldfish//emulator:release",
            ],
        }) + select({
            "@platforms//os:linux": [
                "@android16k-x86_64-user//:BUILD.bazel",
                "@android16k-x86_64-user//:all_files",
                "@build-tools-linux//:BUILD.bazel",
                "@build-tools-linux//:all_files",
                "@platform-tools-linux//:BUILD.bazel",
                "@platform-tools-linux//:all_files",
            ],
            "@platforms//os:macos": [
                "@android16k-arm64-v8a//:BUILD.bazel",
                "@android16k-arm64-v8a//:all_files",
                "@build-tools-mac//:BUILD.bazel",
                "@build-tools-mac//:all_files",
                "@platform-tools-mac//:BUILD.bazel",
                "@platform-tools-mac//:all_files",
            ],
        }),
        exec_properties = {
            "dockerNetwork": "standard",
        },
        size = "enormous",
        tags = [
            "manual",
            "requires-network",
        ],
        deps = [
            "//sequence:agent_common",
            "//sequence:config",
            "@test_seq//test_seq/proto:test_sequencer_pb2",
            "@rules_python//python/runfiles",
        ],
    )
    return test_name
