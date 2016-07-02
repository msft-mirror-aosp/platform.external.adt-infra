import os
import argparse
import subprocess
import psutil
import zipfile
import shutil

parser = argparse.ArgumentParser(description='Download and unzip a list of files separated by comma')
parser.add_argument('--file', dest='remote_file_list', action='store',
                    help='string contains a list of remote files separated by comma')
parser.add_argument('--build-dir', action='store',
                    help='location of build directory')
parser.add_argument('--clean-system-image-dir', action='store_true', help='clean up system image directory')

args = parser.parse_args()


def get_dst_dir(remote_path):
  file_name = os.path.basename(remote_path)
  emulator_branches = ["emu-master-dev", "emu-2.0-release", "emu-2.2-release"]
  if file_name.startswith('sdk-repo-linux-system-images') or file_name.startswith('sdk-repo-linux-addon'):
    branch_name = remote_path.split('/')[-4]
    if 'google' in branch_name and 'addon' in branch_name:
      tag = 'google_apis'
    elif 'google_atv' in branch_name:
      tag = 'android-tv'
    else:
      tag = 'default'
    if 'lmp-mr1' in branch_name:
      api = '22'
    elif 'mnc' in branch_name:
      api = '23'
    elif 'nyc' in branch_name:
      api = '24'
    elif 'lmp' in branch_name:
      api = '21'
    elif 'klp' in branch_name:
      api = '19'
    elif 'gb-emu-dev' in branch_name:
      api = '10'
    elif 'ics-mr1-emu-dev' in branch_name:
      api = '15'
    elif 'jb-emu-dev' in branch_name:
      api = '16'
    elif 'jb-mr1.1-emu-dev' in branch_name:
      api = '17'
    elif 'jb-mr2-emu-dev' in branch_name:
      api = '18'

    else:
      raise ValueError("unsupported image %s", branch_name)
    return os.path.join(os.environ['ANDROID_SDK_ROOT'],
                        "system-images", "android-%s" % api, tag)
  else:
    for branch in emulator_branches:
      if branch in remote_path:
        return branch
  return None

def clean_emu_proc():
  print 'clean up any emulator process'
  for x in psutil.process_iter():
    try:
      proc = psutil.Process(x.pid)
      # mips 64 use qemu-system-mipsel64, others emulator-[arch]
      if "emulator" in proc.name() or "qemu-system" in proc.name():
        print "trying to kill - %s, pid - %d, status - %s" % (proc.name(), proc.pid, proc.status())
        proc.kill()
    except:
      pass

def verbose_call(cmd):
  print "Run command %s" % ' '.join(cmd)
  subprocess.check_call(cmd)

def unzip_addon_dir(file_name, dst_dir):
  print file_name, dst_dir
  with open(file_name, 'rb') as fh:
    z = zipfile.ZipFile(fh)
    for name in z.namelist():
      if ("images/") in name and not name.endswith("images/"):
        base_name = os.path.basename(name)
        if not base_name:
          abi = os.path.basename(os.path.normpath(name))
          verbose_call(["mkdir", "-p", os.path.join(dst_dir,abi)])
          print "Found abi %s" % abi
          continue
        dst_path = os.path.join(dst_dir, abi, base_name)
        with z.open(name) as src, file(dst_path, "wb") as dst:
          print "unzip from %s to %s" % (name, dst_path)
          shutil.copyfileobj(src, dst)

def download_and_unzip():
  clean_emu_proc()
  if args.clean_system_image_dir:
    image_dir = os.path.join(os.environ['ANDROID_SDK_ROOT'], 'system-images')
    print 'Remove system image directory: ', image_dir
    verbose_call(['rm', '-rf', image_dir])
  file_list = args.remote_file_list.split(',')
  dst_dir = get_dst_dir(file_list[0])

  gsutil_path = os.path.join(args.build_dir, 'third_party', 'gsutil', 'gsutil.py')
  for file_path in file_list:
    file_path = file_path.strip('\n')
    if file_path == '':
      continue
    dst_dir = get_dst_dir(file_path)
    file_name = file_path.split('/')[-1]
    try:
      verbose_call(['python', gsutil_path, 'cp', file_path, '.'])
      if dst_dir is not None:
        verbose_call(['mkdir', '-p', dst_dir])
        if 'x86_64' in file_path:
          verbose_call(['rm', '-rf', os.path.join(dst_dir,'x86_64')])
        elif 'x86' in file_path:
          verbose_call(['rm', '-rf', os.path.join(dst_dir,'x86')])
        elif 'armv7' in file_path:
          verbose_call(['rm', '-rf', os.path.join(dst_dir,'armeabi-v7a')])
        if 'addon' in file_name:
          unzip_addon_dir(file_name, dst_dir)
        else:
          verbose_call(['unzip', '-o', file_name, '-d', dst_dir])
        verbose_call(['rm', '-rf', file_name])
      else:
        raise ValueError('Error: Unknown branch!')
    except Exception as e:
      print "Error in download_and_unzip %r" % e
      return 1
  return 0

if __name__ == "__main__":
  exit(download_and_unzip())
