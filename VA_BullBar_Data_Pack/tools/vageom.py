"""Geometry helpers for the Veld Armour bull bar data pack build."""
import math, copy
import ezdxf
from ezdxf import edgeminer as em, edgesmith as es
from ezdxf.math import Vec2
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

GAP = 0.05
SRC = '/tmp/claude-0/-home-user-veldarmour/4af791c2-b675-5e47-8657-0f4afc267ab9/scratchpad/src/'

# ---------------------------------------------------------------- primitives
# Internal representation: list of dicts
#  {'t':'LINE','a':(x,y),'b':(x,y)}
#  {'t':'ARC','c':(x,y),'r':r,'s':deg,'e':deg}   (CCW from s to e)
#  {'t':'CIRCLE','c':(x,y),'r':r}
#  {'t':'POLY','pts':[(x,y,bulge),...],'closed':bool}

def read_source(fname):
    doc = ezdxf.readfile(SRC + fname)
    msp = doc.modelspace()
    cut, bend = [], []
    for e in msp:
        isbend = e.dxf.linetype == 'CENTERX2'
        t = e.dxftype()
        if t == 'LINE':
            p = {'t': 'LINE', 'a': (e.dxf.start.x, e.dxf.start.y), 'b': (e.dxf.end.x, e.dxf.end.y)}
        elif t == 'ARC':
            p = {'t': 'ARC', 'c': (e.dxf.center.x, e.dxf.center.y), 'r': e.dxf.radius,
                 's': e.dxf.start_angle, 'e': e.dxf.end_angle}
        elif t == 'CIRCLE':
            p = {'t': 'CIRCLE', 'c': (e.dxf.center.x, e.dxf.center.y), 'r': e.dxf.radius}
        elif t == 'LWPOLYLINE':
            p = {'t': 'POLY', 'pts': [(x, y, b) for x, y, b in e.get_points('xyb')], 'closed': e.closed}
        else:
            continue
        (bend if isbend else cut).append(p)
    return cut, bend


def transform(prims, dx=0.0, dy=0.0, mirror_x=False, rot90=0):
    """Apply (optional) mirror about Y axis, then rotation by rot90*90 deg CCW, then translation."""
    out = []
    def pt(x, y):
        if mirror_x:
            x = -x
        for _ in range(rot90 % 4):
            x, y = -y, x
        return (x + dx, y + dy)
    def ang(a):
        if mirror_x:
            a = 180.0 - a
        a += 90.0 * (rot90 % 4)
        return a % 360.0
    for p in prims:
        q = copy.deepcopy(p)
        if p['t'] == 'LINE':
            q['a'] = pt(*p['a']); q['b'] = pt(*p['b'])
        elif p['t'] == 'ARC':
            q['c'] = pt(*p['c'])
            s, e = ang(p['s']), ang(p['e'])
            if mirror_x:
                s, e = e, s
            q['s'], q['e'] = s, e
        elif p['t'] == 'CIRCLE':
            q['c'] = pt(*p['c'])
        elif p['t'] == 'POLY':
            pts = [(pt(x, y), (-b if mirror_x else b)) for x, y, b in p['pts']]
            q['pts'] = [(x, y, b) for (x, y), b in pts]
        out.append(q)
    return out


def arc_points(c, r, s, e, n=None):
    s %= 360.0; e %= 360.0
    span = (e - s) % 360.0
    if span == 0:
        span = 360.0
    if n is None:
        n = max(4, int(span / 4) + 1)
    return [(c[0] + r * math.cos(math.radians(s + span * i / n)),
             c[1] + r * math.sin(math.radians(s + span * i / n))) for i in range(n + 1)]


def poly_points(pts, closed):
    """Flatten a bulge polyline to points."""
    out = []
    n = len(pts)
    rng = range(n if closed else n - 1)
    for i in rng:
        x1, y1, b = pts[i]
        x2, y2, _ = pts[(i + 1) % n]
        out.append((x1, y1))
        if abs(b) > 1e-9:
            # bulge arc
            theta = 4 * math.atan(b)
            d = math.hypot(x2 - x1, y2 - y1)
            r = d / (2 * math.sin(abs(theta) / 2))
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            h = math.sqrt(max(r * r - (d / 2) ** 2, 0)) * (1 if b > 0 else -1)
            nx, ny = -(y2 - y1) / d, (x2 - x1) / d
            cx, cy = mx + nx * h * (1 if theta > 0 else 1), my + ny * h
            # sign handling: for b>0 CCW arc centre is to the left of chord
            if b < 0:
                cx, cy = mx - nx * abs(h), my - ny * abs(h)
            else:
                cx, cy = mx + nx * abs(h), my + ny * abs(h)
            a1 = math.atan2(y1 - cy, x1 - cx); a2 = math.atan2(y2 - cy, x2 - cx)
            k = max(3, int(abs(math.degrees(theta)) / 4) + 1)
            for j in range(1, k):
                t = j / k
                a = a1 + theta * t
                out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    if not closed:
        out.append(pts[-1][:2])
    return out


def prims_to_segments(prims):
    """Flatten all prims to polylines (list of point lists) for plotting."""
    segs = []
    for p in prims:
        if p['t'] == 'LINE':
            segs.append([p['a'], p['b']])
        elif p['t'] == 'ARC':
            segs.append(arc_points(p['c'], p['r'], p['s'], p['e']))
        elif p['t'] == 'CIRCLE':
            segs.append(arc_points(p['c'], p['r'], 0, 360, 48))
        elif p['t'] == 'POLY':
            pts = poly_points(p['pts'], p['closed'])
            if p['closed']:
                pts = pts + [pts[0]]
            segs.append(pts)
    return segs


