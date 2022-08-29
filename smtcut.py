#!/usr/bin/env python3

# Cut fine-pitch SMT stencils from a gerber/PDF/SVG/DXF file using
# a Graphtec craft/vinyl cutter. (e.g. Silhouette Cameo or Portrait)
#
# Licensed under the terms of the GPL2, see LICENSE file.
# Copyright (c) 2012 Peter Monta <pmonta@gmail.com>
# Copyright (c) 2015 Philipp Klaus <philipp.klaus@gmail.com>
# Copyright (c) 2022 Julian Heinzel <jeinzi@gmx.de>

import os
import sys
import argparse
import distutils

import pic
import config
import graphtec
import optimize



def main():
    # Parse arguments.
    cnf = config.getDefaultConfig()
    floats = lambda s: list(map(float, s.split(',')))
    formatList = lambda a: str(a).strip("[]").replace(" ", "")

    # Format default values.
    dOffset = formatList(cnf["offset"])
    dBorder = formatList(cnf["border"])
    dMatrix = formatList(cnf["matrix"])
    dSpeed  = formatList(cnf["speed"])
    dMediaSize = formatList(cnf["mediaSize"]).replace(",", "×")

    parser = argparse.ArgumentParser()
    parser.add_argument('--offset', type=floats, default=cnf["offset"],
        help=f'translate to device coordinates x,y (inches) (default: {dOffset})')
    parser.add_argument('--border', type=floats, default=cnf["border"],
        help=f'cut a border around the bounding box of the gerber file; 0,0 to disable (default: {dBorder})')
    parser.add_argument('--matrix', type=floats, default=cnf["matrix"],
        help=f'transform coordinates by [a b;c d] (default: identity transform {dMatrix})')
    parser.add_argument('--speed', type=floats, default=cnf["speed"],
        help=f'use speed s in device units; s2,s3 for multiple passes (default: {dSpeed})')
    parser.add_argument('--force', type=floats, default=cnf["force"],
        help=f'use force f in device units; f2,f3 for multiple passes (default: first pass {cnf["force"][0]}, second pass {cnf["force"][1]})')
    parser.add_argument('--cut_mode', type=int, choices=[0,1], default=cnf["cutMode"],
        help=f'0 for highest accuracy (fine pitch), 1 for highest speed (default: {cnf["cutMode"]})')
    parser.add_argument('--media_size', type=floats, default=cnf["mediaSize"],
        help=f'size of media (default: {dMediaSize} inches)')
    parser.add_argument('--rotate', type=float, dest='theta', default=0.,
        help=f'rotate counterclockwise by theta degrees (default: no rotation)')
    parser.add_argument('--merge', type=int, choices=[0,1], default=cnf["merge"],
        help=f'merge close smaller structures into one big cutout (default: {cnf["merge"]})')
    parser.add_argument('input_filename')
    args = parser.parse_args()


    temp_pdf = "_tmp_gerber.pdf"
    temp_ps  = "_tmp_gerber.ps"
    temp_pic = "_tmp_gerber.pic"
    pdf_filename = args.input_filename
    extension = pdf_filename[-3:].lower()

    # Check dependencies.
    allowed_inkscape_extensions = ('svg', 'dxf')
    
    if distutils.spawn.find_executable("pstoedit") is None:
        print("FATAL ERROR: Could not find 'pstoedit' in your PATH. Exiting.")
        sys.exit(1)
    if distutils.spawn.find_executable("gerbv") is None:
        print("ERROR: Could not find 'gerbv' in your PATH. Exiting.")
        sys.exit(1)
    if distutils.spawn.find_executable("inkscape") is None and extension in allowed_inkscape_extensions:
        print("ERROR: Could not find 'inkscape' in your PATH. Exiting.")
        sys.exit(1)

    # Check if file exists.
    if not os.path.isfile(args.input_filename):
        print(f"ERROR: File '{args.input_filename}' can't be found. Exiting.")
        sys.exit(1)

    # If file is not a PDF, try to convert it to one.
    if extension != "pdf":
      if extension in allowed_inkscape_extensions:
        os.system(f"inkscape --export-filename={temp_pdf} {args.input_filename}")
      else:
        os.system(f"gerbv --export=pdf --output='{temp_pdf}' --border=0 '{args.input_filename}'")
      pdf_filename = temp_pdf

    # Convert PDF to PIC format.
    os.system(f"gs -dNOPAUSE -dBATCH -sDEVICE=ps2write -sOutputFile='{temp_ps}' '{pdf_filename}'")
    os.system(f"pstoedit -f pic '{temp_ps}' '{temp_pic}' 2>/dev/null")


    # Convert to Graphtec.
    g = graphtec.graphtec()
    g.set(media_size=args.media_size)
    offset, border = args.offset, args.border
    g.set(offset=(offset[0]+border[0]+0.5,offset[1]+border[1]+0.5))
    g.set(matrix=args.matrix)
    g.start()

    strokes = pic.read_pic(temp_pic)

    # Optionally merge multiple smaller pads into bigger pads spanning the same area.
    if not args.merge == 0:
      import mergepads
      strokes = mergepads.fix_small_geometry(strokes, cnf["mergeThreshold"][0], cnf["mergeThreshold"][1])

    strokes = optimize.rotate(strokes, args.theta)
    strokes = optimize.justify(strokes)
    max_x,max_y = optimize.max_extent(strokes)

    border_path = [
      (-border[0], -border[1]),
      (max_x+border[0], -border[1]),
      (max_x+border[0], max_y+border[1]),
      (-border[0], max_y+border[1])
    ]

    for (s,f) in zip(args.speed, args.force):
      g.set(speed=s, force=f)
      if args.cut_mode==0:
        lines = optimize.optimize(strokes, border)
        for x in lines:
          g.line(*x)
      else:
        for s in strokes:
          g.closed_path(s)
      if border != [0, 0]:
        g.closed_path(border_path)

    g.end()




if __name__ == "__main__":
    main()
