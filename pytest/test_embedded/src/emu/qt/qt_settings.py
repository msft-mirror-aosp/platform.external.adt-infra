# Copyright 2024 - The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import configparser
import json
import logging
import os
import platform
import plistlib
import subprocess
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List


class SettingsError(Exception):
    """Base exception for all settings-related errors."""


class AccessError(SettingsError):
    """Raised when there are permission issues or file access problems."""


class FormatError(SettingsError):
    """Raised when there are problems with file format or parsing."""


class ValidationError(SettingsError):
    """Raised when settings values fail validation."""


class KeyError(SettingsError):
    """Raised when a settings key is not found."""


class SyncError(SettingsError):
    """Raised when settings cannot be synchronized to storage."""


class Format(Enum):
    NativeFormat = "native"
    IniFormat = "ini"
    JsonFormat = "json"


class Scope(Enum):
    UserScope = "user"
    SystemScope = "system"


class Status(Enum):
    NoError = 0
    AccessError = 1
    FormatError = 2


class CaseSensitiveConfigParser(configparser.RawConfigParser):
    """
    A case-sensitive configuration parser.

    This class inherits from `configparser.RawConfigParser` but overrides the
    `optionxform` method to preserve the case of option names.

    This is useful when you need to maintain case-sensitivity for option names
    in your configuration files.

    Example:
        >>> config = CaseSensitiveConfigParser()
        >>> config.read('config.ini')
        >>> value = config.get('Section', 'optionName')  # Preserves 'optionName' case
    """

    def optionxform(self, optionstr):
        return optionstr  # Return the option name as is


