"""Flat-pattern geometry for every part. Outer profiles are shapely polygons (mm),
inner cut-outs are either shapely polygons (unioned/ subtracted) or 'obround' primitives
exported with true arcs.  Bend lines carry a label for the drawing."""
import math
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
import rack_design as D

REV = "Rev-03"

def obround(cx, cy, L, W, angle=0.0):
    """stadium slot: L overall length, W width, angle deg of long axis"""
    return dict(kind='obround', cx=cx, cy=cy, L=L, W=W, angle=angle)

def circle(cx, cy, dia):
    return dict(kind='circle', cx=cx, cy=cy, dia=dia)

def obround_poly(o, n=12):
    r = o['W'] / 2; half = o['L'] / 2 - r
    pts = []
    for i in range(n + 1):
        a = -math.pi / 2 + math.pi * i / n
        pts.append((half + r * math.cos(a), r * math.sin(a)))
    for i in range(n + 1):
        a = math.pi / 2 + math.pi * i / n
        pts.append((-half + r * math.cos(a), r * math.sin(a)))
    ca, sa = math.cos(math.radians(o['angle'])), math.sin(math.radians(o['angle']))
    return Polygon([(o['cx'] + x * ca - y * sa, o['cy'] + x * sa + y * ca) for x, y in pts])

def rounded_rect(x0, y0, x1, y1, r):
    return box(x0, y0, x1, y1).buffer(-r, join_style=1).buffer(r, join_style=1, resolution=8) if r > 0 else box(x0, y0, x1, y1)

# ------------------------------------------------------------------ SIDE RAIL
def side_rail(mirror=False):
    """Half perimeter rail: one long side + 2 corners + 2 half end-walls.
    Flat laid out along X (developed length s, 0 = joint at front/rear centre), Y across the profile:
    y=0 bottom lip edge ... y=RAIL_FLAT top return edge. Viewed from OUTSIDE face: all bends DOWN."""
    L = D.RAIL_LEN; W = D.RAIL_FLAT
    b1, b2, b3 = D.RAIL_BENDS
    outer = box(0, 0, L, W)
    cuts = []
    # --- corner relief: 3 V-notches per corner in the lip and in the flange+return
    theta = math.radians(30)
    r_mid = D.CORNER_R - D.T / 2
    w_lip = (r_mid - (D.CORNER_R - D.T - D.LIP_B)) * theta          # width at lip tip
    w_fl = (r_mid - (D.CORNER_R - D.T - D.FLANGE_T)) * theta        # width at flange tip / return
    corners = [D.HALF_END, D.HALF_END + D.CORNER_ARC + D.LONG_STRAIGHT]
    corner_marks = []
    for c0 in corners:
        corner_marks.append((c0, c0 + D.CORNER_ARC))
        for k in (0.5, 1.5, 2.5):
            s = c0 + D.CORNER_ARC * k / 3
            # bottom lip V (apex at bend line b1, relief hole)
            cuts.append(Polygon([(s - w_lip / 2, -1), (s + w_lip / 2, -1), (s, b1)]))
            cuts.append(Point(s, b1).buffer(1.25, resolution=8))
            # top flange V from b2 to b3, then straight slot through the return
            cuts.append(Polygon([(s, b2), (s + w_fl / 2, b3), (s + w_fl / 2, W + 1), (s - w_fl / 2, W + 1), (s - w_fl / 2, b3)]))
            cuts.append(Point(s, b2).buffer(1.25, resolution=8))
    outer = outer.difference(unary_union(cuts))
    # --- inner cut-outs
    inner = []
    tab_y0 = D.rail_z_to_flat(D.TAB_Z0 - 0.5); tab_y1 = D.rail_z_to_flat(D.TAB_Z1 + 0.5)
    tab_h = tab_y1 - tab_y0
    for y in D.CROSS_Y:
        s = D.cross_x_to_rail_y(y)
        for dx in (-(D.HAT_TOP / 2 - D.T / 2), (D.HAT_TOP / 2 - D.T / 2)):
            inner.append(obround(s + dx, (tab_y0 + tab_y1) / 2, tab_h, D.SLOT_W, 90))
    tie_y = D.rail_z_to_flat(D.TIE_Z)
    s_long0 = D.HALF_END + D.CORNER_ARC
    for yv in (0, 135, -135, 270, -270, 405, -405, 540, -540):
        inner.append(obround(s_long0 + D.LONG_STRAIGHT / 2 - yv, tie_y, D.TIE_SLOT[0], D.TIE_SLOT[1]))
    for s in (100, 250, 400):
        inner.append(obround(s, tie_y, D.TIE_SLOT[0], D.TIE_SLOT[1]))
        inner.append(obround(L - s, tie_y, D.TIE_SLOT[0], D.TIE_SLOT[1]))
    bends = [(b1, "DOWN 90° R1.5"), (b2, "DOWN 90° R1.5"), (b3, "DOWN 90° R1.5")]
    bend_lines = [((0, b), (L, b), lab) for b, lab in bends]
    part = dict(no=f"RRD-2001-{REV}" if not mirror else f"RRD-2002-{REV}",
                title="Side Rail PS (left)" if not mirror else "Side Rail DS (right)",
                qty=1, outer=outer, inner=inner, bend_lines=bend_lines, corner_marks=corner_marks,
                flat=(L, W), profile=D.rail_profile_segs(),
                profile_dims=[("Lip", D.LIP_B), ("Wall", D.WALL_H), ("Top flange", D.FLANGE_T), ("Return", D.RETURN_T)],
                notes=["Developed length %.1f: 2 corners rolled in-plane to outside R%.0f AFTER press-brake bends." % (L, D.CORNER_R),
                       "Corner zones (hatched) : web only is rolled; weld V-notch seams closed in lip, flange and return, grind flush.",
                       "Two halves (PS + DS) butt-weld at front and rear centre line; fit splice plate RRD-2006 behind joint.",
                       "Tab slots %.1f x %.1f receive cross-member tabs (RRD-2003/2004) - weld tabs outside, grind flush." % (D.SLOT_W, tab_h),
                       "DS rail is the mirror image: same profile, mirrored flat (bend DOWN viewed from outside face)."])
    if mirror:
        from shapely.affinity import scale
        part['outer'] = scale(outer, xfact=-1, yfact=1, origin=(L / 2, 0))
        for o in part['inner']:
            o['cx'] = L - o['cx']
            if o['kind'] == 'obround': o['angle'] = -o['angle']
    return part

