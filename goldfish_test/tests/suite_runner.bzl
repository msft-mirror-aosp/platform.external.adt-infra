"""Generates a repository rule to run ets against the given emulator."""

load("@rules_gcs//gcs:repo_rules.bzl", "gcs_archive")

def _ets_repo_impl(rctx):
    build_content = """load("@goldfish_test//test_seq:test_seq.bzl", "run_sequence")
run_sequence(
  name = "run",
  template = "@goldfish_test//tests/ets:android_ets_templ",
  template_args = {{
    "goldfish_zip": ("path", "{}"),
    "image_extract_dir": ("dir", "@android_minigbm16k-x86_64//:BUILD.bazel"),
    "platform_tools_extract_dir": ("dir", "@platform-tools-linux//:BUILD.bazel"),
    "build_tools_extract_dir": ("dir", "@build-tools-linux//:BUILD.bazel"),
    "android_ets_zip": ("path", "@goldfish_test//tests/ets:android_ets_zip"),
    "ets_plan_xml": ("path", "@goldfish_test//tests/ets:ets_plans"),
  }},
)
""".format(rctx.attr.goldfish_zip)

    rctx.file("run/BUILD.bazel", build_content)

def _generic_build():
    """Generic BUILD file contents for a gcs_archive which includes all files."""
    return """package(default_visibility = ["//visibility:public"])
filegroup(
  name = "all_files",
  srcs = glob(["**/*"]),
)
"""

def _run_suite_impl(mctx):
    """Generates a repository to run ets: @repo_name//ets:run"""
    gcs_archive(
        name = "build-tools-linux",
        build_file_content = _generic_build(),
        sha256 = "321e687caa570210bf4acd80e8cfbe901d17368d83f51976ccbba3656093fe2b",
        url = "gs://emu-next-bazel/ab/aosp-sdk-release/sdk/13278306/sdk-repo-linux-build-tools-13278306.zip",
    )
    gcs_archive(
        name = "platform-tools-linux",
        build_file_content = _generic_build(),
        sha256 = "5c377d32e7ba0c1f982417ec588c33d8e379141e806c46c2de26cf42fe6ed51e",
        url = "gs://emu-next-bazel/ab/aosp-sdk-release/sdk/13278306/sdk-repo-linux-platform-tools-13278306.zip",
    )
    gcs_archive(
        name = "android_minigbm16k-x86_64",
        build_file_content = _generic_build(),
        sha256 = "2f98e9fdc3c1e51f302eff758de57a531911d725b86bfd0b608f364603992010",
        url = "gs://emu-next-bazel/sys-img/sdk_gphone16k_x86_64_minigbm-userdebug/sdk-repo-linux-system-images-14339737.zip",
    )

    for mod in mctx.modules:
        for ets in mod.tags.ets:
            create_ets_repo(name = ets.name, goldfish_zip = ets.goldfish_zip)

run_suite = module_extension(
    implementation = _run_suite_impl,
    tag_classes = {
        "ets": tag_class(attrs = {"name": attr.string(), "goldfish_zip": attr.label()}),
    },
)

create_ets_repo = repository_rule(
    implementation = _ets_repo_impl,
    attrs = {"goldfish_zip": attr.label(default = None, mandatory = True)},
)