class QSettings:
    """
    A class for managing application settings, similar to the QT QSettings class

    Provides a platform-independent way to store and retrieve settings
    in various formats, including native formats, INI, and JSON.

    Supports hierarchical grouping of settings and arrays.

    Attributes:
        organization (str): The name of the organization associated with the settings.
        application (str): The name of the application associated with the settings.
        format (Format): The format of the settings file.
        scope (Scope): The scope of the settings (user or system).

    Example:
        >>> settings = QSettings(organization="MyOrg", application="MyApp")
        >>> settings["username"] = "johndoe"
        >>> username = settings["username"]
        >>> print(username)
        johndoe
    """

    def __init__(
        self,
        organization: str = "",
        domain: str = "",
        application: str = "",
        settings_format: Format = Format.NativeFormat,
        scope: Scope = Scope.UserScope,
    ):
        if not organization:
            raise ValidationError("Organization name cannot be empty")

        self.organization = organization
        self._domain = domain
        self.application = application
        self.format = settings_format
        self.scope = scope
        self._data: Dict[str, Any] = {}
        self._current_group: List[str] = []
        self._current_array: List[str] = []
        self._array_index: int = -1
        self._status = Status.NoError
        if application:
            self._domain += f".{application}"

        try:
            self._load_settings()
        except Exception as e:
            raise AccessError(f"Failed to initialize settings: {str(e)}")

    def _get_settings_path(self) -> Path:
        """Determine the appropriate settings file path based on platform, scope and format."""
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                if self.format == Format.NativeFormat:
                    if self.scope == Scope.UserScope:
                        base_path = Path.home() / "Library" / "Preferences"
                    else:
                        base_path = Path("/Library/Preferences")
                    return base_path / f"{self._domain}.plist"

            elif system == "Linux":  # Unix-like systems
                if self.scope == Scope.UserScope:
                    base_path = Path.home() / ".config"
                else:
                    base_path = Path("/etc/xdg")

            else:  # Windows
                if self.scope == Scope.UserScope:
                    base_path = Path(os.getenv("APPDATA", ""))
                    if not base_path:
                        raise AccessError("Could not determine user settings directory")
                else:
                    base_path = Path(os.getenv("PROGRAMDATA", ""))
                    if not base_path:
                        raise AccessError(
                            "Could not determine system settings directory"
                        )

            # For non-native formats or non-macOS systems
            extension = {
                Format.NativeFormat: "conf",
                Format.IniFormat: "ini",
                Format.JsonFormat: "json",
            }[self.format]

            filename = (
                f"{self.application}.{extension}"
                if self.application
                else f"{self.organization}.{extension}"
            )
            return base_path / self.organization / filename

        except Exception as e:
            raise AccessError(f"Failed to determine settings path: {str(e)}")

    def _load_settings(self) -> None:
        """Load settings from file based on format and platform."""
        path = self._get_settings_path()
        try:
            if platform.system() == "Darwin" and self.format == Format.NativeFormat:
                self._load_macos_settings()
            else:
                self._load_regular_settings(path)
        except AccessError:
            raise
        except FormatError:
            raise
        except Exception as e:
            raise FormatError(f"Unexpected error loading settings: {str(e)}")

    def _load_macos_settings(self) -> None:
        """Load settings from macOS property list format."""
        path = self._get_settings_path()
        try:
            if path.exists():
                with open(path, "rb") as f:
                    try:
                        self._data = plistlib.load(f)
                    except plistlib.InvalidFileException as e:
                        raise FormatError(f"Invalid plist file: {str(e)}")
            else:
                # Try to read from macOS defaults system
                try:
                    result = subprocess.run(
                        ["defaults", "read", self._domain],
                        capture_output=True,
                        text=True,
                        check=False,
                    )
                    if result.returncode == 0:
                        try:
                            self._data = ast.literal_eval(result.stdout)
                        except (SyntaxError, ValueError) as e:
                            raise FormatError(
                                f"Invalid defaults data format: {str(e)}"
                            ) from e
                except subprocess.CalledProcessError as e:
                    logging.warning("Failed to read to defaults from system: %s", e)
                    self._data = {}
        except (AccessError, FormatError):
            raise
        except Exception as e:
            raise AccessError(
                f"Unexpected error accessing macOS settings: {str(e)}"
            ) from e

    def _load_regular_settings(self, path: Path) -> None:
        """Load settings from non-native format files."""
        try:
            if self.format == Format.JsonFormat:
                with open(path, "r", encoding="utf-8") as f:
                    try:
                        self._data = json.load(f)
                    except json.JSONDecodeError as e:
                        raise FormatError(f"Invalid JSON format: {str(e)}") from e
            else:
                config = CaseSensitiveConfigParser()
                try:
                    config.read(path)
                    self._data = {
                        section: dict(config[section]) for section in config.sections()
                    }
                except configparser.Error as e:
                    raise FormatError(f"Invalid format: {str(e)}") from e
        except (AccessError, FormatError):
            raise
        except Exception as e:
            raise AccessError(f"Failed to read settings file: {str(e)}") from e

    def load(self) -> None:
        """Reload settings from disk."""
        self._load_settings()

    def sync(self) -> None:
        """Save settings to file."""
        path = self._get_settings_path()

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise AccessError(f"Failed to create settings directory: {str(e)}") from e

        try:
            if platform.system() == "Darwin" and self.format == Format.NativeFormat:
                self._sync_macos_settings()
            else:
                self._sync_regular_settings(path)
        except (AccessError, FormatError, SyncError):
            raise
        except Exception as e:
            raise SyncError(f"Unexpected error during sync: {str(e)}") from e

    def _sync_regular_settings(self, path: Path) -> None:
        """Save settings to non-native format files."""
        if self.format == Format.JsonFormat:
            with open(path, "w") as f:
                json.dump(self._data, f, indent=2)
        else:
            config = CaseSensitiveConfigParser()
            for section, values in self._data.items():
                config[section] = {str(k): str(v) for k, v in values.items()}
            with open(path, "w", encoding="utf-8") as f:
                config.write(f)

    def _sync_macos_settings(self) -> None:
        """Save settings in macOS property list format."""
        path = self._get_settings_path()

        try:
            # Save to plist file
            with open(path, "wb") as f:
                try:
                    plistlib.dump(self._data, f)
                except (TypeError, ValueError) as e:
                    raise FormatError(f"Invalid data format for plist: {str(e)}") from e

            # Update macOS defaults system

            for key, value in self._data.items():
                try:
                    value_str = str(value)
                    result = subprocess.run(
                        ["defaults", "write", self._domain, key, value_str],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    logging.warning(
                        "Failed to write to defaults system: %s, ignoring direct write",
                        e,
                    )

        except (AccessError, FormatError, SyncError):
            raise
        except Exception as e:
            raise SyncError(f"Unexpected error syncing macOS settings: {str(e)}") from e

    def _transform_key(self, key: str) -> str:
        """Transform the key based on the format."""
        if self.format == Format.NativeFormat and platform.system() == "Darwin":
            return key
        else:
            parts = key.split("/")
            if len(parts) == 1:
                return f"General/{parts[0]}"
            elif len(parts) == 2:
                return f"{parts[0]}/{parts[1]}"
            else:
                rep = "\\".join(parts[1:])
                return f"{parts[0]}/{rep}"

    def set_value(self, key: str, value: Any) -> None:
        """Set a value in the settings."""
        if not key:
            raise ValidationError("Key cannot be empty")

        try:
            full_key = self._get_full_key(key)
            transformed_key = self._transform_key(full_key)
            current_dict = self._data

            # Navigate through groups
            key_parts = transformed_key.split("/")
            for part in key_parts[:-1]:
                if part not in current_dict:
                    current_dict[part] = {}
                current_dict = current_dict[part]

            current_dict[key_parts[-1]] = value

            # For macOS, immediately sync to defaults system if in native format
            if platform.system() == "Darwin" and self.format == Format.NativeFormat:
                import subprocess

                try:
                    subprocess.run(
                        ["defaults", "write", self._domain, full_key, str(value)],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    logging.warning(
                        "Failed to write to defaults system: %s, ignoring direct write",
                        e,
                    )

        except SyncError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to set value: {str(e)}") from e

    def value(self, key: str, default_value: Any = None) -> Any:
        """Get a value from the settings."""
        if not key:
            raise ValidationError("Key cannot be empty")

        try:
            full_key = self._get_full_key(key)
            current_dict = self._data
            transformed_key = self._transform_key(full_key)  # Transform the key
            for part in transformed_key.split("/"):
                current_dict = current_dict[part]
            return current_dict
        except KeyError as e:
            if default_value is not None:
                return default_value
            raise KeyError(f"Setting not found: {key}") from e
        except Exception as e:
            raise AccessError(f"Failed to retrieve value: {str(e)}") from e

    def _get_full_key(self, key: str) -> str:
        """Get the full key including current group and array index."""
        parts = []
        if self._current_group:
            parts.extend(self._current_group)
        if self._current_array:
            parts.extend(self._current_array)
            if self._array_index >= 0:
                parts.append(str(self._array_index))
        parts.append(key)

        if platform.system() == "Darwin" and self.format == Format.NativeFormat:
            return ".".join(parts).replace("/", ".")

        return "/".join(parts)

    def contains(self, key: str) -> bool:
        """Check if a key exists in the settings."""
        try:
            self.value(key)
            return True
        except KeyError:
            return False

    def remove(self, key: str) -> None:
        """Remove a key from the settings."""
        full_key = self._get_full_key(key)
        current_dict = self._data

        key_parts = full_key.split("/")
        for part in key_parts[:-1]:
            current_dict = current_dict[part]

        if key_parts[-1] in current_dict:
            del current_dict[key_parts[-1]]

    def clear(self) -> None:
        """Clear all settings."""
        self._data.clear()

    def keys(self) -> List[str]:
        """Get all keys in the settings."""
        keys = []

        def collect_keys(d: Dict, prefix: str = ""):
            for k, v in d.items():
                full_key = f"{prefix}/{k}" if prefix else k
                if isinstance(v, dict):
                    collect_keys(v, full_key)
                else:
                    keys.append(full_key)

        collect_keys(self._data)
        return keys

    def status(self) -> Status:
        """Get the current status."""
        return self._status

    def __getitem__(self, key: str) -> Any:
        """Get a value from the settings using dictionary-like access."""
        return self.value(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value in the settings using dictionary-like access."""
        self.set_value(key, value)
