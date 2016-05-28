import os
import platform
import argparse
import shutil
from subprocess import PIPE,STDOUT
import psutil
import logging
import threading

parser = argparse.ArgumentParser(description='Download and unzip a list of files separated by comma')
parser.add_argument('--build-dir', dest='build_dir', action='store',
                    help='full path to build directory')
parser.add_argument('--log-dir', dest='log_dir', action='store',
                    help='full path to log directory')
parser.add_argument('--props', dest='props', action='store',
                    help='build properties')

args = parser.parse_args()
if not os.path.exists(args.log_dir):
  os.makedirs(args.log_dir)

log_formatter = logging.Formatter('%(message)s')
file_handler = logging.FileHandler(os.path.join(args.log_dir, "init_bot.log"))
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG)

logger = logging.getLogger()
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.setLevel(logging.DEBUG)


def clean_up():
  """clean up build directory and qemu-gles-[pid] files"""

  # remove qemu-gles-[pid] files
  host = platform.system()
  if host in ["Linux", "Darwin"]:
    tmp_dir = "/tmp/android-%s" % os.environ["USER"]
  else:
    tmp_dir = os.path.join(os.path.expanduser("~"), 'AppData', 'Local', 'Temp')
  if os.path.isdir(tmp_dir):
    logger.info("Delete directory %s", tmp_dir)
    try:
      shutil.rmtree(tmp_dir)
    except Exception as e:
      logger.info("Error in deleting %s, %r", tmp_dir, e)

  # remove build directory
  for f in os.listdir(args.build_dir):
    file_path = os.path.join(args.build_dir,f)
    try:
      if os.path.isfile(file_path):
        logger.info("Delete file %s", file_path)
        os.remove(file_path)
      elif os.path.isdir(file_path) and args.log_dir != f:
        logger.info("Delete directory %s", file_path)
        shutil.rmtree(file_path)
    except Exception as e:
      logger.error("Error in deleting build directory %r", e)

def update_sdk_with_timeout(filter, timeout):
    def update_sdk():
        android_exec = "android.bat" if os.name == "nt" else "android"
        cmd = [android_exec, "update", "sdk", "-s", "--no-ui", "--filter", filter, "--force"]
        logger.info("Update android sdk, cmd: %s", ' '.join(cmd))
        update_sdk.ps = psutil.Popen(cmd, stdout=PIPE, stdin=PIPE, stderr=STDOUT, bufsize=1)
        with update_sdk.ps.stdout:
            update_sdk.ps.stdin.write('y\n')
            update_sdk.ps.stdin.flush()
            for line in iter(update_sdk.ps.stdout.readline, b""):
                logger.info(line)
                if "Do you accept the license" in line:
                    try:
                        update_sdk.ps.stdin.write('y\n')
                        update_sdk.ps.stdin.flush()
                    except:
                        pass
            update_sdk.ps.wait()
    thread = threading.Thread(target=update_sdk)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        logger.info('Terminating process %s' % update_sdk.ps)
        for proc in psutil.process_iter():
            try:
                if any([x == update_sdk.ps.pid for x in [proc.ppid(), proc.pid]]):
                    logger.info("Terminate subprocess: %s - %s" % (proc.pid, proc.cmdline()))
                    proc.kill()
            except Exception as e:
                pass
        thread.join(5)
        return 1
    return 0

if __name__ == "__main__":
  try:
    with open(os.path.join(args.log_dir, 'build.props'), 'w') as outfile:
        outfile.write(args.props)
    logger.info(args.props)
    clean_up()
  except:
    pass
  rc = update_sdk_with_timeout('add-on,system-image,extra,platform-tool,platform,tool', 900)

  # kill adb process, during update of sdk tools, it will run adb start-server, which leaves
  # a child adb process, clean it up here to avoid hanging of script
  for proc in psutil.process_iter():
    try:
      pinfo = proc.as_dict(attrs=['pid', 'name', 'status'])
      if 'adb' in pinfo['name'] and pinfo['status'] != 'zombie':
        logger.info("Kill adb process %s", pinfo)
        proc.kill()
        proc.wait(5)
    except psutil.NoSuchProcess:
        pass

  exit(rc)
