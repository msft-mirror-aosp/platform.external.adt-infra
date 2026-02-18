"""Module extension which loads the OS specific test_sequencer."""

_local_dir_build = """
package(default_visibility = ["//visibility:public"])

filegroup(
    name = "all_files",
    srcs = glob(["**/*"]),
)
"""

_alias_dir_build = """
package(default_visibility = ["//visibility:public"])
alias(
    name = "BUILD.bazel",
    actual = "{label}:BUILD.bazel",
)
alias(
    name = "all_files",
    actual = "{label}:all_files",
)
"""

_goldfish_build = """
package(default_visibility = ["//visibility:public"])
alias(
    name = "release",
    actual = "{label}:release",
)
"""

def _local_impl(repo_ctx):
    """Local override repository.

    This repository will contain cts, goldfish and image targets that use the local version if
    present otherwise the gcs_archive version. One oddity is that the supporting code uses the
    BUILD.bazel file from the gcs_archive as a reference to get to the top-level directory of the
    extracted files. To support aliasing this to a different BUILD.bazel file, the build file
    cannot be named BUILD.bazel or a name conflict arises. Therefore, in the alias case, BUILD is
    used instead.
    """

    # Defaults are OS specific.
    goldfish_label = "@goldfish//emulator"
    if "linux" in repo_ctx.os.name or "windows" in repo_ctx.os.name:
        cts_label = "@cts-x86-64//"
        image_label = "@android16k-x86_64//"
    elif "mac" in repo_ctx.os.name:
        cts_label = "@cts-arm64//"
        image_label = "@android16k-arm64//"
    else:
        fail("Unsupported os name: " + repo_ctx.os.name)

    # Now look for any local overrides.
    base_path = repo_ctx.workspace_root.get_child("third_party/adt-infra/goldfish_test/deps/local")

    # The supporting code expects cts and the system image to be pre-extracted. To save the user
    # a step, this code will extract the zip if it finds one.
    if _check_for_zip_and_extract(repo_ctx, base_path, "cts"):
        repo_ctx.file("cts/BUILD.bazel", _local_dir_build)
    else:
        repo_ctx.file("cts/BUILD", _alias_dir_build.format(label = cts_label))

    if _check_for_zip_and_extract(repo_ctx, base_path, "image"):
        repo_ctx.file("image/BUILD.bazel", _local_dir_build)
    else:
        repo_ctx.file("image/BUILD", _alias_dir_build.format(label = image_label))

    # The goldfish target is always expected to be a zip file, so it is always aliased.
    if _get_local_zip(base_path, "goldfish") != None:
        goldfish_label = "@goldfish_test//deps/local/goldfish"
    repo_ctx.file("goldfish/BUILD", _goldfish_build.format(label = goldfish_label))

def _get_local_zip(base_path, name):
    zips = [p for p in base_path.get_child(name).readdir() if p.basename.endswith(".zip")]
    if len(zips) > 1:
        fail("Multiple zip files found in {} directory!".format(name))
    elif len(zips) == 1:
        return zips[0]
    return None

def _check_for_zip_and_extract(repo_ctx, base_path, name):
    local_zip = _get_local_zip(base_path, name)
    if local_zip != None:
        repo_ctx.extract(local_zip, output = name)
        return True
    return False

local = repository_rule(
    implementation = _local_impl,
    configure = True,
    local = True,
)
