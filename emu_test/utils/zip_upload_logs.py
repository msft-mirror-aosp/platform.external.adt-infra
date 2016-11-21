import os
import argparse
import subprocess
import shutil

parser = argparse.ArgumentParser(description='Zip and upload log folders')

parser.add_argument('--dir', dest='log_dir', action='store',
                    help='local log directory')
parser.add_argument('--name', dest='zip_name', action='store',
                    help='name of zipped file - usually contains the build number')
parser.add_argument('--user', dest='remote_user', action='store',
                    help='remote user name')
parser.add_argument('--ip', dest='remote_ip', action='store',
                    help='remote ip')
parser.add_argument('--dst', dest='remote_dir', action='store',
                    help='remote directory')
parser.add_argument('--skiplog', dest='skiplog', action='store_true', help='skip uploading log')
parser.add_argument('--build-dir', dest='build_dir', action='store', help='path to build directory')
parser.add_argument('--iswindows', dest="is_windows", action='store_false', help='treat file args as windows style')

args = parser.parse_args()

def zip_and_upload():

  def verbose_call(cmd):
    print "Run command %s" % ' '.join(cmd)
    subprocess.check_call(cmd)

  try:
    args.remote_dir = args.remote_dir.replace(" ", "_")
    remote_host = '%s@%s' % (args.remote_user, args.remote_ip)
    remote_path = '%s:%s' % (remote_host, args.remote_dir)
    gsutil_path = os.path.join(args.build_dir, 'third_party', 'gsutil', 'gsutil.py')

    if args.skiplog is False:
      verbose_call(['zip', '-r', args.zip_name, args.log_dir])
      verbose_call(['ssh', remote_host, 'mkdir -p %s' % args.remote_dir])
      verbose_call(['scp', args.zip_name, remote_path])

    # if cts result is available, upload to public_html directory
    for x in ['CTS', 'GTS']:
      cts_logdir = os.path.join(args.log_dir, '%s_test' % x, '%s_combined_result' % x.lower())
      if os.path.isdir(cts_logdir):
        builderName = os.path.basename(os.path.normpath(args.remote_dir))
        cts_dst = os.path.join(args.remote_dir, "..", "..", "public_html", "%s_Result" % x, builderName)
        cts_dst = os.path.normpath(cts_dst)
        verbose_call(['ssh', remote_host, 'mkdir -p %s' % cts_dst])
        verbose_call(['scp', '-r', os.path.join(cts_logdir, ''), '%s:%s' % (remote_host, os.path.join(cts_dst, args.zip_name[:-4]))])

    # if ui result is available, upload to public_html directory
    ui_logdir = os.path.join(args.log_dir, "UI_test")
    if os.path.isdir(ui_logdir):
      builderName = os.path.basename(os.path.normpath(args.remote_dir))
      ui_dst = os.path.join(args.remote_dir, "..", "..", "public_html", "UI_Result", builderName)
      if args.is_windows is True:
        import posixpath
        ui_dst = posixpath.normpath(ui_dst)  # Destination is a *Nix machine.
      else:
        ui_dst = os.path.normpath(ui_dst)
      verbose_call(['ssh', remote_host, 'mkdir -p %s' % os.path.join(ui_dst, args.zip_name[:-4])])
      ui_gs_dst = 'gs://sysimage_test_traces/%s/%s' % (builderName, args.log_dir)
      for x in os.listdir(ui_logdir):
        # upload gradle report to the master
        if os.path.isdir(os.path.join(ui_logdir, x)) and x.endswith("_report"):
          verbose_call(['scp', '-r', os.path.join(ui_logdir, x), '%s:%s' % (remote_host, os.path.join(ui_dst, args.zip_name[:-4]))])
        # upload bugreport, logcat, verbose, and details dir to GCS
        elif os.path.isdir(os.path.join(ui_logdir, x)) and x.endswith("_details"):
          verbose_call(['python', gsutil_path, 'cp', '-r', os.path.join(ui_logdir, x), os.path.join(ui_gs_dst, x[:-8])])
        elif x.endswith('_bugreport.txt') or x.endswith('_logcat.txt') or x.endswith('_verbose.txt'):
          verbose_call(['python', gsutil_path, 'cp', os.path.join(ui_logdir, x), os.path.join(ui_gs_dst, x[:x.rfind('_')], '')])

    # if console result is available, upload to public_html directory
    console_logdir = os.path.join(args.log_dir, "Console_test")
    if os.path.isdir(console_logdir):
        builderName = os.path.basename(os.path.normpath(args.remote_dir))
        console_dst = os.path.join(args.remote_dir, "..", "..", "public_html", "Console_Result", builderName)
        console_dst = os.path.normpath(console_dst)
        verbose_call(['ssh', remote_host, 'mkdir -p %s' % console_dst])
        verbose_call(['scp', '-r', os.path.join(console_logdir, ''), '%s:%s' % (remote_host, os.path.join(console_dst, args.zip_name[:-4]))])

    # remove log directory
    try:
      print "Delete directory %s" % args.log_dir
      shutil.rmtree(args.log_dir)
    except Exception as e:
      print "Error in deleting log directory %r" % e

  except Exception as e:
    print "Error in zip_and_upload %r" % e
    return 1

  return 0

if __name__ == "__main__":
  exit(zip_and_upload())
