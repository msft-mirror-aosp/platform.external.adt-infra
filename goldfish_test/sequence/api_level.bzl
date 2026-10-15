"""Helpers for selecting system images and xTS suites by Android API level (29-37)."""

SUPPORTED_API_LEVELS = [29, 30, 31, 32, 33, 34, 35, 36, 37]
DEFAULT_API_LEVEL = 37

def _ensure_api_level_config_settings():
    """Defines per-OS, per-API config_setting targets in the current package if not already defined."""
    for api in SUPPORTED_API_LEVELS:
        linux_name = "linux_api_%d" % api
        if not native.existing_rule(linux_name):
            native.config_setting(
                name = linux_name,
                constraint_values = ["@platforms//os:linux"],
                values = {"define": "api_level=%d" % api},
            )
        macos_name = "macos_api_%d" % api
        if not native.existing_rule(macos_name):
            native.config_setting(
                name = macos_name,
                constraint_values = ["@platforms//os:macos"],
                values = {"define": "api_level=%d" % api},
            )

def sysimg_repo_for_api(api, abi, prefer_user = False):
    """Returns the repository name for the system image at `api` and `abi`.

    Args:
      api: Android API level integer (29..37).
      abi: Target ABI string ("x86_64" or "arm64-v8a").
      prefer_user: Whether to prefer the user build for API 37 x86_64.

    Returns:
      Repository name string for the system image archive.
    """
    if api == 37 and abi == "x86_64" and prefer_user:
        return "sysimg-android-37-x86_64-user"
    return "sysimg-android-%d-%s" % (api, abi)

def cts_repo_for_api(api, abi):
    """Returns the repository name for the CTS archive at `api` and `abi`.

    Args:
      api: Android API level integer (29..37).
      abi: Target ABI string ("x86_64" or "arm64-v8a").

    Returns:
      Repository name string for the CTS archive.
    """
    arch = "x86-64" if abi == "x86_64" else "arm64"
    return "cts-android-%d-%s" % (api, arch)

def cts_verifier_repo_for_api(api, abi):
    """Returns the repository name for the CTS-Verifier archive at `api` and `abi`.

    Args:
      api: Android API level integer (29..37).
      abi: Target ABI string ("x86_64" or "arm64-v8a").

    Returns:
      Repository name string for the CTS-Verifier archive.
    """
    arch = "x86-64" if abi == "x86_64" else "arm64"
    return "cts-verifier-android-%d-%s" % (api, arch)

# buildifier: disable=unnamed-macro
def select_by_os_and_api(
        linux_fn,
        macos_fn,
        api_level = None,
        default_api = DEFAULT_API_LEVEL):
    """Builds a select() over OS and optional `--define api_level=<29..37>`.

    Args:
      linux_fn: Function `fn(api_level) -> list` returning value for Linux at `api_level`.
      macos_fn: Function `fn(api_level) -> list` returning value for macOS at `api_level`.
      api_level: Optional fixed integer API level (29..37). When None, uses config_setting
        targets responding to `--define api_level=<29..37>` with fallback to `default_api`.
      default_api: Default API level when `--define api_level` is not set.

    Returns:
      A Bazel `select()` expression.
    """
    if api_level != None:
        return select({
            "@platforms//os:linux": linux_fn(api_level),
            "@platforms//os:macos": macos_fn(api_level),
        })

    _ensure_api_level_config_settings()
    conditions = {}
    for api in SUPPORTED_API_LEVELS:
        conditions[":linux_api_%d" % api] = linux_fn(api)
        conditions[":macos_api_%d" % api] = macos_fn(api)
    conditions["@platforms//os:linux"] = linux_fn(default_api)
    conditions["@platforms//os:macos"] = macos_fn(default_api)
    return select(conditions)
