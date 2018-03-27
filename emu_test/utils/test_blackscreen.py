#this will test blackscreen
#it uses the screenshot console command, instead
#of the adb shell screencap because screencap is
#not reliable, and is not truthful
#

import subprocess
import sys
import time
import os
import shutil
import re
import xml.etree.ElementTree as ET
from PIL import Image

def take_screenshot(png_dir):
    subprocess.call(['adb', 'emu', 'screenrecord', 'screenshot', png_dir])

def reset_dir(png_dir):
    if os.path.exists(png_dir):
        shutil.rmtree(png_dir)
    os.makedirs(png_dir)

def find_first_png(png_dir):
    for filename in os.listdir(png_dir):
        if filename.endswith(".png"):
            return os.path.join(png_dir, filename)
    raise Exception("Cannot find any png file")

def read_black_pixels_ratio(png_dir):
    filename = find_first_png(png_dir);
    png_image = Image.open(filename)
    pixels = png_image.load()
    width = png_image.size[0]
    height = png_image.size[1]
    total_pixels = width * height
    print "image size: ", png_image.size
    count = 0
    for row in range(0, width):
        for col in range(0, height):
            pix = pixels[row, col]
            if pix[0] == 0 and pix[1] == 0 and pix[2] == 0:
                count = count + 1
    ratio = (count * 1.0) / total_pixels
    return ratio

def is_blackscreen():
    png_dir = os.path.join(os.getcwd(), 'screenpng')
    reset_dir(png_dir)
    take_screenshot(png_dir)
    ratio = read_black_pixels_ratio(png_dir)
    print "black ratio is ", ratio
    if (ratio > 0.99):
        print "black ratio is too high"
        return True
    return False

def do_blackscreen_test():
    try:
        return not is_blackscreen()
    except Exception as e:
        print 'exception happened in homescreen test, error:', e
        return False

if __name__ == '__main__':
    ret = do_blackscreen_test()
    if ret == False:
        print 'fail'
        sys.exit(1)
    print 'pass'