# ------------------------------------------------------------------ CROSS MEMBER
def cross(mount=False):
    L = D.CROSS_LEN; W = D.CROSS_FLAT
    b1, b2, b3, b4 = D.CROSS_BENDS
    x0, x1 = -L / 2, L / 2
    outer = box(x0, 0, x1, W)
    notch_len = D.LIP_B + 1.0
    web_start = b1 + D.BA90 / 2            # flat y where straight web starts (z = 3)
    cuts = [box(x0 - 1, -1, x0 + notch_len, web_start), box(x1 - notch_len, -1, x1 + 1, web_start),
            box(x0 - 1, W - web_start, x0 + notch_len, W + 1), box(x1 - notch_len, W - web_start, x1 + 1, W + 1),
            box(x0 - 1, b2, x0 + 1.0, b3), box(x1 - 1.0, b2, x1 + 1, b3)]      # top flange 1 mm clearance
    outer = outer.difference(unary_union(cuts))
    # tabs on both webs, both ends
    ty0 = D.TAB_Z0 + web_start - (D.R_IN + D.T); ty1 = D.TAB_Z1 + web_start - (D.R_IN + D.T)
    tabs = [box(x1 - 0.5, ty0, x1 + D.TAB_PROUD, ty1), box(x0 - D.TAB_PROUD, ty0, x0 + 0.5, ty1),
            box(x1 - 0.5, W - ty1, x1 + D.TAB_PROUD, W - ty0), box(x0 - D.TAB_PROUD, W - ty1, x0 + 0.5, W - ty0)]
    outer = unary_union([outer] + tabs)
    inner = []
    ymid = (b2 + b3) / 2
    for xc in (0, 280, -280):
        inner.append(obround(xc, ymid, D.ACC_SLOT[0], D.ACC_SLOT[1]))
    if mount:
        for xc in (D.MOUNT_X, -D.MOUNT_X):
            inner.append(obround(xc, ymid, 30, 11))
    bends = [(b1, "DOWN 90° R1.5"), (b2, "DOWN 90° R1.5"), (b3, "DOWN 90° R1.5"), (b4, "DOWN 90° R1.5")]
    bend_lines = [((x0 + notch_len, b), (x1 - notch_len, b), lab) if b in (b1, b4) else ((x0, b), (x1, b), lab) for b, lab in bends]
    part = dict(no=f"RRD-2004-{REV}" if mount else f"RRD-2003-{REV}",
                title="Mount Cross Member" if mount else "Deck Cross Member",
                qty=2 if mount else 5, outer=outer, inner=inner, bend_lines=bend_lines, corner_marks=[],
                flat=(L + 2 * D.TAB_PROUD, W), profile=D.cross_profile_segs(),
                profile_dims=[("Foot", D.HAT_FOOT), ("Web", D.HAT_H), ("Top", D.HAT_TOP), ("Web", D.HAT_H), ("Foot", D.HAT_FOOT)],
                notes=["Top-hat section, open side DOWN (feet rest on canopy roof skin).",
                       "End tabs (4 off, %.0f x %.1f) pass through side-rail wall slots; weld outside and grind flush." % (D.TAB_Z1 - D.TAB_Z0, D.T),
                       "Feet notched %.0f mm at ends to clear side-rail bottom lip." % notch_len,
                       "3 x accessory slots %.0f x %.0f in deck face (rated tie-down points)." % D.ACC_SLOT]
                      + (["Mount slots 30 x 11 at X = ±%.1f: VERIFY against canopy roof holes before cutting." % D.MOUNT_X,
                          "Fit closing plate RRD-2005 inside hat, flush with feet, before fitting to rack (box section)."] if mount else []))
    return part

