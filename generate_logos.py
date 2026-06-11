"""
Veld Armour — 3x CNC Laser Cut Logo Designs
Material: 1.5mm 304 Brushed Stainless Steel
All dimensions in mm. Min feature size >= 2mm for clean cuts.
"""

import ezdxf
from ezdxf import units
import math

# ─── helpers ──────────────────────────────────────────────────────────────────

def add_lwpoly(msp, points, closed=True, layer="CUT"):
    poly = msp.add_lwpolyline(points, dxfattribs={"layer": layer, "closed": closed})
    return poly

def add_arc(msp, center, radius, start_angle, end_angle, layer="CUT"):
    return msp.add_arc(center, radius, start_angle, end_angle, dxfattribs={"layer": layer})

def add_circle(msp, center, radius, layer="CUT"):
    return msp.add_circle(center, radius, dxfattribs={"layer": layer})

def add_line(msp, start, end, layer="CUT"):
    return msp.add_line(start, end, dxfattribs={"layer": layer})

def make_doc():
    doc = ezdxf.new("R2010")
    doc.units = units.MM
    msp = doc.modelspace()
    doc.layers.add("CUT", color=7)      # white = cut line
    doc.layers.add("ENGRAVE", color=3)  # green = engrave / etch
    return doc, msp

def shield_points(cx, cy, w, h):
    """Pentagon shield outline: top-flat, rounded bottom point."""
    hw = w / 2
    # 5 control points: TL, TR, mid-right, bottom-point, mid-left
    notch = h * 0.15   # how far down the top corners sit
    shoulder = h * 0.6  # where sides start curving to point
    return [
        (cx - hw, cy + notch),          # top-left
        (cx + hw, cy + notch),          # top-right
        (cx + hw, cy - shoulder),       # right shoulder
        (cx,      cy - h + notch),      # bottom point
        (cx - hw, cy - shoulder),       # left shoulder
    ]

def approx_quad_bezier(p0, p1, p2, n=16):
    """Approximate quadratic bezier as polyline points."""
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
        y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
        pts.append((x, y))
    return pts

def approx_cubic_bezier(p0, p1, p2, p3, n=24):
    pts = []
    for i in range(n + 1):
        t = i / n
        x = (1-t)**3*p0[0] + 3*(1-t)**2*t*p1[0] + 3*(1-t)*t**2*p2[0] + t**3*p3[0]
        y = (1-t)**3*p0[1] + 3*(1-t)**2*t*p1[1] + 3*(1-t)*t**2*p2[1] + t**3*p3[1]
        pts.append((x, y))
    return pts

def smooth_shield(cx, cy, w, h):
    """
    Shield with smooth curved bottom.
    SVG-inspired: top flat, sides straight to 60% down, then bezier to bottom point.
    """
    hw = w / 2
    top_y   = cy + h * 0.10   # top edge (slight inset from very top)
    corner_y = cy + h * 0.12
    side_bot_y = cy - h * 0.38   # where straight sides end
    bot_y   = cy - h * 0.50    # bottom point

    # left side curve control
    left_ctrl = (cx - hw, bot_y + (side_bot_y - bot_y) * 0.1)
    # right side curve control
    right_ctrl = (cx + hw, bot_y + (side_bot_y - bot_y) * 0.1)

    pts = []
    # top-left to top-right (flat top)
    pts.append((cx - hw + 4, top_y))
    pts.append((cx + hw - 4, top_y))
    # top-right corner (rounded) → right side straight
    pts.append((cx + hw, corner_y))
    # right side down to shoulder
    pts.append((cx + hw, side_bot_y))
    # curve to bottom point
    curve_r = approx_quad_bezier((cx + hw, side_bot_y), right_ctrl, (cx, bot_y), 20)
    pts.extend(curve_r[1:])
    # curve from bottom point to left side
    curve_l = approx_quad_bezier((cx, bot_y), left_ctrl, (cx - hw, side_bot_y), 20)
    pts.extend(curve_l[1:])
    # left side up
    pts.append((cx - hw, corner_y))
    return pts

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN 1 — Classic Shield (150mm tall, portrait)
# VA monogram + VELD ARMOUR wordmark
# ─────────────────────────────────────────────────────────────────────────────

