"""Macro for running different ETS plans."""

load("//sequence:sequence.bzl", "run_sequence")

def run_ets(name):
    run_sequence(
        name = name,
        size = "large",
        srcs = ["android_ets_cfg.py"],
        args = [
            "--ets_plan",
            name,
            "--goldfish_zip",
            "$(rlocationpath @goldfish//emulator:release)",
            "--hellovk_extract_dir",
            "$(rlocationpath @hellovk//:BUILD.bazel)",
            "--tradefed_zip",
            "$(rlocationpath :android_ets_zip)",
            "--emulator_access_json",
            "$(rlocationpath @goldfish//emulator/libs/grpc_security:unsecure-emulator-access)",
        ] + select({
            "@platforms//os:linux": [
                "--abi",
                "x86_64",
                "--build_tools_extract_dir",
                "$(rlocationpath @build-tools-linux//:BUILD.bazel)",
                "--image_extract_dir",
                "$(rlocationpath @android16k-x86_64//:BUILD.bazel)",
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
            ":android_ets_zip",
            "@goldfish//emulator:release",
            "@goldfish//emulator/libs/grpc_security:unsecure-emulator-access",
            "@hellovk//:BUILD.bazel",
            "@hellovk//:all_files",
        ] + select({
            "@platforms//os:linux": [
                "@android16k-x86_64//:BUILD.bazel",
                "@android16k-x86_64//:all_files",
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
        main = "android_ets_cfg.py",
        tags = [
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

    run_sequence(
        name = "local_" + name,
        size = "large",
        srcs = ["android_ets_cfg.py"],
        args = [
            "--ets_plan",
            name,
            "--goldfish_zip",
            "$(rlocationpath @local//goldfish:release)",
            "--image_extract_dir",
            "$(rlocationpath @local//image:BUILD.bazel)",
            "--hellovk_extract_dir",
            "$(rlocationpath @hellovk//:BUILD.bazel)",
            "--tradefed_zip",
            "$(rlocationpath :android_ets_zip)",
            "--emulator_access_json",
            "$(rlocationpath @goldfish//emulator/libs/grpc_security:unsecure-emulator-access)",
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
        data = [
            ":android_ets_zip",
            "@local//goldfish:release",
            "@local//image:BUILD.bazel",
            "@local//image:all_files",
            "@goldfish//emulator/libs/grpc_security:unsecure-emulator-access",
            "@hellovk//:BUILD.bazel",
            "@hellovk//:all_files",
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
        main = "android_ets_cfg.py",
        tags = [
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

    run_sequence(
        name = "external_" + name,
        size = "large",
        srcs = ["external_ets_cfg.py"],
        args = [
            "--ets_plan",
            name,
            "--hellovk_extract_dir",
            "$(rlocationpath @hellovk//:BUILD.bazel)",
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
        data = [
            ":android_ets_zip",
            "@hellovk//:BUILD.bazel",
            "@hellovk//:all_files",
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
        main = "external_ets_cfg.py",
        tags = [
            "manual",
            "requires-network",
            # Bazel normally runs in a sandbox with a different user id. Local mode will run it as
            # the current user, enabling easier access to the emulator.
            "local",
        ],
        deps = [
            "//sequence:agent_common",
            "//sequence:config",
            "@test_seq//test_seq/proto:test_sequencer_pb2",
        ],
    )