def bbox(prims):
    xs, ys = [], []
    for s in prims_to_segments(prims):
        for x, y in s:
            xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


# ---------------------------------------------------------------- DXF writing

def add_prims(msp, prims, layer):
    for p in prims:
        if p['t'] == 'LINE':
            msp.add_line(p['a'], p['b'], dxfattribs={'layer': layer})
        elif p['t'] == 'ARC':
            msp.add_arc(p['c'], p['r'], p['s'], p['e'], dxfattribs={'layer': layer})
        elif p['t'] == 'CIRCLE':
            msp.add_circle(p['c'], p['r'], dxfattribs={'layer': layer})
        elif p['t'] == 'POLY':
            msp.add_lwpolyline(p['pts'], format='xyb', close=p['closed'], dxfattribs={'layer': layer})


def chain_to_polylines(msp, prims, layer):
    """Write prims as closed LWPOLYLINEs where loops can be chained; circles stay circles.
    Returns (n_closed, n_open, loops_as_point_lists)."""
    circles = [p for p in prims if p['t'] == 'CIRCLE']
    polys = [p for p in prims if p['t'] == 'POLY' and p['closed']]
    others = [p for p in prims if p['t'] not in ('CIRCLE',) and not (p['t'] == 'POLY' and p['closed'])]
    tmp = ezdxf.new('R2000'); tmsp = tmp.modelspace()
    add_prims(tmsp, others, '0')
    ents = list(tmsp)
    edges = list(es.edges_from_entities_2d(ents, gap_tol=GAP))
    chains = []
    if edges:
        dep = em.Deposit(edges, gap_tol=GAP)
        chains = em.find_all_simple_chains(dep)
    n_closed = n_open = 0
    loops = []
    for ch in chains:
        if em.is_loop(ch, gap_tol=GAP):
            pl = es.lwpolyline_from_chain(ch, dxfattribs={'layer': layer})
            pl.closed = True
            msp.add_entity(pl)
            n_closed += 1
            loops.append([(v.x, v.y) for v in ezdxf.path.make_path(pl).flattening(0.1)])
        else:
            # keep open chain as polyline (should not happen on good data)
            pl = es.lwpolyline_from_chain(ch, dxfattribs={'layer': layer})
            msp.add_entity(pl)
            n_open += 1
    for p in polys:
        msp.add_lwpolyline(p['pts'], format='xyb', close=True, dxfattribs={'layer': layer})
        loops.append(poly_points(p['pts'], True))
    for p in circles:
        msp.add_circle(p['c'], p['r'], dxfattribs={'layer': layer})
        loops.append(arc_points(p['c'], p['r'], 0, 360, 64))
    return n_closed, n_open, loops


def net_area(loops):
    """Outer loop = largest area; all others are holes. Returns (net_area_mm2, outer_polygon)."""
    pgs = [Polygon(l) for l in loops if len(l) >= 3]
    pgs = [pg.buffer(0) for pg in pgs if pg.is_valid or True]
    pgs.sort(key=lambda pg: pg.area, reverse=True)
    outer = pgs[0]
    holes = unary_union(pgs[1:]) if len(pgs) > 1 else None
    net = outer.difference(holes) if holes is not None else outer
    return net.area, outer


# ---------------------------------------------------------------- bending maths

def bend_allowance(angle_deg, r_in, t, k=0.44):
    return math.radians(angle_deg) * (r_in + k * t)


def outside_setback(angle_deg, r_in, t):
    # tangent length from bend line to apex of outside mould lines
    return (r_in + t) * math.tan(math.radians(angle_deg) / 2) if angle_deg < 180 else float('inf')


def bend_deduction(angle_deg, r_in, t, k=0.44):
    if angle_deg >= 180:
        return float('nan')
    return 2 * outside_setback(angle_deg, r_in, t) - bend_allowance(angle_deg, r_in, t, k)


def formed_profile(flat_lengths, bends, t, k=0.44):
    """Build a 2D formed section (neutral axis) for parallel bends.
    flat_lengths: list of n+1 distances between bend lines along the section direction.
    bends: list of n (direction, angle, r_in).  direction 'UP' => +z (CCW).
    Returns list of point lists (polyline of neutral axis) as a single flattened polyline."""
    pts = [(0.0, 0.0)]
    heading = 0.0  # radians
    x, y = 0.0, 0.0
    for i, L in enumerate(flat_lengths):
        # straight portion: subtract half bend allowance on each side
        s = L
        if i > 0:
            s -= bend_allowance(bends[i - 1][1], bends[i - 1][2], t, k) / 2
        if i < len(bends):
            s -= bend_allowance(bends[i][1], bends[i][2], t, k) / 2
        s = max(s, 0.0)
        x += s * math.cos(heading); y += s * math.sin(heading)
        pts.append((x, y))
        if i < len(bends):
            d, a, r = bends[i]
            sign = 1 if d.upper() == 'UP' else -1
            rn = r + k * t
            # arc of radius rn turning by a (deg) with sign
            ang = math.radians(a)
            n = max(4, int(a / 5))
            cx = x - sign * rn * math.sin(heading); cy = y + sign * rn * math.cos(heading)
            for j in range(1, n + 1):
                h = heading + sign * ang * j / n
                px = cx + sign * rn * math.sin(h); py = cy - sign * rn * math.cos(h)
                pts.append((px, py))
            x, y = pts[-1]
            heading += sign * ang
    return pts


def profile_polygon(pts, t):
    return LineString(pts).buffer(t / 2, cap_style=2, join_style=1)
