"""
GS bucket poller to poll for a specific artifact for a build number.
Uses a config file to decide which build artifact needs to be fetched.
"""

import os
import sys
import csv
import time
import subprocess

gs_bucket_sysimage = 'gs://android-build-emu-sysimage/builds/'
gs_bucket_emubuild = 'gs://android-build-emu/builds/'

adt_infra = os.environ["ADT_INFRA"]
config_file = os.path.join(adt_infra, 'emu_test', 'config', 'poll_cfg.csv')

def poll(build_name, build_num, gs_bucket):
    print "Polling for", build_name, build_num

    for counter in range(12):
       print "Polling Iteration", (counter+1)
       gs_file_path = gs_bucket + build_name + '/' + build_num + '/'
       return_code = subprocess.call("gsutil ls %s" % gs_file_path, shell=True)
       if return_code == 0:
          break
       time.sleep(600)

    return return_code

if __name__ == '__main__':
    """Main execution
    """
    ori = sys.argv[1]
    build_num = sys.argv[2]
    build_dir = sys.argv[3]

    if ori == "public":
       gs_bucket = gs_bucket_emubuild
    else:
       gs_bucket = gs_bucket_sysimage

    print "Wait for 30 mins before starting to poll"
    time.sleep(1800)

    print "Polling for", build_num, "in", gs_bucket
    print "Copy builds in", build_dir

    with open(config_file, "rb") as file:
       reader = csv.reader(file)
       for row in reader:
          # Skip the first line of the file.  It is only a Header for human readable viewing.
          if reader.line_num == 1 or reader.line_num == 2:
             continue
          else:
             if(row[0].strip() == ori):
                for x in row[1:]:
                   x = x.strip()
                   status = poll(x, build_num, gs_bucket)
                   if status != 0:
                      print x, build_num, "Not available in", gs_bucket
                      exit(status)
                   else:
                      time.sleep(60)
                      gs_file_path = gs_bucket + x + '/' + build_num + '/'
                      dst_path = build_dir
                      if 'aosp-emu' in x:
                         dst_path = dst_path + '/'
                      elif 'tv' in x:
                         dst_path = dst_path + '/' + 'tv-x86.zip'
                      elif 'wear' in x:
                         dst_path = dst_path + '/' + 'wear-x86.zip'
                      elif 'user' in x:
                         dst_path = dst_path + '/' + 'gphone-x86-user.zip'
                      elif '64' in x:
                         dst_path = dst_path + '/' + 'gphone-x86-64.zip'
                      else:
                         dst_path = dst_path + '/' + 'gphone-x86.zip'

                      cmd = "gsutil cp " + gs_file_path + '*/* ' + dst_path
                      print cmd
                      subprocess.call(cmd, shell=True)

    exit(0)
