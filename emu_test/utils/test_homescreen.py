#this is supposed to test homescreen for googleapis
#they should have just the launcher at top activity
#nothing else;
#there are at least two types of issue
#1. there is an activty on top of home activity
#2. there is a pop up on top of home activity
#we need to detect both
#package="com.google.android.apps.nexuslauncher"
#or package='com.android.launcher2"
#or package='com.android.launcher3"


import subprocess
import sys
import time
import os
import re
import xml.etree.ElementTree as ET

#there should be just one Stack when the guest is booted
#and the stack topactivity should be the launcher
def find_num_stack(filename):
    count = 0
    with open(filename) as f:
        for line in f:
            if 'Stack id' in line:
                count = count + 1
    return count

def get_activity_name(line):
    p = re.compile(r"topActivity=ComponentInfo{.*\}")
    ms = p.findall(line)
    if ms:
        return ms[0]
    return ''

def find_top_activity(filename):
    with open(filename) as f:
        for line in f:
            if 'topActivity' in line:
                return get_activity_name(line);
    return ''

def find_home_activity(filename):
    num_stacks = find_num_stack(filename)
    if num_stacks > 1:
        return False;
    top_activity = find_top_activity(filename)
    # aosp launcher
    if 'com.android.launcher' in top_activity:
        return True;
    # nexus launcher
    if 'nexus' in top_activity:
        return True;
    print "cannot fine launcher in ", top_activity
    return False;

def do_activity_test():
    subprocess.call(['adb', 'shell', 'am', 'stack', 'list', '>', '/data/local/tmp/activity.txt'])
    subprocess.call(['adb', 'pull', '/data/local/tmp/activity.txt'])
    ret = find_home_activity('activity.txt')
    if not ret:
        return False
    return True

def find_package(root, name):
    for x in root.iter('node'):
        if name in x.get('package'):
            return True;
    return False

def parse_xml(name):
    tree = ET.parse(name)
    root = tree.getroot()
    return root

def do_popup_test():
    subprocess.call(['adb', 'shell', 'uiautomator', 'dump'])
    subprocess.call(['adb', 'pull', '/sdcard/window_dump.xml', 'topscreen.xml'])
    root = parse_xml('topscreen.xml');
    os.remove("topscreen.xml");
    aosplauncher=find_package(root, 'com.android.launcher');
    if aosplauncher:
        print 'found aosp launcher'
        return True;
    nexuslauncher=find_package(root, 'nexuslauncher');
    if nexuslauncher:
        print 'found nexuslauncher'
        return True;
    return False

def do_homescreen_test():
    try:
        ret1 = do_activity_test();
        if not ret1:
            return False;
        ret2 = do_popup_test();
        if not ret2:
            return False;
    except Exception as e:
        print 'exception happened in homescreen test, error:', e
        return False
    return True;


if __name__ == '__main__':
    ret = do_homescreen_test()
    if ret == False:
        print 'fail'
        sys.exit(1)
    print 'pass'

