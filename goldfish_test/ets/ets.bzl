"""Macro for running different ETS plans."""

load("@rules_kotlin//kotlin:jvm.bzl", "kt_jvm_test")
load("//sequence:sequence.bzl", "run_sequence")

def _ets_sequence(name, config, args = [], data = [], tags = []):
    run_sequence(
        name = name,
        size = "large",
        srcs = [config],
        args = args + [
            "--tradefed_zip",
            "$(rlocationpath :android_ets_zip)",
        ] + select({
            "@platforms//os:linux": [
                "--abi",
                "x86_64",
                "--build_tools_extract_dir",
                "$(rlocationpath @build-tools-linux//:BUILD.bazel)",
                "--platform_tools_extract_dir",
                "$(rlocationpath @platform-tools-linux//:BUILD.bazel)",
            ],
            "@platforms//os:macos": [
                "--abi",
                "arm64-v8a",
                "--build_tools_extract_dir",
                "$(rlocationpath @build-tools-mac//:BUILD.bazel)",
                "--platform_tools_extract_dir",
                "$(rlocationpath @platform-tools-mac//:BUILD.bazel)",
            ],
        }),
        data = data + [
            ":android_ets_zip",
        ] + select({
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
        exec_properties = {
            "dockerNetwork": "standard",
        },
        main = config,
        tags = tags + [
            # "exclusive-if-local" fails to parallelize on RBE
            # https://github.com/bazelbuild/bazel/issues/17834
            "resources:qemu_instances:1",
            "manual",
            "requires-network",
        ],
        deps = [
            "//sequence:agent_common",
            "//sequence:config",
            "@test_seq//test_seq/proto:test_sequencer_pb2",
        ],
    )

def _boot_normal_config(args, data):
    ret_args = args + [
        "--goldfish_zip",
        "$(rlocationpath @goldfish//emulator:release)",
        "--emulator_access_json",
        "$(rlocationpath @goldfish//emulator/libs/grpc_security:unsecure-emulator-access)",
    ] + select({
        "@platforms//os:linux": [
            "--image_extract_dir",
            "$(rlocationpath @android16k-x86_64//:BUILD.bazel)",
        ],
        "@platforms//os:macos": [
            "--image_extract_dir",
            "$(rlocationpath @android16k-arm64-v8a//:BUILD.bazel)",
        ],
    })
    ret_data = data + [
        "@goldfish//emulator:release",
        "@goldfish//emulator/libs/grpc_security:unsecure-emulator-access",
    ] + select({
        "@platforms//os:linux": [
            "@android16k-x86_64//:BUILD.bazel",
            "@android16k-x86_64//:all_files",
        ],
        "@platforms//os:macos": [
            "@android16k-arm64-v8a//:BUILD.bazel",
            "@android16k-arm64-v8a//:all_files",
        ],
    })
    return ret_args, ret_data

def _boot_local_config(args, data):
    ret_args = args + [
        "--goldfish_zip",
        "$(rlocationpath @local//goldfish:release)",
        "--image_extract_dir",
        "$(rlocationpath @local//image:BUILD.bazel)",
        "--emulator_access_json",
        "$(rlocationpath @goldfish//emulator/libs/grpc_security:unsecure-emulator-access)",
    ]
    ret_data = data + [
        "@goldfish//emulator/libs/grpc_security:unsecure-emulator-access",
        "@local//goldfish:release",
        "@local//image:BUILD.bazel",
        "@local//image:all_files",
    ] + select({
        "@platforms//os:linux": [
            "@android16k-x86_64//:BUILD.bazel",
            "@android16k-x86_64//:all_files",
        ],
        "@platforms//os:macos": [
            "@android16k-arm64-v8a//:BUILD.bazel",
            "@android16k-arm64-v8a//:all_files",
        ],
    })
    return ret_args, ret_data

def ets_boot_emulator(name, config, args = [], data = [], tags = []):
    """Create bazel targets run boot an emulator and run ETS.

    Includes a normal and local override version of the target.

    Args:
        name: The base name of the bazel targets.
        config: The config to use for the ETS.
        args: Additional arguments to pass to the bazel targets.
        data: Additional data to pass to the bazel targets.
        tags: Additional tags to pass to the bazel targets.
    """

    # Normal version which starts an emulator.
    normal_args, normal_data = _boot_normal_config(args, data)
    _ets_sequence(
        name = name,
        config = config,
        args = normal_args,
        data = normal_data,
        tags = tags + [
            "manual",
            "requires-network",
        ],
    )

    # Version which starts an emulator using local overrides (goldfish/img).
    local_args, local_data = _boot_local_config(args, data)
    _ets_sequence(
        name = "local_" + name,
        config = config,
        args = local_args,
        data = local_data,
        tags = tags + [
            "manual",
            "requires-network",
        ],
    )

def ets_external_emulator(name, config, args = [], data = [], tags = []):
    """Runs ETS.

    Args:
        name: The base name of the bazel targets.
        config: The config to use for the ETS.
        args: Additional arguments to pass to the bazel targets.
        data: Additional data to pass to the bazel targets.
        tags: Additional tags to pass to the bazel targets.
    """
    _ets_sequence(
        name = name,
        config = config,
        args = args,
        data = data,
        tags = tags + [
            # Bazel normally runs in a sandbox with a different user id. Local mode will run it as
            # the current user, enabling easier access to the emulator.
            "local",
            "manual",
            "requires-network",
        ],
    )

def ets_plan(name, plan, tags = []):
    """Runs a normal ETS plan with normal/local/external variants.

    Args:
        name: The base name of the bazel targets.
        plan: The ETS plan to run.
        tags: Additional tags to pass to the bazel targets.
    """
    args = [
        "--ets_plan",
        plan,
        "--hellovk_extract_dir",
        "$(rlocationpath @hellovk//:BUILD.bazel)",
    ]
    data = [
        "@hellovk//:BUILD.bazel",
        "@hellovk//:all_files",
    ]
    ets_boot_emulator(
        name = name,
        args = args,
        config = "android_ets_cfg.py",
        data = data,
        tags = tags,
    )
    ets_external_emulator(
        name = "external_" + name,
        args = args,
        config = "external_ets_cfg.py",
        data = data,
        tags = tags,
    )

def _ets_host_module_config_impl(ctx):
    config = """
<configuration description="{}">
  <test class="com.android.tradefed.testtype.HostTest">
    <option name="class" value="{}" />
  </test>
</configuration>
  """
    ctx.actions.write(
        output = ctx.outputs.output_file,
        content = config.format(ctx.attr.description, ctx.attr.class_name),
    )

_ets_host_module_config = rule(
    implementation = _ets_host_module_config_impl,
    attrs = {
        "class_name": attr.string(mandatory = True),
        "description": attr.string(mandatory = True),
        "output_file": attr.output(mandatory = True),
    },
)

def ets_host_test(name, srcs, class_name, description = "", **kwargs):
    """Creates an ETS Host Test.

    This will do the following:
    - Create a tradefed config file <name>.config
    - Create a filegroup named pkg for the config file.
    - Create a kt_jvm_test target for the test using **kwargs.

    Args:
        name: The name of the bazel targets.
        srcs: The source files for the test.
        class_name: The class name of the test.
        description: The description of the test.
        **kwargs: Additional arguments to pass to the kt_jvm_test target.
    """
    output_file = srcs[0].replace(".kt", ".config")
    _ets_host_module_config(
        name = name + "_config",
        class_name = class_name,
        description = description,
        output_file = output_file,
    )
    kt_jvm_test(
        name = name,
        srcs = srcs,
        visibility = ["//ets/java/com/android/tools/e2etests:__pkg__"],
        **kwargs
    )

def ets_pkg(name, srcs):
    """Creates a filegroup for ETS tests.

    Args:
        name: The name of the bazel targets.
        srcs: The source files for the test.
    """
    native.filegroup(
        name = name,
        srcs = srcs,
        visibility = ["//ets:__pkg__"],
        testonly = True,
    )