# ------------------------------------------------------------------ FLAT PLATES
def closer():
    L = 1000.0; W = D.CLOSER_W
    outer = rounded_rect(-L / 2, -W / 2, L / 2, W / 2, 3)
    inner = [circle(D.MOUNT_X, 0, 12.0), circle(-D.MOUNT_X, 0, 12.0)]
    return dict(no=f"RRD-2005-{REV}", title="Mount Cross Closing Plate", qty=2, outer=outer, inner=inner,
                bend_lines=[], corner_marks=[], flat=(L, W), profile=None, profile_dims=[],
                notes=["Flat plate. Slides inside RRD-2004 hat, flush with feet; stitch weld 25/100 to webs from below.",
                       "Ø12 holes line up with mount slots; fit spacer tube between plate and roof rib (see assembly)."])

def splice():
    outer = rounded_rect(-30, -45, 30, 45, 3)
    return dict(no=f"RRD-2006-{REV}", title="Rail Splice Plate", qty=2, outer=outer, inner=[],
                bend_lines=[], corner_marks=[], flat=(60, 90), profile=None, profile_dims=[],
                notes=["Flat plate, fits inside wall behind PS/DS butt joint (front and rear centre).",
                       "Plug/fillet weld to wall from inside, both halves."])

def backing():
    outer = rounded_rect(-60, -15, 60, 15, 3)
    inner = [obround(0, 0, 24, 11, 0)]
    return dict(no=f"RRD-2007-{REV}", title="Roof Backing Plate", qty=4, outer=outer, inner=inner,
                bend_lines=[], corner_marks=[], flat=(120, 30), profile=None, profile_dims=[],
                notes=["Flat plate, fits inside canopy under roof rib top flat (35 wide channel).",
                       "Slot 24 x 11 along vehicle axis for M10 mounting bolt."])

def all_parts():
    return [side_rail(False), side_rail(True), cross(False), cross(True), closer(), splice(), backing()]

if __name__ == '__main__':
    for p in all_parts():
        print(p['no'], p['title'], 'qty', p['qty'], 'flat %.1f x %.1f' % p['flat'], 'area %.0f mm2' % p['outer'].area,
              'mass %.2f kg' % (p['outer'].area * D.T * D.RHO))
