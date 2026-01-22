"""Module extension which loads the OS specific test_sequencer."""

load("@rules_gcs//gcs:repo_rules.bzl", "gcs_archive")

_build_file = """package(default_visibility = ["//visibility:public"])

filegroup(
    name = "test_seq_files",
    srcs = glob(["test_seq/**"]),
)

filegroup(
    name = "test_seq",
    srcs = select({
      "@platforms//os:windows": ["test_seq/test_seq.exe"],
      "//conditions:default": ["test_seq/test_seq"],
    }),
)
"""

def _test_seq_extension_impl(module_ctx):
    root_modules = [m for m in module_ctx.modules if m.is_root]
    if len(root_modules) > 1:
        fail("Expected at most one root module, found {}".format(", ".join([x.name for x in root_modules])))

    if root_modules:
        module = root_modules[0]
    else:
        module = module_ctx.modules[0]

    os_tags = None
    if "linux" in module_ctx.os.name:
        os_tags = module.tags.linux[0]
    elif "mac" in module_ctx.os.name:
        os_tags = module.tags.macos[0]
    elif "windows" in module_ctx.os.name:
        os_tags = module.tags.windows[0]
    if not os_tags:
        fail("Unsupported OS {}".format(module_ctx.os.name))
    gcs_archive(
        name = "test_seq",
        build_file_content = _build_file,
        sha256 = os_tags.sha256,
        url = os_tags.url,
    )
    return module_ctx.extension_metadata(reproducible = True)

_archive_tags = tag_class(attrs = {
    "sha256": attr.string(),
    "url": attr.string(),
})

test_seq_extension = module_extension(
    implementation = _test_seq_extension_impl,
    os_dependent = True,
    tag_classes = {
        "linux": _archive_tags,
        "macos": _archive_tags,
        "windows": _archive_tags,
    },
)
