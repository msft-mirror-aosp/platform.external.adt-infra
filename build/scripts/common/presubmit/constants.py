import os
from common.presubmit.agent_lib import AgentLib

class Constants:
  PRESUBMIT_FETCH_URL_PREFIX = "https://googleplex-android.googlesource.com"

  PRESUBMIT_PROJECT_NAME_ARRAY = "PRESUBMIT_PROJECT_NAME_ARRAY"
  PRESUBMIT_FETCH_URL_ARRAY = "PRESUBMIT_FETCH_URL_ARRAY"
  PRESUBMIT_FETCH_REF_ARRAY = "PRESUBMIT_FETCH_REF_ARRAY"
  IS_TOPIC = "IS_TOPIC"

  CHANGE_ID = "CHANGE_ID"
  CHANGE_REVISION = "CHANGE_REVISION"
  CHANGE_FILES = "CHANGE_FILES"

  # Variables needed to communicate with Gerrit REST API.
  HOST = "https://googleplex-android-review.googlesource.com/"
  # TODO: Assign platform-dependent value once Windows and Mac presubmit bots are up
  COOKIE_PATH = os.path.join(os.path.expanduser('~'), '.gitcookies')
  PROJECTS = [] # Intentionally empty since slave only calls verify() (i.e. does not query).
  BRANCH = "studio-master-dev"
  PATH = ".*"
  AGENT_LIB = AgentLib(HOST, COOKIE_PATH, PROJECTS, BRANCH, PATH)