def letter_V(cx, cy, w, h, layer="CUT"):
    """Stroke-outline V letter as closed polyline. Thick stroke."""
    sw = w * 0.20   # stroke width
    pts = [
        (cx - w/2,          cy + h/2),
        (cx - w/2 + sw,     cy + h/2),
        (cx,                cy - h/2 + sw*1.5),
        (cx + w/2 - sw,     cy + h/2),
        (cx + w/2,          cy + h/2),
        (cx,                cy - h/2),
    ]
    return pts

def letter_A(cx, cy, w, h, layer="CUT"):
    """Stroke-outline A letter."""
    sw = w * 0.18
    # outer A outline (clockwise)
    apex_x, apex_y = cx, cy + h/2
    bl_x, bl_y = cx - w/2, cy - h/2
    br_x, br_y = cx + w/2, cy - h/2

    # cross bar position
    bar_y = cy - h * 0.05
    # where crossbar meets the left/right sides
    t = (bar_y - bl_y) / h
    bar_lx = bl_x + t * (apex_x - bl_x)
    bar_rx = br_x + t * (apex_x - br_x)

    # inner triangle (cutout for the enclosed space above crossbar)
    inner_apex_x = cx
    inner_apex_y = apex_y - sw * 1.8
    inner_bl_x = bar_lx + sw * 0.7
    inner_bl_y = bar_y + sw * 0.5
    inner_br_x = bar_rx - sw * 0.7
    inner_br_y = bar_y + sw * 0.5

    return {
        "outer": [
            (apex_x, apex_y),
            (br_x, br_y),
            (bar_rx + sw * 0.4, br_y),
            (bar_rx + sw * 0.4, bar_y - sw * 0.4),
            (bar_lx - sw * 0.4, bar_y - sw * 0.4),
            (bar_lx - sw * 0.4, br_y),
            (bl_x, bl_y),
        ],
        "inner": [
            (inner_apex_x, inner_apex_y),
            (inner_br_x, inner_br_y),
            (inner_bl_x, inner_bl_y),
        ],
        "crossbar": [
            (bar_lx + sw * 0.5, bar_y + sw * 0.55),
            (bar_rx - sw * 0.5, bar_y + sw * 0.55),
            (bar_rx - sw * 0.5, bar_y - sw * 0.55),
            (bar_lx + sw * 0.5, bar_y - sw * 0.55),
        ],
    }


