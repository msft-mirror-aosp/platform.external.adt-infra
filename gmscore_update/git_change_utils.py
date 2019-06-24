"""Utils to upload a change to gerrit."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import collections
import os
import subprocess
import tempfile
from absl import logging


ANDROID_GERRIT_RPC = 'rpc://googleplex-android-review.git.corp.google.com/'
FileTransferInfo = collections.namedtuple(
    'FileTransferInfo', ['source', 'dest', 'arch', 'build_type', 'dpi'])


class EmptyChangeError(Exception):
  """Raised when attempting to push an empty change."""


def CreateChange(git, project, branch, topic, commit_message,
                 file_transfer_infos, git_dir, gmscore_branch,
                 file_operation_fn, dry_run):
  """Creates a gerrit change from modifications file_operation_fn makes to repo.

  Prerequisite: Assumes CheckoutBranch has been called already.

  Args:
    git: string, Path to git binary from
      devtools/gerritcodereview/git-remote-google MPM'
    project: string, Gerrit project to create change on
    branch: string, branch of the Gerrit project to modify
    topic: string, topic to add new change to
    commit_message: string, the commit message
    file_transfer_infos: list(FileTransferInfo), what files to change
    git_dir: string, the base directory for the git project
    gmscore_branch: string, the gmscore branch to drop
    file_operation_fn: function, manipulates the files in the git repo
    dry_run: only commit the change but not upload to Gerrit
  """
  os.chdir(git_dir)
  os.system("curl -Lo `git rev-parse --git-dir`/hooks/commit-msg https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x `git rev-parse --git-dir`/hooks/commit-msg")
  try:
    _PushChange(git, commit_message, project, branch, file_transfer_infos,
                git_dir, gmscore_branch, topic, file_operation_fn, dry_run)
  except EmptyChangeError:
    logging.warning('Abadoning change because it was empty.')


def _GetProjectUrl(project):
  """Gets the Git project URL for a project name.

  Args:
    project: string, the gerrit project to check out
  Returns:
    string, the gerrit project URL
  """
  return ANDROID_GERRIT_RPC + project


def _PushChange(git, subject, project, branch, file_transfer_infos, git_dir,
                gmscore_branch, topic, file_operation_fn, dry_run):
  """Pushes changes to update project based on file_operation_fn.

  This function uses git directly rather than the Gerrit API to avoid the
  5MB limit on post body size set on the gerrit frontend.

  Assumes that subject contains the "Change-Id:" line causing an existing
  Gerrit change to be updated.

  Assumes the git branch has already been checked out via CheckoutBranch.

  Args:
    git: string, Path to git binary from
      devtools/gerritcodereview/git-remote-google MPM'
    subject: string, the change description to use including the change ID
    project: string, the gerrit project to push to
    branch: string, the branch to push to
    file_transfer_infos: list(FileTransferInfo), what files to change
    git_dir: string, the base directory for the git project
    gmscore_branch: string, the gmscore branch to drop
    file_operation_fn: function, manipulates the files in the git repo
    dry_run: only commit the change but not upload to Gerrit 
  Raises:
    EmptyChangeError: if there are no changes to push
  """
  # move files into place after directory is cloned
  if file_operation_fn != None:
    file_operation_fn(file_transfer_infos, git_dir, gmscore_branch)

  subprocess.call([git, '-C', git_dir, 'add', '.'])

  status_fd, status_filename = tempfile.mkstemp(suffix='git-status')
  try:
    subprocess.call(
        [git, '-C', git_dir, 'status', '--porcelain'],
        stdout=status_fd,
        stderr=subprocess.STDOUT)
  finally:
    os.close(status_fd)
  if os.path.getsize(status_filename) == 0:
    raise EmptyChangeError

  subprocess.call([git, '-C', git_dir, 'commit', '-a', '-m', subject])

  if not dry_run:
    subprocess.call([
        git, '-C', git_dir, 'push',
        _GetProjectUrl(project), 'HEAD:refs/for/{0}'.format(branch), '-o', 'topic={0}'.format(topic)
    ])


def CheckoutBranch(git, project, branch, git_dir):
  """Just checks out a branch to read files locally.

  Args:
    git: string, Path to git binary from
      devtools/gerritcodereview/git-remote-google MPM'
    project: string, the gerrit project to check out
    branch: string, the branch to check out
    git_dir: string, the base directory for the git project
  """
  subprocess.call([
      git, 'clone', '--depth', '1', '--branch', branch,
      _GetProjectUrl(project), git_dir
  ])
