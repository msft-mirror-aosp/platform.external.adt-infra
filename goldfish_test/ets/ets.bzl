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
            "$(rlocationpath @goldfish//emulator/grpc/security:unsecure-emulator-access)",
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
            "@goldfish//emulator/grpc/security:unsecure-emulator-access",
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
