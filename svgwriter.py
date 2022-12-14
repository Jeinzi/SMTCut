#!/usr/bin/env python3

# Dump strokes to an SVG file.
#
# Licensed under the terms of the GPL2, see LICENSE file.
# Copyright (c) 2017 fishpepper <fishpepper@gmail.com>

import svgwrite
from svgwrite import cm, mm

class svgwriter:
    def __init__(self, filename):
        self.dwg = svgwrite.Drawing(filename, profile='tiny')

    def draw_polygon(self, strokes, color):
        for s in strokes:
            points = []
            for p in s:
                # create polygon list and convert user units to be in inch (*90)
                points.append((p[0] * 90, p[1] * 90))
            
            poly = self.dwg.polygon(points=points, fill='none', stroke=color, stroke_width="0.01mm")
            self.dwg.add(poly)

    def finish(self):
        self.dwg.save()
