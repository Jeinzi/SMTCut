#!/usr/bin/env python3

# Send a file to a Graphtec vinyl cutter using libusb.
#
# Licensed under the terms of the GPL2, see LICENSE file.
# Copyright (c) 2013 Peter Monta <pmonta@gmail.com>
# Copyright (c) 2022 Julian Heinzel <jeinzi@gmx.de>

import os
import sys
import usb1

progressAvailable = False
try:
  from tqdm import tqdm
  progressAvailable = True
except:
  print("Progress bar not available, install tqdm if you'd like to change that.")

#
# open a graphtec vinyl cutter from a list of recognized devices
#

device_list = [
  (0x0b4d, 0x1121, "Silhouette Cameo"),
  (0x0b4d, 0x112b, "Silhouette Cameo 2"),
  (0x0b4d, 0x112f, "Silhouette Cameo 3"),
  (0x0b4d, 0x1123, "Silhouette Portrait"),
  (0x0b4d, 0x1132, "Silhouette Portrait 2"),
  (0x0b4d, 0x113A, "Silhouette Portrait 3"),  # Not tested
  (0x0b4d, 0x112c, "Silhouette SD1"),         # Not tested
  (0x0b4d, 0x112d, "Silhouette SD2"),         # Not tested
]

# Open the first recognized device.
def open_graphtec_device(ctx):
  for (vendor_id,product_id,product_name) in device_list:
    handle = ctx.openByVendorIDAndProductID(vendor_id, product_id)
    if handle:
      return (handle, product_name)
  return None

#
# main program
#

if len(sys.argv)==2:
  f = open(sys.argv[1], "rb")
elif len(sys.argv)==1:
  f = sys.stdin
  progressAvailable = False
else:
  print("Usage: file2graphtec [filename]")
  sys.exit(1)

endpoint = 1
ctx = usb1.USBContext()

res = open_graphtec_device(ctx)

if not res:
  sys.stderr.write("No graphtec device found.\n")
  sys.exit(1)
else:
  (handle, product_name) = res

handle.claimInterface(0)
print(f"Found device '{product_name}'.")

# If possible, create a progress bar.
if progressAvailable:
  fileSize = os.path.getsize(sys.argv[1])
  pBar = tqdm(total=fileSize, unit="Byte")

while True:
  if not (data := f.read(8)):
    break
  handle.bulkWrite(endpoint, data)
  if progressAvailable:
    pBar.update(8)

f.close()
