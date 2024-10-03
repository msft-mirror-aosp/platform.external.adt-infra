#!/usr/bin/env python3

import subprocess
import os
from pathlib import Path


HERE = Path(os.path.dirname(__file__)).absolute()


class Git:
    """
    A class for interacting with a Git repository.

    Provides methods for getting information about the repository,
    such as the root directory, the last commit SHA1, and the list of
    changed files.

    Attributes:
        repo (Path): The path to the Git repository. Defaults to the directory
                     containing this script.
    """

    def __init__(self, repo=HERE):
        """
        Initialize a new Git object.

        Args:
            repo (Path): The path to the Git repository.
        """
        self.repo = repo

    def root(self) -> Path:
        """
        Get the root directory of the Git repository.

        Returns:
            Path: The absolute path to the root directory.
        """
        return Path(
            subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], cwd=self.repo
            )
            .decode("utf-8")
            .strip()
        )

    def last(self) -> str:
        """
        Get the SHA1 of the last commit in the Git repository.

        Returns:
            str: The SHA1 of the last commit.
        """
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.repo)
            .decode("utf-8")
            .strip()
        )

    def open_changes(self) -> bool:
        """
        Check if there are any uncommitted changes in the Git repository.

        Returns:
            bool: True if there are uncommitted changes, False otherwise.
        """
        try:
            subprocess.run(
                ["git", "diff-index", "--quiet", "HEAD"], check=True, cwd=self.repo
            )
            return False
        except subprocess.CalledProcessError:
            return True

    def changed_files(self, git_sha1="HEAD") -> list[Path]:
        """
        Get a list of files changed in a specific commit.

        Args:
            git_sha1 (str): The SHA1 of the commit. Defaults to "HEAD".

        Returns:
            list[Path]: A list of filenames that were changed in the commit.
        """
        return [
            Path(x)
            for x in subprocess.check_output(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", git_sha1],
                cwd=self.repo,
            )
            .decode("utf-8")
            .splitlines()
        ]

    def is_valid_git_commit(self, commit_hash):
        """
        Checks if a given string is a valid Git commit hash.

        Args:
            commit_hash: The string to check.
            repo_path: The path to the Git repository. Defaults to the current directory.

        Returns:
            True if the string is a valid commit hash, False otherwise.
        """
        try:
            subprocess.run(
                ["git", "cat-file", "-e", commit_hash],
                cwd=self.repo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
