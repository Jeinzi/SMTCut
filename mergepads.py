# merge multiple small pads to one big pad spanning the same area
import math
import numpy as np
from scipy.spatial import ConvexHull

DEBUG = False
DEBUG_SVG = False

def log(s):
    if DEBUG:
        print(s)

def distance(p1, p2):
    return math.sqrt(math.pow((p1[0]-p2[0]), 2) + math.pow((p1[1]-p2[1]), 2))

def minimum_bounding_rectangle(npoints, scale = 1.0):
    """
    Find the smallest bounding rectangle for a set of points.
    Returns a set of points representing the corners of the bounding box.
    source: 
    https://gis.stackexchange.com/questions/22895/finding-minimum-area-rectangle-for-given-points

    :param points: an nx2 matrix of coordinates
    :rval: an nx2 matrix of coordinates
    """
    from scipy.ndimage.interpolation import rotate
    pi2 = np.pi/2.

    points = np.array(npoints)
    # get the convex hull for the points
    hull_points = points[ConvexHull(points).vertices]

    # calculate edge angles
    edges = np.zeros((len(hull_points)-1, 2))
    edges = hull_points[1:] - hull_points[:-1]

    angles = np.zeros((len(edges)))
    angles = np.arctan2(edges[:, 1], edges[:, 0])

    angles = np.abs(np.mod(angles, pi2))
    angles = np.unique(angles)

    # find rotation matrices
    rotations = np.vstack([
        np.cos(angles),
        np.cos(angles-pi2),
        np.cos(angles+pi2),
        np.cos(angles)]).T
    rotations = rotations.reshape((-1, 2, 2))

    # apply rotations to the hull
    rot_points = np.dot(rotations, hull_points.T)

    # find the bounding points
    min_x = np.nanmin(rot_points[:, 0], axis=1)
    max_x = np.nanmax(rot_points[:, 0], axis=1)
    min_y = np.nanmin(rot_points[:, 1], axis=1)
    max_y = np.nanmax(rot_points[:, 1], axis=1)

    # find the box with the best area
    areas = (max_x - min_x) * (max_y - min_y)
    best_idx = np.argmin(areas)

    # return the best box
    x1 = max_x[best_idx]
    x2 = min_x[best_idx]
    y1 = max_y[best_idx]
    y2 = min_y[best_idx]
    r = rotations[best_idx]

    # rescale box along its smallest width
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    dx = abs(x1 - x2)
    dy = abs(y1 - y2)
    if (dx < dy):
        x1 = cx - scale * (cx - x1)
        x2 = cx + scale * (x2 - cx)
    else:
        y1 = cy - scale * (cy - y1)
        y2 = cy + scale * (y2 - cy)

    rval = np.zeros((4, 2))
    rval[0] = np.dot([x1, y2], r)
    rval[1] = np.dot([x2, y2], r)
    rval[2] = np.dot([x2, y1], r)
    rval[3] = np.dot([x1, y1], r)

    return rval.tolist()

# helper to find rectangles that are small
def small_rect(stroke, min_size):
    log("small rect: " + str(stroke))
    if (len(stroke) != 5):
        # skip cuts that are no rectangles
        return False
    log("distance from " + str(stroke))

    # check if any of the cuts is smaller the minimum size
    for p1 in stroke:
        for p2 in stroke:
            if p1 != p2:
                dist = distance(p1, p2)
                log("dist["+str(p1)+", "+str(p2)+"] = "+str(dist))
                if (dist < min_size):
                    return True
    # not a small rect
    return False

# find minimum distance between two sets of points
def min_stroke_distance(s1, s2):
    min_dist = float("inf")
    for p1 in s1:
        for p2 in s2:
            min_dist = min(min_dist, distance(p1, p2))
    return min_dist

# calculate the area of a given polygon
def polygon_area(corners):
    n = len(corners) # of corners
    if corners[0] != corners[n-1]:
        print("ERROR: polygon is not closed. aborting")
        exit(0)

    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += corners[i][0] * corners[j][1]
        area -= corners[j][0] * corners[i][1]
    area = abs(area) / 2.0
    return area

# fetch a list of all small rects
def fix_small_geometry(strokes, min_size, min_dist):
    small_rects = []
    processed_strokes  = []

    # sort into small and normal cuts
    for s in strokes:
        if not small_rect(s, min_size):
            # not a small rect, keep it
            processed_strokes.append(s)
        else:
            # small rect, add to small list
            log("got small rect " + str(s))
            small_rects.append(s)

    # small rects list is now searched for rects that are close together
    log("trying to merge close rects")
    joined_rects = []
    for s1 in small_rects:
       joined = False
       index = 0
       for (index, (area_s2, s2)) in enumerate(joined_rects):
             dist = min_stroke_distance(s1, s2)
             log("distance: " + str(dist) + " (min=" + str(min_dist)+ ")")
             if dist < min_dist:
                 # both strokes are close to each other, join into one stroke set
                 if not joined:
                     # new join
                     bbox = minimum_bounding_rectangle(s1 + s2)
                     # keep track of area used
                     joined_rects[index][0] = area_s2 + polygon_area(s1)
                     # replace current stroke with new bounding box and close polygon
                     joined_rects[index][1] = bbox + [bbox[0]]
                 else:
                     # this has been joined to something else before, make sure to
                     # append this to the previous join:
                     bbox = minimum_bounding_rectangle(s2 + joined_rects[joined_to][1])
                     # keep track of area used
                     joined_rects[joined_to][0] = area_s2 + joined_rects[joined_to][0]
                     # replace current stroke with new bounding box and close polygon
                     joined_rects[joined_to][1] = bbox + [bbox[0]]

                 # mark rect as joined
                 joined = True
                 joined_to = index

       if not joined:
           log("adding new polygon to list: " + str(s1))
           area = polygon_area(s1)
           joined_rects.append([area, s1])

    # merging might have produced subsets that are not merged yet
    # test if all small rects are merged
    for i,s in enumerate(joined_rects):
        if small_rect(s[1], min_size):
            # small rect, add to small list
            log("WARNING: still got a small rect at " + str(i) + " = " +  str(s))

    # shrink joined rects to accomodate for joining 
    smallrect_strokes = []
    for r in joined_rects:
        area_before = r[0]
        points = r[1]
        area_now = polygon_area(points)
        scale = area_before / area_now
        log("scale " + str(scale))

        # fetch a new bounding box that is scaled along its shorter side
        bbox = minimum_bounding_rectangle(points, scale = scale)

        # make sure to close polygon
        smallrect_strokes.append(bbox + [bbox[0]])         

    
    if (DEBUG_SVG):
        import svgwriter
        svg = svgwriter.svgwriter("_tmp_gerber.svg")
        svg.draw_polygon(smallrect_strokes, 'blue')
        svg.draw_polygon(processed_strokes, 'black')
        svg.draw_polygon(small_rects, 'red')
        svg.finish()

    return smallrect_strokes + processed_strokes 