def design1(filename):
    """
    Design 1: Classic VA Shield
    - Outer shield: 120 × 145mm
    - VA monogram centred, large
    - 'VELD ARMOUR' as geometric dot text below
    - 4× mounting holes Ø5mm at corners
    """
    doc, msp = make_doc()

    cx, cy = 0, 0
    sw, sh = 120, 145  # shield width, height

    # ── outer shield ──────────────────────────────────────────────────────────
    pts = smooth_shield(cx, cy, sw, sh)
    add_lwpoly(msp, pts, closed=True, layer="CUT")

    # ── inner shield (offset ~6mm for border effect) ──────────────────────────
    pts_inner = smooth_shield(cx, cy, sw - 12, sh - 13)
    add_lwpoly(msp, pts_inner, closed=True, layer="CUT")

    # ── VA monogram ───────────────────────────────────────────────────────────
    # V — left half of monogram, centred slightly left
    lw, lh = 46, 52   # letter bounding box
    sw2 = lw * 0.18   # stroke width

    # V outer shape
    v_cx = cx - 16
    v_cy = cy + 8
    v_outer = [
        (v_cx - lw/2,         v_cy + lh/2),
        (v_cx + lw/2,         v_cy + lh/2),
        (v_cx,                v_cy - lh/2),
    ]
    # V inner cutout (hollow interior)
    v_inner = [
        (v_cx - lw/2 + sw2,   v_cy + lh/2 - sw2*0.5),
        (v_cx + lw/2 - sw2,   v_cy + lh/2 - sw2*0.5),
        (v_cx,                v_cy - lh/2 + sw2*2.0),
    ]
    add_lwpoly(msp, v_outer, closed=True, layer="CUT")
    add_lwpoly(msp, v_inner, closed=True, layer="CUT")

    # A — right of monogram
    a_cx = cx + 16
    a_cy = cy + 8
    a = letter_A(a_cx, a_cy, lw, lh)
    add_lwpoly(msp, a["outer"], closed=True, layer="CUT")
    add_lwpoly(msp, a["crossbar"], closed=True, layer="CUT")

    # ── divider line ──────────────────────────────────────────────────────────
    add_lwpoly(msp, [(cx - 36, cy - 34), (cx + 36, cy - 34)], closed=False, layer="CUT")
    add_lwpoly(msp, [(cx - 36, cy - 37), (cx + 36, cy - 37)], closed=False, layer="CUT")

    # ── diamond accent ────────────────────────────────────────────────────────
    d = 3.5
    add_lwpoly(msp, [(cx, cy - 35.5 - d), (cx + d, cy - 35.5), (cx, cy - 35.5 + d), (cx - d, cy - 35.5)], closed=True, layer="CUT")

    # ── dot-matrix brand name ─────────────────────────────────────────────────
    # "VELD ARMOUR" as small Ø2mm circles (dot-engraving style)
    # Each letter is 6 dots wide × 7 dots tall; dot pitch = 3.5mm
    font = {
        'V': [(0,6),(1,5),(2,4),(3,3),(4,4),(5,5),(6,6),(1,6),(2,5),(3,4),(4,5),(5,6)],
        'E': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,6),(3,6),(1,3),(2,3),(3,3),(1,0),(2,0),(3,0)],
        'L': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,0),(2,0),(3,0)],
        'D': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,5),(3,4),(3,3),(3,2),(2,1),(1,0)],
        ' ': [],
        'A': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(1,6),(2,6),(3,5),(3,4),(3,3),(3,2),(3,1),(3,0),(1,3),(2,3)],
        'R': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,5),(2,4),(1,3),(2,2),(3,1),(3,0)],
        'M': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,5),(2,4),(3,5),(4,6),(4,5),(4,4),(4,3),(4,2),(4,1),(4,0)],
        'O': [(0,1),(0,2),(0,3),(0,4),(0,5),(1,6),(2,6),(3,5),(3,4),(3,3),(3,2),(3,1),(2,0),(1,0)],
        'U': [(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,0),(2,0),(3,1),(3,2),(3,3),(3,4),(3,5),(3,6)],
    }

    text = "VELD ARMOUR"
    dot_r = 1.0
    dot_pitch = 3.2
    letter_w = 4 * dot_pitch
    gap = dot_pitch * 0.8
    total_w = len(text) * (letter_w + gap) - gap
    # count spaces as narrower
    total_w = 0
    for ch in text:
        if ch == ' ':
            total_w += gap * 2
        else:
            total_w += letter_w + gap
    total_w -= gap

    tx = cx - total_w / 2
    ty = cy - 50
    for ch in text:
        if ch == ' ':
            tx += gap * 2
            continue
        dots = font.get(ch, [])
        for (col, row) in dots:
            dx = tx + col * dot_pitch
            dy = ty + row * dot_pitch
            add_circle(msp, (dx, dy), dot_r, layer="CUT")
        tx += letter_w + gap

    # ── mounting holes Ø5mm ───────────────────────────────────────────────────
    for hx, hy in [(-45, 62), (45, 62), (-45, -56), (45, -56)]:
        add_circle(msp, (hx, hy), 2.5, layer="CUT")

    doc.saveas(filename)
    print(f"Saved {filename}")


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN 2 — Horizontal Name-Plate / Entry Badge
# 200mm × 60mm rectangle, shield icon left, wordmark right
# ─────────────────────────────────────────────────────────────────────────────

