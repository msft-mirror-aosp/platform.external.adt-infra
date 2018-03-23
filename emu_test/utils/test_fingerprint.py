#this is supposed to work on all screen size on pi

import subprocess
import sys
import time
import os
import xml.etree.ElementTree as ET

g_emulator_serial = 'emulator-5554'

if len(sys.argv) == 2:
    g_emulator_serial = sys.argv[1];

def dump_screen_xml():
    subprocess.call(['adb', '-s', g_emulator_serial, 'shell', 'uiautomator', 'dump'])

def pull_xml(name):
    subprocess.call(['adb','-s', g_emulator_serial,  'pull', '/sdcard/window_dump.xml', name])

def parse_xml(name):
    tree = ET.parse(name)
    root = tree.getroot()
    return root

def get_middle(bounds):
    aa = bounds.replace('[', ' ');
    bb = aa.replace(']', ' ');
    cc = bb.replace(',', ' ');
    dd = cc.split();
    [x1, y1, x2, y2] = dd
    x = (int(x1) + int(x2)) / 2;
    y = (int(y1) + int(y2)) / 2;
    return [str(x), str(y)]


def find_location(root, name):
    for x in root.iter('node'):
        if name == x.get('text'):
            return get_middle(x.get('bounds'));
    print 'ERROR: cannot find ' + name +  ' button'
    return []

def get_button_location(name):
    dump_screen_xml();
    pull_xml(name + '.xml');
    root = parse_xml(name + '.xml');
    xy=find_location(root, name);
    return xy

def adb_touch(x,y):
    time.sleep(2)
    subprocess.call(['adb', 'shell', 'input', 'tap', x, y]);
    time.sleep(2)

def adb_touch_button(name):
    tries = 0
    [x, y] = ['0', '0']
    status = False
    while tries < 10:
        z = get_button_location(name)
        if len(z) == 0:
            print "cannot find the location, try again"
            time.sleep(2)
            tries = tries + 1
        else:
            [x, y] = z
            status = True
            break
    os.remove(name + ".xml");
    if not status:
        raise Exception("Tried many times but still failed to find location of button " + name)
    adb_touch(x,y)

def adb_input_text(textstr):
    time.sleep(2)
    subprocess.call(['adb', 'shell', 'input', 'text', textstr]);
    time.sleep(2)

def emu_console_finger_touch(x):
    time.sleep(2)
    subprocess.call(['adb', 'emu', 'finger', 'touch', x]);
    time.sleep(2)

def adb_power_key():
    time.sleep(2)
    subprocess.call(['adb', 'shell', 'input', 'keyevent', '26']);
    time.sleep(2)

def check_screen_is_unlocked():
    ret1 = subprocess.call(['adb', 'shell', 'dumpsys', 'deviceidle', '|', 'grep',
            'mScreenLocked=false']);
    if ret1:
        print 'fail to unlock screen'
        return False
    else:
        print 'screen unlocked successfully'
        return True

def check_screen_is_locked():
    ret1 = subprocess.call(['adb', 'shell', 'dumpsys', 'deviceidle', '|', 'grep',
            'mScreenLocked=true']);
    if ret1:
        print 'fail to lock screen'
        return False
    else:
        print 'screen locked successfully'
        return True

#this works on pi
def do_fingerprint_test():
    try:
        subprocess.call(['adb', 'shell', 'am', 'start', '-n', \
                'com.android.settings/com.android.settings.fingerprint.FingerprintEnrollIntroduction'])
        adb_touch_button('NEXT');
        adb_touch_button('Fingerprint + PIN');
        adb_touch_button('NO');
        adb_input_text('1111');
        adb_touch_button('NEXT');
        adb_input_text('1111');
        adb_touch_button('CONFIRM');
        adb_touch_button('DONE');
        emu_console_finger_touch('1');
        emu_console_finger_touch('1');
        emu_console_finger_touch('1');
        adb_touch_button('DONE');
        #test a few times
        for tries in range(0,3):
            #turn off screen
            adb_power_key();
            #turn on screen
            adb_power_key();
            #check it is locked
            check_screen_is_locked();
            #touch fingerprint
            emu_console_finger_touch('1');
            #check it is unlocked
            ret = check_screen_is_unlocked();
            if ret:
                return True
        return False
    except Exception as e:
        print 'exception happened in fingerprint test, error:', e
        return False

if __name__ == '__main__':
    ret = do_fingerprint_test()
    if ret == False:
        sys.exit(1)