def design2(filename):
    doc, msp = make_doc()

    pw, ph = 200, 60
    r = 8  # corner radius

    # ── rounded rectangle outer ───────────────────────────────────────────────
    x0, y0 = -pw/2, -ph/2
    x1, y1 =  pw/2,  ph/2
    pts = [
        (x0+r, y0), (x1-r, y0),   # bottom edge
        (x1, y0+r), (x1, y1-r),   # right edge
        (x1-r, y1), (x0+r, y1),   # top edge
        (x0, y1-r), (x0, y0+r),   # left edge
    ]
    # build rounded rect via arcs + lines
    msp.add_line((x0+r, y0), (x1-r, y0), dxfattribs={"layer":"CUT"})
    msp.add_arc((x1-r, y0+r), r, 270, 0,   dxfattribs={"layer":"CUT"})
    msp.add_line((x1, y0+r), (x1, y1-r),   dxfattribs={"layer":"CUT"})
    msp.add_arc((x1-r, y1-r), r, 0,   90,  dxfattribs={"layer":"CUT"})
    msp.add_line((x1-r, y1), (x0+r, y1),   dxfattribs={"layer":"CUT"})
    msp.add_arc((x0+r, y1-r), r, 90,  180, dxfattribs={"layer":"CUT"})
    msp.add_line((x0, y1-r), (x0, y0+r),   dxfattribs={"layer":"CUT"})
    msp.add_arc((x0+r, y0+r), r, 180, 270, dxfattribs={"layer":"CUT"})

    # ── inner rounded rectangle (border effect, offset 3.5mm) ─────────────────
    iw, ih, ir = pw - 7, ph - 7, 5
    ix0, iy0 = -iw/2, -ih/2
    ix1, iy1 =  iw/2,  ih/2
    msp.add_line((ix0+ir, iy0), (ix1-ir, iy0), dxfattribs={"layer":"CUT"})
    msp.add_arc((ix1-ir, iy0+ir), ir, 270, 0,   dxfattribs={"layer":"CUT"})
    msp.add_line((ix1, iy0+ir), (ix1, iy1-ir),  dxfattribs={"layer":"CUT"})
    msp.add_arc((ix1-ir, iy1-ir), ir, 0,   90,  dxfattribs={"layer":"CUT"})
    msp.add_line((ix1-ir, iy1), (ix0+ir, iy1),  dxfattribs={"layer":"CUT"})
    msp.add_arc((ix0+ir, iy1-ir), ir, 90,  180, dxfattribs={"layer":"CUT"})
    msp.add_line((ix0, iy1-ir), (ix0, iy0+ir),  dxfattribs={"layer":"CUT"})
    msp.add_arc((ix0+ir, iy0+ir), ir, 180, 270, dxfattribs={"layer":"CUT"})

    # ── vertical divider ─────────────────────────────────────────────────────
    div_x = -50
    msp.add_line((div_x, -20), (div_x, 20), dxfattribs={"layer":"CUT"})

    # ── mini shield left side ─────────────────────────────────────────────────
    s_cx, s_cy = -75, 0
    s_pts = smooth_shield(s_cx, s_cy, 32, 38)
    add_lwpoly(msp, s_pts, closed=True, layer="CUT")
    s_pts2 = smooth_shield(s_cx, s_cy, 32-6, 38-7)
    add_lwpoly(msp, s_pts2, closed=True, layer="CUT")

    # VA inside mini shield
    # simplified: just V shape and A shape, small
    for sx, ch_pts in [
        (-81, [(-81,-4-8),(-81+5,-4-8),(-78,-4+8),(-75+3,-4-8),(-75+8,-4-8),(-75,-4+8+2)]),
        (-68, [(-68,-4-8),(-68+8,-4-8),(-68+8,-4),(-68+4,-4+8),(-68,-4+8),(-68,-4-8)]),
    ]:
        pass

    # Simple V
    v_pts = [(-82, 10), (-78, 10), (-75, -8), (-72, 10), (-68, 10), (-75, -10)]
    add_lwpoly(msp, v_pts, closed=True, layer="CUT")
    # Simple A
    a_pts = [(-63, -10), (-57, -10), (-57, -6), (-60, 10), (-63, -6)]
    add_lwpoly(msp, a_pts, closed=True, layer="CUT")

    # ── "VELD ARMOUR" large dot text right side ───────────────────────────────
    # Two rows: "VELD" top, "ARMOUR" bottom
    font = {
        'V': [(0,6),(1,5),(2,4),(3,3),(4,4),(5,5),(6,6)],
        'E': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,6),(3,6),(1,3),(2,3),(1,0),(2,0),(3,0)],
        'L': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,0),(2,0),(3,0)],
        'D': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,5),(3,4),(3,3),(3,2),(2,1),(1,0)],
        'A': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(1,6),(2,6),(3,5),(3,4),(3,3),(3,2),(3,1),(3,0),(1,3),(2,3)],
        'R': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,5),(2,4),(1,3),(2,2),(3,1),(3,0)],
        'M': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,5),(2,4),(3,5),(4,6),(4,5),(4,4),(4,3),(4,2),(4,1),(4,0)],
        'O': [(0,1),(0,2),(0,3),(0,4),(0,5),(1,6),(2,6),(3,5),(3,4),(3,3),(3,2),(3,1),(2,0),(1,0)],
        'U': [(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,0),(2,0),(3,1),(3,2),(3,3),(3,4),(3,5),(3,6)],
    }
    dp = 2.8   # dot pitch
    dr = 0.9   # dot radius
    lw2 = 4 * dp

    for row_text, row_y in [("VELD", 8), ("ARMOUR", -16)]:
        total = len(row_text) * (lw2 + dp*0.7) - dp*0.7
        rx = div_x + 12 + (92 - total) / 2
        for ch in row_text:
            for (col, r_) in font.get(ch, []):
                add_circle(msp, (rx + col*dp, row_y + r_*dp), dr, layer="CUT")
            rx += lw2 + dp * 0.7

    # ── "BUILT FOR THE VELD" tagline ──────────────────────────────────────────
    font2 = {
        'B': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,3),(1,2),(2,1),(1,0)],
        'U': [(0,1),(0,2),(0,3),(0,4),(1,0),(2,0),(3,1),(3,2),(3,3),(3,4)],
        'I': [(0,0),(0,1),(0,2),(0,3),(0,4)],
        'L': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,0),(2,0)],
        'T': [(0,4),(1,4),(2,4),(1,0),(1,1),(1,2),(1,3)],
        'F': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,4),(1,2),(2,2)],
        'O': [(0,1),(0,2),(0,3),(1,4),(2,4),(3,3),(3,2),(3,1),(2,0),(1,0)],
        'R': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,3),(1,2),(2,1),(2,0)],
        'H': [(0,0),(0,1),(0,2),(0,3),(0,4),(3,0),(3,1),(3,2),(3,3),(3,4),(1,2),(2,2)],
        'E': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,4),(1,2),(2,2),(1,0),(2,0)],
        'V': [(0,4),(1,3),(2,2),(3,3),(4,4),(1,4),(3,4)],
        'D': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,3),(2,2),(2,1),(1,0)],
        ' ': [],
    }
    tag = "BUILT FOR THE VELD"
    dp3 = 1.6
    dr3 = 0.55
    lw3 = 4 * dp3
    total3 = 0
    for ch in tag:
        total3 += (dp3*2 if ch == ' ' else lw3 + dp3*0.6)
    total3 -= dp3*0.6
    rx3 = div_x + 12 + (92 - total3) / 2
    ty3 = -26
    for ch in tag:
        if ch == ' ':
            rx3 += dp3 * 2
            continue
        for (col, r_) in font2.get(ch, []):
            add_circle(msp, (rx3 + col*dp3, ty3 + r_*dp3), dr3, layer="CUT")
        rx3 += lw3 + dp3 * 0.6

    # ── mounting holes ────────────────────────────────────────────────────────
    for hx, hy in [(-88, 22), (88, 22), (-88, -22), (88, -22)]:
        add_circle(msp, (hx, hy), 2.5, layer="CUT")

    doc.saveas(filename)
    print(f"Saved {filename}")


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN 3 — Circular Badge (Ø160mm)
# "VELD ARMOUR" arc top, "BUILT FOR THE VELD" arc bottom
# Shield + VA centre
# ─────────────────────────────────────────────────────────────────────────────

def design3(filename):
    doc, msp = make_doc()

    cx, cy = 0, 0
    R_out = 80   # outer radius
    R_mid = 73   # inner ring of outer band
    R_inn = 66   # inner circle

    # ── outer ring ─────────────────────────────────────────────────────────────
    add_circle(msp, (cx, cy), R_out, layer="CUT")
    add_circle(msp, (cx, cy), R_mid, layer="CUT")
    add_circle(msp, (cx, cy), R_inn, layer="CUT")

    # ── tick marks around ring (every 30°) ────────────────────────────────────
    for i in range(12):
        angle = math.radians(i * 30)
        if i % 3 == 0:  # major tick
            r1, r2 = R_mid, R_inn
        else:            # minor tick (inside outer band only)
            r1, r2 = R_out - 2, R_mid
        x1 = cx + math.cos(angle) * r1
        y1 = cy + math.sin(angle) * r1
        x2 = cx + math.cos(angle) * r2
        y2 = cy + math.sin(angle) * r2
        add_line(msp, (x1, y1), (x2, y2), layer="CUT")

    # ── diamond accents at 90°/270° ───────────────────────────────────────────
    for angle in [90, 270]:
        ang = math.radians(angle)
        mx = cx + math.cos(ang) * (R_mid + (R_out - R_mid) / 2)
        my = cy + math.sin(ang) * (R_mid + (R_out - R_mid) / 2)
        d = 2.5
        add_lwpoly(msp, [(mx, my+d),(mx+d, my),(mx, my-d),(mx-d, my)], closed=True, layer="CUT")

    # ── shield centre ─────────────────────────────────────────────────────────
    s_pts = smooth_shield(cx, cy + 4, 56, 66)
    add_lwpoly(msp, s_pts, closed=True, layer="CUT")
    s_pts2 = smooth_shield(cx, cy + 4, 46, 55)
    add_lwpoly(msp, s_pts2, closed=True, layer="CUT")

    # ── VA monogram in shield ─────────────────────────────────────────────────
    v_pts = [(-19, 22), (-14, 22), (-7, 0), (0, 22), (5, 22), (-7, -4)]
    add_lwpoly(msp, v_pts, closed=True, layer="CUT")
    # A
    a_pts = [(7, -4), (21, -4), (21, 4), (14, 22), (7, 4)]
    add_lwpoly(msp, a_pts, closed=True, layer="CUT")
    # A crossbar cutout
    add_lwpoly(msp, [(9, 7),(19, 7),(19, 12),(9, 12)], closed=True, layer="CUT")

    # ── dot-text "VELD ARMOUR" in arc along top (radius ~69mm) ───────────────
    # Place dots along arc from ~155° to ~25° (going through top = 90°)
    font = {
        'V': [(0,6),(1,5),(2,4),(3,3),(4,4),(5,5),(6,6)],
        'E': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,6),(3,6),(1,3),(2,3),(1,0),(2,0),(3,0)],
        'L': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,0),(2,0),(3,0)],
        'D': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,5),(3,4),(3,3),(3,2),(2,1),(1,0)],
        'A': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(1,6),(2,6),(3,5),(3,4),(3,3),(3,2),(3,1),(3,0),(1,3),(2,3)],
        'R': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,6),(2,5),(2,4),(1,3),(2,2),(3,1),(3,0)],
        'M': [(0,0),(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,5),(2,4),(3,5),(4,6),(4,5),(4,4),(4,3),(4,2),(4,1),(4,0)],
        'O': [(0,1),(0,2),(0,3),(0,4),(0,5),(1,6),(2,6),(3,5),(3,4),(3,3),(3,2),(3,1),(2,0),(1,0)],
        'U': [(0,1),(0,2),(0,3),(0,4),(0,5),(0,6),(1,0),(2,0),(3,1),(3,2),(3,3),(3,4),(3,5),(3,6)],
    }
    # Place "VELD ARMOUR" along top arc
    text_top = "VELD ARMOUR"
    arc_r = 69.5
    dp_t = 2.2
    dr_t = 0.75
    lw_t = 4 * dp_t
    gap_t = dp_t * 0.5
    space_t = dp_t * 2

    total_t = 0
    for ch in text_top:
        total_t += space_t if ch == ' ' else lw_t + gap_t
    total_t -= gap_t

    # arc from +angle_span to -angle_span around 90° (top)
    # angular width in radians for the total text
    angle_span = (total_t / arc_r) / 2  # radians
    start_angle = math.pi/2 + angle_span
    cur_angle = start_angle

    for ch in text_top:
        if ch == ' ':
            cur_angle -= space_t / arc_r
            continue
        ch_width = lw_t
        for (col, row) in font.get(ch, []):
            # letter local coords: (col*dp, row*dp)
            lx = col * dp_t - ch_width/2
            ly = row * dp_t
            # rotate by current arc angle
            a = cur_angle - (ch_width/2) / arc_r
            a_char = a + lx / arc_r
            r_char = arc_r + ly - (lw_t*6*dp_t)/2 * 0    # radial offset
            r_char = arc_r - 3 + (row * dp_t)
            px = cx + math.cos(a_char) * r_char
            py = cy + math.sin(a_char) * r_char
            add_circle(msp, (px, py), dr_t, layer="CUT")
        cur_angle -= (ch_width + gap_t) / arc_r

    # ── "BUILT FOR THE VELD" along bottom arc ────────────────────────────────
    font2 = {
        'B': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,3),(1,2),(2,1),(1,0)],
        'U': [(0,0),(0,1),(0,2),(0,3),(0,4),(2,0),(3,1),(3,2),(3,3),(3,4)],
        'I': [(0,0),(0,1),(0,2),(0,3),(0,4)],
        'L': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,0),(2,0)],
        'T': [(0,4),(1,4),(2,4),(1,0),(1,1),(1,2),(1,3)],
        'F': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,4),(1,2)],
        'O': [(0,1),(0,2),(0,3),(1,4),(2,4),(3,3),(3,2),(3,1),(2,0),(1,0)],
        'R': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,3),(1,2),(2,1),(2,0)],
        'H': [(0,0),(0,1),(0,2),(0,3),(0,4),(3,0),(3,1),(3,2),(3,3),(3,4),(1,2),(2,2)],
        'E': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,4),(1,2),(1,0),(2,0)],
        'V': [(0,4),(1,3),(2,2),(3,3),(4,4)],
        'D': [(0,0),(0,1),(0,2),(0,3),(0,4),(1,4),(2,3),(2,2),(2,1),(1,0)],
        ' ': [],
    }
    text_bot = "BUILT FOR THE VELD"
    arc_r2 = 69.5
    dp_b = 1.6
    dr_b = 0.55
    lw_b = 4 * dp_b
    gap_b = dp_b * 0.5
    sp_b  = dp_b * 2

    total_b = 0
    for ch in text_bot:
        total_b += sp_b if ch == ' ' else lw_b + gap_b
    total_b -= gap_b

    angle_span_b = (total_b / arc_r2) / 2
    # bottom arc: centred at 270° (−90°)
    start_angle_b = -math.pi/2 + angle_span_b
    cur_angle_b = start_angle_b

    for ch in text_bot:
        if ch == ' ':
            cur_angle_b -= sp_b / arc_r2
            continue
        ch_width_b = lw_b
        for (col, row) in font2.get(ch, []):
            lx = col * dp_b - ch_width_b/2
            ly = (4 - row) * dp_b   # flip vertically for bottom arc
            a_char = cur_angle_b - (ch_width_b/2) / arc_r2 + lx / arc_r2
            r_char = arc_r2 - 3 + ly
            px = cx + math.cos(a_char) * r_char
            py = cy + math.sin(a_char) * r_char
            add_circle(msp, (px, py), dr_b, layer="CUT")
        cur_angle_b -= (ch_width_b + gap_b) / arc_r2

    # ── mounting holes ─────────────────────────────────────────────────────────
    for angle in [45, 135, 225, 315]:
        ang = math.radians(angle)
        hx = cx + math.cos(ang) * (R_out - 8)
        hy = cy + math.sin(ang) * (R_out - 8)
        add_circle(msp, (hx, hy), 2.5, layer="CUT")

    doc.saveas(filename)
    print(f"Saved {filename}")


# ─── run all three ─────────────────────────────────────────────────────────────
design1("/home/user/veldarmour/VA_Logo_D1_Shield.dxf")
design2("/home/user/veldarmour/VA_Logo_D2_Nameplate.dxf")
design3("/home/user/veldarmour/VA_Logo_D3_CircleBadge.dxf")
print("All 3 designs generated.")
