"""Build the Veld Armour bull bar CNC data pack: cleaned DXFs + A3 bend sheets + assembly sheet."""
import os, math, json, datetime
import ezdxf
from ezdxf.enums import TextEntityAlignment
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Polygon as MplPolygon, FancyArrowPatch
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.image import imread
from shapely.geometry import Polygon, LineString, MultiLineString
from shapely.ops import unary_union, polygonize
import vageom as g

S = '/tmp/claude-0/-home-user-veldarmour/4af791c2-b675-5e47-8657-0f4afc267ab9/scratchpad'
OUT = '/home/user/veldarmour/VA_BullBar_Data_Pack'
DXF_DIR = OUT + '/dxf'
PDF_DIR = OUT + '/pdf'
for d in (OUT, DXF_DIR, PDF_DIR):
    os.makedirs(d, exist_ok=True)

K = 0.46
DENSITY = 7.93e-6  # kg/mm3 (304 stainless)
MATERIAL = '304 stainless steel (1.4301), 2B'
PRODUCT = 'VA-BB'
REV = 'A'
DATE = datetime.date.today().strftime('%Y-%m-%d')
GOLD = '#c8a84b'
INK = '#0a0a0a'
FONT = FontProperties(fname='/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf')

# ------------------------------------------------------------------ part table
# bends: list of (match, direction, angle, radius) where match is 'auto' (sorted by offset) or (mx,my) midpoint in source coords
PARTS = [
    dict(no='VA-BB-01', name='Centre panel', src='beb367d2-Flat_pattern_-_centre.DXF', t=3.0, qty=1, item=1,
         bends=[('auto', 'UP', 90.0, 2.5), ('auto', 'DOWN', 54.76, 2.5), ('auto', 'UP', 54.76, 2.5)],
         ref=(2, (120, 140, 430, 370)), ref2=(2, (620, 230, 830, 400)), logo=True,
         notes=['Veld Armour monogram cut through; wordmark on ETCH layer (mirrored in flat, reads correct on outside face).',
                'Half-round notches clear the upright lugs - check fit-up before final bend.']),
    dict(no='VA-BB-02', name='End panel (item 2)', src='ea6101d6-Flat_pattern_-_end.DXF', t=3.0, qty=1, item=2,
         bends=[((13.8, -199.8), 'DOWN', 90.0, 2.5), ((-5.0, -346.6), 'DOWN', 48.0, 2.5), ((-53.2, -426.0), 'UP', 45.0, 2.5),
                ((-57.6, -453.0), 'DOWN', 90.0, 2.5), ((-271.8, -21.0), 'DOWN', 90.0, 2.5), ((84.4, -36.6), 'DOWN', 90.0, 2.5)],
         ref=(3, (110, 80, 680, 400)), nosection=True,
         notes=['Non-parallel bends: form the short 90 deg corner flanges last, after the 48/45/90 return lip.',
                'Suggested sequence: B2 (48 deg) > B3 (45 deg up) > B4 (90 deg lip) > B1 (long 90) > B5, B6 (corner flanges).']),
    dict(no='VA-BB-03', name='Upright RH', src='d79e6554-Flat_pattern_-_Upriht.DXF', t=5.0, qty=1, item=3,
         bends=[('auto', 'DOWN', 20.0, 3.0), ('auto', 'UP', 20.0, 3.0)],
         ref=(4, (170, 60, 380, 620)), fix='upright',
         notes=['Two opposed 20 deg bends form a joggle - set back gauge from the slotted foot (datum edge A).',
                'Lug (VA-BB-07) welds over the dia 30 hole; R30 boss on this part matches lug outer radius.']),
    dict(no='VA-BB-04', name='End panel, opposite hand (item 4)', src='7f169f1e-Flat_pattern_-_end_3.DXF', t=3.0, qty=1, item=4,
         bends=[((13.8, 199.8), 'DOWN', 90.0, 2.5), ((-5.0, 346.6), 'DOWN', 48.0, 2.5), ((-53.2, 426.0), 'UP', 45.0, 2.5),
                ((-57.6, 453.0), 'DOWN', 90.0, 2.5), ((-271.8, 21.0), 'DOWN', 90.0, 2.5), ((84.4, 36.6), 'DOWN', 90.0, 2.5)],
         ref=(5, (130, 130, 700, 420)), nosection=True,
         notes=['Mirror of VA-BB-02. Same bend sequence as VA-BB-02.']),
    dict(no='VA-BB-05', name='End plate', src='f5a73ff3-Flat_pattern_-_end_plate.DXF', t=3.0, qty=2, item=5,
         bends=[('auto', 'UP', 40.84, 1.5)],
         ref=(6, (170, 170, 680, 580)),
         notes=['Single shallow bend; use a sharp-radius V-die (V = 6T = 18 mm).']),
    dict(no='VA-BB-06', name='Bracket 1 (chassis bracket)', src='3678cd2c-Flat_pattern_-_BRKT_1.DXF', t=5.0, qty=2, item=6,
         bends=[('auto', 'DOWN', 90.0, 3.0), ('auto', 'DOWN', 90.0, 3.0)],
         ref=(7, (130, 80, 530, 500)),
         notes=['U-channel: bend both legs in the same direction. Check slot alignment to chassis rail after forming.']),
    dict(no='VA-BB-07', name='Recovery lug', src=None, t=12.0, qty=4, item=7,
         bends=[], ref=(8, (170, 110, 480, 450)), lug=True,
         notes=['Redrawn from assembly drawing sheet 8 (no flat supplied in source). Dia 30 hole, R30 boss. Upgraded from 8 mm to 12 mm (Rev A).',
                'Laser cut 12 mm with nitrogen; dress the hole for a 30 mm pin / shackle bow. Weld through to the chassis bracket, not only to the 3 mm end panel.']),
    dict(no='VA-BB-11', name='Spot bracket (light mount)', src='e3a78948-Flat_pattern_-_SPOT_BRKT.DXF', t=2.0, qty=2, item=11,
         bends=[('auto', 'DOWN', 50.0, 1.25), ('auto', 'DOWN', 50.0, 1.25)],
         ref=(10, (230, 60, 430, 340)), ref2=(10, (1220, 200, 1450, 560)), fix='spot',
         notes=['Both wings bend the same way (down) to form a saddle. Dia 9 hole for M8 spot-light stud.']),
    dict(no='VA-BB-12', name='Centre panel P2 (top plate)', src='02106d2d-Flat_pattern_-_centre_P2.DXF', t=3.0, qty=1, item=12,
         bends=[('auto', 'UP', 90.0, 2.0), ('auto', 'UP', 90.0, 2.0)], rot=3,
         ref=(11, (960, 70, 1600, 470)),
         notes=['Hat/channel section with unequal legs (17.5 and 37.5 mm). Short leg first.']),
    dict(no='VA-BB-13', name='Centre panel P3 (lower channel)', src='465dbed0-Flat_pattern_-_centre_P3.DXF', t=3.0, qty=1, item=13,
         bends=[('auto', 'UP', 90.0, 2.5), ('auto', 'UP', 90.0, 2.5)],
         ref=(12, (1080, 60, 1600, 420)),
         notes=['9 x hex apertures (20 mm A/F) on the web - decorative/vent. Equal 37.5 mm legs.']),
    dict(no='VA-BB-14', name='Upright LH', src='d79e6554-Flat_pattern_-_Upriht.DXF', t=5.0, qty=1, item=14,
         bends=[('auto', 'DOWN', 20.0, 3.0), ('auto', 'UP', 20.0, 3.0)], mirror=True,
         ref=(4, (170, 60, 380, 620)), fix='upright',
         notes=['Mirror of VA-BB-03 (generated). Bend directions unchanged.']),
    dict(no='VA-BB-17', name='Face 1 (RH trim strip)', src='e31a439c-Flat_pattern_-_face_1.DXF', t=2.0, qty=1, item=17,
         bends=[('auto', 'DOWN', 90.0, 1.25), ('auto', 'DOWN', 17.0, 1.25), ('auto', 'DOWN', 162.0, 42.0)], rot=3,
         ref=(9, (380, 330, 580, 1050)),
         notes=['Bends confirmed by Veld Armour (source sheet 9 note "NO BENDING" is superseded).',
                'B3 (162 deg, R42) wraps the R42 top radius of the upright - roll/bump-form it, then fit the strip over the upright edge; B1/B2 on the brake.']),
    dict(no='VA-BB-18', name='Face 1 LH (trim strip)', src='e31a439c-Flat_pattern_-_face_1.DXF', t=2.0, qty=1, item=18,
         bends=[('auto', 'DOWN', 90.0, 1.25), ('auto', 'DOWN', 17.0, 1.25), ('auto', 'DOWN', 162.0, 42.0)], rot=3, mirror=True,
         ref=(9, (380, 330, 580, 1050)),
         notes=['Mirror of VA-BB-17 (generated). Same forming method as VA-BB-17.']),
]

# Tube schedule - measured from the 1:20 assembly drawing (front and side views, sheet 1).
# Scale derived from the 1741.09 overall dimension (7.0573 mm per drawing pt).
TUBES = [
    dict(no='VA-BB-08', name='Pipe lift (jacking stub)', qty=2, item=8, od=38.1, wall=2.0, cut=100.0,
         bends=[], spec='CHS 38.1 x 2.0', conf='approx.',
         how='Seen end-on under the centre section in the front view (Ø38 outer / Ø32 inner at 705 mm centres); length from side view.'),
    dict(no='VA-BB-09', name='Pipe centre (top hoop)', qty=1, item=9, od=63.5, wall=2.0, cut=702.0,
         bends=[], spec='CHS 63.5 x 2.0', conf='measured',
         how='Straight tube between the upright faces at the top (front view 5529.4 to 6231.4); Ø63 end-on in side view.'),
    dict(no='VA-BB-10', name='Pipe spot (light bar)', qty=1, item=10, od=38.1, wall=2.0, cut=805.0,
         bends=[], spec='CHS 38.1 x 2.0', conf='measured',
         how='Straight tube between the upright feet (front view 5477.9 to 6282.9), 38.1 wide in front view.'),
    dict(no='VA-BB-15', name='Tube 50 LH (side hoop)', qty=1, item=15, od=50.0, wall=2.0, cut=510.0,
         bends=[dict(angle=90, clr=80, legA=180, legB=204, plane=25)], spec='CHS 50 x 2.0', conf='measured',
         how='Vertical leg 180 from end-panel top to tangent; 90 deg bend, CLR 80 (105 outer / 55 inner); inboard leg 204 to end, running 25 deg rearward of lateral into the upright window.'),
    dict(no='VA-BB-16', name='Tube 50 RH (side hoop)', qty=1, item=16, od=50.0, wall=2.0, cut=510.0,
         bends=[dict(angle=90, clr=80, legA=180, legB=204, plane=25)], spec='CHS 50 x 2.0', conf='measured',
         how='Mirror of VA-BB-15.'),
]


# ------------------------------------------------------------------ fixes for source artefacts

def fix_upright(cut):
    """Remove the duplicated 1.8 mm relief strip SolidWorks left under the window cut-out."""
    out = []
    for p in cut:
        ends = []
        if p['t'] == 'LINE':
            ends = [p['a'], p['b']]
        elif p['t'] == 'ARC':
            ends = g.arc_points(p['c'], p['r'], p['s'], p['e'], 1)
        if any(abs(y - 57.297) < 0.02 and -221 < x < -111 for x, y in ends):
            continue
        out.append(p)
    return out


def envelope_fix(cut):
    """Rebuild outline as the outer envelope of all cut linework (removes zero-width relief slivers).
    Returns prims: circles kept, everything else replaced by flattened closed polylines."""
    circles = [p for p in cut if p['t'] == 'CIRCLE']
    lines = []
    for s in g.prims_to_segments([p for p in cut if p['t'] != 'CIRCLE']):
        lines.append(LineString(s))
    import shapely
    merged = shapely.set_precision(unary_union(lines), 0.001)
    faces = list(polygonize(merged))
    solid = unary_union(faces)
    if solid.geom_type == 'MultiPolygon':
        solid = max(solid.geoms, key=lambda q: q.area)
    solid = solid.simplify(0.01)
    out = []
    rings = [solid.exterior] + list(solid.interiors)
    for r in rings:
        pts = [(x, y, 0.0) for x, y in list(r.coords)[:-1]]
        out.append({'t': 'POLY', 'pts': pts, 'closed': True})
    return out + circles


def make_lug():
    """Recovery lug from sheet 8: dia 30 hole, R30 boss, tapered tab. Hole centre at origin."""
    A = (-27.3, 12.4); B = (-5.0, 61.7); C = (60.6, 13.8); D = (60.6, -14.6); E = (52.1, -14.6); F = (9.3, -28.5)
    # snap A and F exactly onto R30
    def on30(p):
        a = math.atan2(p[1], p[0]); return (30 * math.cos(a), 30 * math.sin(a))
    A = on30(A); F = on30(F)
    sa = math.degrees(math.atan2(A[1], A[0])); ea = math.degrees(math.atan2(F[1], F[0]))
    prims = [
        {'t': 'ARC', 'c': (0.0, 0.0), 'r': 30.0, 's': sa, 'e': ea % 360},
        {'t': 'LINE', 'a': A, 'b': B}, {'t': 'LINE', 'a': B, 'b': C}, {'t': 'LINE', 'a': C, 'b': D},
        {'t': 'LINE', 'a': D, 'b': E}, {'t': 'LINE', 'a': E, 'b': F},
        {'t': 'CIRCLE', 'c': (0.0, 0.0), 'r': 15.0},
    ]
    return prims


# ------------------------------------------------------------------ logo

def text_polys(txt, size, fp=FONT):
    tp = TextPath((0, 0), txt, size=size, prop=fp)
    polys = tp.to_polygons()
    return [[(float(x), float(y)) for x, y in p] for p in polys if len(p) > 2]


def va_monogram(cx, cy, mirror=True):
    """Stencil V + A monogram, ~78 x 52 mm, as closed CUT polylines, centred on (cx, cy)."""
    V = [(-39, 34), (-27, 34), (-16, 7), (-5, 34), (7, 34), (-16, -18)]
    A = [(16, 34), (39, -18), (29, -18), (16, 10), (3, -18), (-7, -18)]
    bar = [(10, -7), (22, -7), (22, -13), (10, -13)]
    shapes = [V, A, bar]
    out = []
    for sh in shapes:
        pts = [((-x if mirror else x) + cx, y + cy, 0.0) for x, y in sh]
        out.append({'t': 'POLY', 'pts': pts, 'closed': True})
    return out


def va_wordmark(cx, cy, h=7.0, mirror=True):
    polys = text_polys('VELD ARMOUR', h)
    xs = [x for p in polys for x, _ in p]
    w = max(xs) - min(xs); x0 = min(xs)
    out = []
    for p in polys:
        pts = []
        for x, y in p:
            xx = (x - x0) - w / 2
            if mirror:
                xx = -xx
            pts.append((cx + xx, cy + y, 0.0))
        out.append({'t': 'POLY', 'pts': pts, 'closed': True})
    return out


def remove_source_logo(cut):
    out = []
    for p in cut:
        x0, y0, x1, y1 = g.bbox([p])
        if -106 < x0 and x1 < -27 and -191 < y0 and y1 < -134:
            continue
        out.append(p)
    return out


# ------------------------------------------------------------------ bend line grouping

def group_bends(bend_prims):
    """Group collinear bend line segments. Returns list of dict(angle, offset, segs=[(a,b)], mid)."""
    groups = []
    for p in bend_prims:
        a, b = p['a'], p['b']
        ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
        if ang > 179.5:
            ang = 0.0
        nx, ny = -math.sin(math.radians(ang)), math.cos(math.radians(ang))
        off = a[0] * nx + a[1] * ny
        for gr in groups:
            if abs(gr['angle'] - ang) < 0.5 and abs(gr['offset'] - off) < 0.3:
                gr['segs'].append((a, b)); break
        else:
            groups.append({'angle': ang, 'offset': off, 'segs': [(a, b)], 'n': (nx, ny)})
    for gr in groups:
        pts = [q for s in gr['segs'] for q in s]
        gr['mid'] = (sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts))
        # extremes along the line direction
        dx, dy = math.cos(math.radians(gr['angle'])), math.sin(math.radians(gr['angle']))
        ts = [x * dx + y * dy for x, y in pts]
        gr['p0'] = min(zip(ts, pts))[1]; gr['p1'] = max(zip(ts, pts))[1]
    return groups


def assign_bends(groups, spec, src_bend_prims, tf):
    """Attach (direction, angle, radius) to each group. spec entries 'auto' are assigned by increasing offset
    (in transformed space); explicit midpoints are matched in source space then transformed."""
    explicit = [s for s in spec if s[0] != 'auto']
    if explicit:
        src_groups = group_bends(src_bend_prims)
        # transform src midpoints
        for s in explicit:
            best = min(src_groups, key=lambda gr: math.dist(gr['mid'], s[0]))
            tm = g.transform([{'t': 'LINE', 'a': best['mid'], 'b': best['mid']}], **tf)[0]['a']
            gr = min(groups, key=lambda gr: math.dist(gr['mid'], tm))
            gr['dir'], gr['ang'], gr['r'] = s[1], s[2], s[3]
    autos = [s for s in spec if s[0] == 'auto']
    if autos:
        order = sorted(groups, key=lambda gr: gr['offset'])
        assert len(order) == len(autos), (len(order), len(autos))
        for gr, s in zip(order, autos):
            gr['dir'], gr['ang'], gr['r'] = s[1], s[2], s[3]
    # sequence: spec order for explicit (forming order), offset order for auto
    if explicit:
        for i, s in enumerate(explicit):
            src_groups = group_bends(src_bend_prims)
            best = min(src_groups, key=lambda gr: math.dist(gr['mid'], s[0]))
            tm = g.transform([{'t': 'LINE', 'a': best['mid'], 'b': best['mid']}], **tf)[0]['a']
            gr = min(groups, key=lambda gr: math.dist(gr['mid'], tm))
            gr['seq'] = i + 1
    else:
        for i, gr in enumerate(sorted(groups, key=lambda gr: gr['offset'])):
            gr['seq'] = i + 1
    return sorted(groups, key=lambda gr: gr['seq'])


# ------------------------------------------------------------------ build one part

def build_part(P):
    tf = dict(mirror_x=P.get('mirror', False), rot90=P.get('rot', 0))
    if P.get('lug'):
        cut, bend = make_lug(), []
        src_bend = []
    else:
        cut, bend = g.read_source(P['src'])
        src_bend = list(bend)
        if P.get('fix') == 'upright':
            cut = fix_upright(cut)
        if P.get('fix') == 'spot':
            cut = envelope_fix(cut)
        if P.get('logo'):
            cut = remove_source_logo(cut)
    cut = g.transform(cut, **tf); bend = g.transform(bend, **tf)
    x0, y0, x1, y1 = g.bbox(cut)
    cut = g.transform(cut, dx=-x0, dy=-y0); bend = g.transform(bend, dx=-x0, dy=-y0)
    tf_full = dict(tf, dx=-x0, dy=-y0)
    W, H = x1 - x0, y1 - y0
    etch = []
    if P.get('logo'):
        # logo region in transformed space (source centre -66.8,-162.1) -> place monogram in top flange
        lx = -66.8 + (-x0); top = -123.0 + (-y0)
        cut += va_monogram(lx, top - 40.0, mirror=True)
        etch += va_wordmark(lx, top - 72.0, h=7.0, mirror=True)
    groups = assign_bends(group_bends(bend), P['bends'], src_bend, tf_full) if bend else []

    # ---- DXF
    doc = ezdxf.new('R2000'); doc.header['$INSUNITS'] = 4; doc.header['$MEASUREMENT'] = 1
    doc.layers.add('CUT', color=7)
    doc.layers.add('BEND_UP', color=1, linetype='CENTER')
    doc.layers.add('BEND_DOWN', color=5, linetype='CENTER')
    doc.layers.add('ETCH', color=3)
    doc.layers.add('INFO', color=8)
    for lt in ('CENTER',):
        if lt not in doc.linetypes:
            doc.linetypes.add(lt, pattern=[10.16, 6.35, -1.27, 1.27, -1.27])
    msp = doc.modelspace()
    nc, no, loops = g.chain_to_polylines(msp, cut, 'CUT')
    for gr in groups:
        layer = 'BEND_UP' if gr['dir'] == 'UP' else 'BEND_DOWN'
        for a, b in gr['segs']:
            msp.add_line(a, b, dxfattribs={'layer': layer})
        # label near midpoint
        txt = f"B{gr['seq']} {gr['dir']} {gr['ang']:g} R{gr['r']:g}"
        t = msp.add_text(txt, dxfattribs={'layer': 'INFO', 'height': 4, 'rotation': gr['angle']})
        t.set_placement((gr['mid'][0] - 2 * math.sin(math.radians(gr['angle'])),
                         gr['mid'][1] + 2 * math.cos(math.radians(gr['angle']))), align=TextEntityAlignment.BOTTOM_CENTER)
    g.add_prims(msp, etch, 'ETCH')
    info = f"{P['no']} REV {REV} | {P['name']} | {MATERIAL} {P['t']:g} mm | QTY {P['qty']} | K={K} | mm"
    msp.add_text(info, dxfattribs={'layer': 'INFO', 'height': 5}).set_placement((0, -12), align=TextEntityAlignment.LEFT)
    fn = f"{DXF_DIR}/{P['no']}_{P['name'].split(' (')[0].replace(' ', '_').replace('/', '-')}_{P['t']:g}mm.dxf"
    doc.saveas(fn)

    area, outer = g.net_area(loops)
    mass = area * P['t'] * DENSITY
    return dict(P, cut=cut, etch=etch, groups=groups, W=W, H=H, area=area, mass=mass, dxf=os.path.basename(fn),
                loops=loops, nclosed=nc, nopen=no)


# ------------------------------------------------------------------ PDF drawing helpers
A3 = (420.0, 297.0)


def mm_axes(fig, x, y, w, h):
    ax = fig.add_axes([x / A3[0], y / A3[1], w / A3[0], h / A3[1]])
    ax.set_axis_off()
    return ax


def draw_segments(ax, segs, **kw):
    for s in segs:
        xs, ys = zip(*s)
        ax.plot(xs, ys, **kw)


def dim_h(ax, x1, x2, y, txt, scale, above=True):
    ax.annotate('', xy=(x1, y), xytext=(x2, y), arrowprops=dict(arrowstyle='<|-|>', lw=0.5, color=INK, mutation_scale=6))
    ax.text((x1 + x2) / 2, y + (2 if above else -2) * scale, txt, ha='center', va='bottom' if above else 'top', fontsize=6.5, color=INK)


def dim_v(ax, y1, y2, x, txt, scale, right=True):
    ax.annotate('', xy=(x, y1), xytext=(x, y2), arrowprops=dict(arrowstyle='<|-|>', lw=0.5, color=INK, mutation_scale=6))
    ax.text(x + (2 if right else -2) * scale, (y1 + y2) / 2, txt, ha='left' if right else 'right', va='center', fontsize=6.5, color=INK, rotation=90)


def ext_line(ax, p, q):
    ax.plot([p[0], q[0]], [p[1], q[1]], lw=0.3, color='#555555')


def frame_and_titleblock(fig, part_no, title, fields, sheet='1 of 1', scale_txt='1:5'):
    # border
    bx = mm_axes(fig, 0, 0, A3[0], A3[1]); bx.set_xlim(0, A3[0]); bx.set_ylim(0, A3[1])
    bx.add_patch(Rectangle((8, 8), A3[0] - 16, A3[1] - 16, fill=False, lw=1.2, ec=INK))
    # title block
    tb_h = 38; tb_y = 8; tb_x = 8; tb_w = A3[0] - 16
    bx.add_patch(Rectangle((tb_x, tb_y), tb_w, tb_h, fill=False, lw=1.0, ec=INK))
    bx.add_patch(Rectangle((tb_x, tb_y + tb_h), tb_w, 2.2, fc=GOLD, ec='none'))
    # brand cell
    bw = 92
    bx.add_patch(Rectangle((tb_x, tb_y), bw, tb_h, fc=INK, ec=INK))
    bx.text(tb_x + bw / 2, tb_y + tb_h - 11, 'VELD ARMOUR', ha='center', va='center', fontsize=17, color=GOLD, fontproperties=FONT)
    bx.text(tb_x + bw / 2, tb_y + tb_h - 20, 'BUILT FOR THE VELD', ha='center', va='center', fontsize=6.5, color='#f5f2ed', fontproperties=FONT)
    bx.text(tb_x + bw / 2, tb_y + 7, 'CNC / PRESS-BRAKE DATA PACK', ha='center', va='center', fontsize=6, color='#c8c8c8')
    # part no cell
    px = tb_x + bw; pw = 95
    bx.plot([px, px], [tb_y, tb_y + tb_h], color=INK, lw=0.8)
    bx.text(px + 3, tb_y + tb_h - 5, 'PART NO.', fontsize=5.5, color='#666666', va='top')
    bx.text(px + 3, tb_y + tb_h - 9, part_no, fontsize=15, va='top', fontproperties=FONT, color=INK)
    bx.text(px + 3, tb_y + 11, 'TITLE', fontsize=5.5, color='#666666', va='top')
    bx.text(px + 3, tb_y + 7.5, title, fontsize=8, va='top', fontproperties=FONT, color=INK)
    # fields grid
    fx = px + pw
    bx.plot([fx, fx], [tb_y, tb_y + tb_h], color=INK, lw=0.8)
    cols = 3; rows = 4
    cw = (tb_x + tb_w - fx) / cols; rh = tb_h / rows
    for i in range(1, rows):
        bx.plot([fx, tb_x + tb_w], [tb_y + i * rh, tb_y + i * rh], color='#999999', lw=0.4)
    for j in range(1, cols):
        bx.plot([fx + j * cw, fx + j * cw], [tb_y, tb_y + tb_h], color='#999999', lw=0.4)
    for idx, (k, v) in enumerate(fields):
        c, r = idx % cols, idx // cols
        X = fx + c * cw + 2; Y = tb_y + tb_h - r * rh - 1.5
        bx.text(X, Y, k.upper(), fontsize=5, color='#666666', va='top')
        bx.text(X, Y - 3.6, v, fontsize=7, va='top', color=INK, fontproperties=FONT if r == 0 else None)
    # footer strip text
    bx.text(A3[0] - 10, 4.5, f'A3  |  SHEET {sheet}  |  SCALE {scale_txt}  |  REV {REV}  |  {DATE}  |  DO NOT SCALE DRAWING  |  ALL DIMENSIONS IN MM',
            ha='right', va='center', fontsize=5.5, color='#444444')
    bx.text(10, 4.5, 'Veld Armour (Pty) Ltd  -  proprietary; not for distribution without written consent', ha='left', va='center', fontsize=5.5, color='#444444')
    return bx


def fit_axes(ax, x0, y0, x1, y1, pad=0.08):
    w, h = x1 - x0, y1 - y0
    bb = ax.get_position(); fw, fh = bb.width * A3[0], bb.height * A3[1]
    s = max(w / fw, h / fh) * (1 + 2 * pad)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ax.set_xlim(cx - s * fw / 2, cx + s * fw / 2); ax.set_ylim(cy - s * fh / 2, cy + s * fh / 2)
    ax.set_aspect('equal')
    return s  # mm of part per mm of paper


def nice_scale(s):
    for cand in (1, 2, 2.5, 4, 5, 6, 8, 10, 12.5, 15, 20):
        if cand >= s:
            return cand
    return math.ceil(s)


def part_sheet(pdf, R, idx, total):
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    fields = [('Material', '304 SS 2B'), ('Thickness', f"{R['t']:g} mm"), ('Qty / assy', str(R['qty'])),
              ('Flat size', f"{R['W']:.1f} x {R['H']:.1f}"), ('Net mass', f"{R['mass']:.2f} kg"), ('K-factor', f'{K} (air bend, 304)'),
              ('Bends', str(len(R['groups']))), ('Source item', f"#{R['item']}"), ('DXF', R['dxf']),
              ('Tol. linear', '+/- 0.5 mm'), ('Tol. angular', '+/- 1 deg'), ('Finish', 'Deburr; brush; passivate')]
    # main flat-pattern view
    main_w, main_h = 262, 215
    ax = mm_axes(fig, 14, 56, main_w, main_h)
    s = fit_axes(ax, 0, 0, R['W'], R['H'], pad=0.16)
    scale_txt = f'1:{nice_scale(s):g}'
    bx = frame_and_titleblock(fig, R['no'], f"{R['name']}  -  FLAT PATTERN", fields, f'{idx} of {total}', scale_txt)
    draw_segments(ax, g.prims_to_segments(R['cut']), color=INK, lw=0.9)
    draw_segments(ax, g.prims_to_segments(R['etch']), color='#2a8a2a', lw=0.6)
    # bend lines + callouts
    for gr in R['groups']:
        col = '#c0392b' if gr['dir'] == 'UP' else '#1f5fbf'
        for a, b in gr['segs']:
            ax.plot([a[0], b[0]], [a[1], b[1]], color=col, lw=0.8, ls=(0, (8, 2, 1.5, 2)))
        txt = f"B{gr['seq']}  {gr['dir']} {gr['ang']:g}°  R{gr['r']:g}"
        ang = gr['angle']
        if ang > 90: ang -= 180
        ox, oy = -math.sin(math.radians(gr['angle'])) * 2.2 * s, math.cos(math.radians(gr['angle'])) * 2.2 * s
        ax.text(gr['mid'][0] + ox, gr['mid'][1] + oy, txt, rotation=ang, rotation_mode='anchor', ha='center', va='bottom', fontsize=6.5, color=col, fontproperties=FONT)
    # overall dimensions
    W, H = R['W'], R['H']
    dy = 10 * s; dx = 10 * s
    ext_line(ax, (0, H), (0, H + dy + 2 * s)); ext_line(ax, (W, H), (W, H + dy + 2 * s))
    dim_h(ax, 0, W, H + dy, f'{W:.2f}', s)
    ext_line(ax, (W, 0), (W + dx + 2 * s, 0)); ext_line(ax, (W, H), (W + dx + 2 * s, H))
    dim_v(ax, 0, H, W + dx, f'{H:.2f}', s)
    # datum marks
    ax.text(-3 * s, -3 * s, 'A', fontsize=7, fontproperties=FONT, ha='right', va='top', color=INK)
    ax.plot([0, 0], [0, -6 * s], color=INK, lw=0.6); ax.plot([0, -6 * s], [0, 0], color=INK, lw=0.6)
    # bend position dimensions (parallel bends only: horizontal or vertical)
    horiz = [gr for gr in R['groups'] if abs(gr['angle']) < 0.5 or abs(gr['angle'] - 180) < 0.5]
    vert = [gr for gr in R['groups'] if abs(gr['angle'] - 90) < 0.5]
    for i, gr in enumerate(sorted(horiz, key=lambda q: q['offset'])):
        y = gr['mid'][1]; xx = -dx * (1.0 + 0.8 * i) - 8 * s
        ext_line(ax, (0, y), (xx - 2 * s, y))
        dim_v(ax, 0, y, xx, f'{y:.2f}', s, right=False)
    for i, gr in enumerate(sorted(vert, key=lambda q: q['offset'])):
        x = gr['mid'][0]; yy = -dy * (1.0 + 0.8 * i) - 8 * s
        ext_line(ax, (x, 0), (x, yy - 2 * s))
        dim_h(ax, 0, x, yy, f'{x:.2f}', s, above=False)
    if horiz:
        ext_line(ax, (0, 0), (-dx * (1.0 + 0.8 * (len(horiz) - 1)) - 10 * s, 0))
    if vert:
        ext_line(ax, (0, 0), (0, -dy * (1.0 + 0.8 * (len(vert) - 1)) - 10 * s))
    ax.text(0.01, 0.99, f'FLAT PATTERN  -  viewed from bend-note face (UP = toward viewer)   scale {scale_txt}', transform=ax.transAxes,
            fontsize=7, va='top', fontproperties=FONT, color=INK)
    # legend
    ax.text(0.01, 0.955, 'red dash-dot = BEND UP   blue dash-dot = BEND DOWN   green = ETCH/mark   datum A = bottom-left corner of flat', transform=ax.transAxes, fontsize=5.5, va='top', color='#444444')

    # ---- right column: bend table
    rx = 284; rw = 128
    tx = mm_axes(fig, rx, 200, rw, 71); tx.set_xlim(0, rw); tx.set_ylim(0, 71)
    tx.add_patch(Rectangle((0, 0), rw, 71, fill=False, lw=0.6, ec=INK))
    tx.add_patch(Rectangle((0, 65), rw, 6, fc=INK, ec='none'))
    tx.text(2, 68, 'BEND TABLE', color=GOLD, fontsize=7.5, va='center', fontproperties=FONT)
    cols = [('No', 0), ('Dir', 9), ('Angle', 22), ('R in', 38), ('From A', 52), ('BA', 74), ('BD', 92), ('V-die', 110)]
    for k, X in cols:
        tx.text(X + 2, 61.5, k, fontsize=6, va='center', fontproperties=FONT, color=INK)
    tx.plot([0, rw], [58.5, 58.5], color=INK, lw=0.5)
    y = 54.5
    for gr in R['groups']:
        ba = g.bend_allowance(gr['ang'], gr['r'], R['t'], K)
        bd = g.bend_deduction(gr['ang'], gr['r'], R['t'], K)
        vdie = max(8 * R['t'], 8 * gr['r']) if gr['r'] < 10 else 0
        horizontal = abs(gr['angle']) < 0.5 or abs(gr['angle'] - 180) < 0.5
        vertical = abs(gr['angle'] - 90) < 0.5
        froma = f"{gr['mid'][1]:.2f} (Y)" if horizontal else (f"{gr['mid'][0]:.2f} (X)" if vertical else 'see view')
        vals = [f"B{gr['seq']}", gr['dir'], f"{gr['ang']:g}°", f"{gr['r']:g}", froma, f'{ba:.2f}', ('n/a' if math.isnan(bd) else f'{bd:.2f}'), (f'{vdie:g}' if vdie else 'roll')]
        for (k, X), v in zip(cols, vals):
            tx.text(X + 2, y, v, fontsize=6, va='center', color=INK)
        y -= 5.2
    if not R['groups']:
        tx.text(2, 54, 'No bends - flat laser-cut part.', fontsize=6.5, color=INK)
    tight = [f"B{q['seq']}" for q in R['groups'] if q['r'] < R['t']]
    warn = ('\nWARNING: ' + ', '.join(tight) + f' inside R < 1T - cracking risk in 304; use R >= {R["t"]:g} tooling or prove on first-off.') if tight else ''
    tx.text(2, 2, f'BA = bend allowance, BD = bend deduction (mm), K = {K}, inside radius as listed. V-die = 8T opening (mm).\n"From A" = bend-line centre from datum edge. 304: ~1.5x mild-steel tonnage, 2-3 deg extra springback.' + warn, fontsize=5, va='bottom', color='#b00000' if tight else '#444444')

    # ---- section sketch
    sx_y, sx_h = 120, 76
    sx = mm_axes(fig, rx, sx_y, rw, sx_h)
    sx.add_patch(Rectangle((0, 0), 1, 1, transform=sx.transAxes, fill=False, lw=0.6, ec=INK))
    sx.text(0.02, 0.96, 'FORMED SECTION (neutral axis, to scale)', transform=sx.transAxes, fontsize=6.5, va='top', fontproperties=FONT, color=INK)
    if R['groups'] and not R.get('nosection') and (len(horiz) == len(R['groups']) or len(vert) == len(R['groups'])):
        key = (lambda q: q['mid'][1]) if horiz else (lambda q: q['mid'][0])
        order = sorted(R['groups'], key=key)
        total = H if horiz else W
        positions = [0.0] + [key(q) for q in order] + [total]
        flats = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        pts = g.formed_profile(flats, [(q['dir'], q['ang'], q['r']) for q in order], R['t'], K)
        poly = g.profile_polygon(pts, R['t'])
        xs, ys = zip(*pts)
        pad = max(max(xs) - min(xs), max(ys) - min(ys)) * 0.15 + R['t'] * 2
        sx.set_xlim(min(xs) - pad, max(xs) + pad); sx.set_ylim(min(ys) - pad - 6, max(ys) + pad)
        sx.set_aspect('equal')
        if poly.geom_type == 'Polygon':
            sx.add_patch(MplPolygon(list(poly.exterior.coords), fc='#d9d9d9', ec=INK, lw=0.6))
        sx.plot(xs, ys, color='#c0392b', lw=0.4, ls='--')
        sx.plot(xs[0], ys[0], 'o', ms=3, color=INK); sx.text(xs[0], ys[0] - 4, 'A', fontsize=6, ha='center', va='top', fontproperties=FONT)
        for i, f in enumerate(flats):
            pass
        sx.text(0.02, 0.04, f'Flats from A: ' + ' / '.join(f'{f:.1f}' for f in flats) + ' mm', transform=sx.transAxes, fontsize=5.5, color='#444444')
    else:
        msg = 'Non-parallel bends - see formed view and\nassembly sheet for orientation.' if R['groups'] else 'Flat part - no section.'
        sx.text(0.5, 0.5, msg, transform=sx.transAxes, ha='center', va='center', fontsize=6.5, color='#444444')

    # ---- reference image(s)
    ix = mm_axes(fig, rx, 56, rw, 60)
    ix.add_patch(Rectangle((0, 0), 1, 1, transform=ix.transAxes, fill=False, lw=0.6, ec=INK))
    ix.text(0.02, 0.96, 'FORMED VIEW (reference, not to scale)', transform=ix.transAxes, fontsize=6.5, va='top', fontproperties=FONT, color=INK)
    imgs = [R['ref']] + ([R['ref2']] if R.get('ref2') else [])
    n = len(imgs)
    for i, (page, (a, b, c, d)) in enumerate(imgs):
        im = imread(f'{S}/pdfpng/a150-{page:02d}.png')
        crop = im[int(b * 1.5):int(d * 1.5), int(a * 1.5):int(c * 1.5)]
        sub = fig.add_axes([(rx + 3 + i * (rw - 6) / n) / A3[0], 58 / A3[1], ((rw - 6) / n - 2) / A3[0], 50 / A3[1]])
        sub.imshow(crop); sub.set_axis_off()
        if R.get('mirror'):
            sub.text(0.5, -0.02, 'opposite hand shown', transform=sub.transAxes, ha='center', va='top', fontsize=5, color='#888888')

    # ---- notes
    nx = mm_axes(fig, 14, 50, 262, 6)
    notes = ['NOTES: ' + ' '.join(f'({i + 1}) {n}' for i, n in enumerate(R['notes']))]
    nx.text(0, 0.5, notes[0], fontsize=5.6, va='center', wrap=True, color=INK)
    pdf.savefig(fig); fig.savefig(f"{PDF_DIR}/{R['no']}_bend_sheet.pdf"); plt.close(fig)


def assembly_sheet(pdf, results, idx, total):
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    sheet_mass = sum(r['mass'] * r['qty'] for r in results)
    tube_mass = sum(math.pi * (t['od'] ** 2 - (t['od'] - 2 * t['wall']) ** 2) / 4 * t['cut'] * DENSITY * t['qty'] for t in TUBES)
    fields = [('Material', '304 SS 2B'), ('Sheet parts', str(sum(r['qty'] for r in results))), ('Plate / tube mass', f'{sheet_mass:.1f} / {tube_mass:.1f} kg'),
              ('Overall width', '1741 mm'), ('Centre section', '835 mm'), ('End sections', '448 mm each'),
              ('Thicknesses', '2 / 3 / 5 / 12 mm'), ('Fitment', 'TBC (per source 4x4 design)'), ('Tube', 'CHS 50 / 63.5 / 38.1'),
              ('Welding', 'TIG/MIG, ER308L, purge'), ('Finish', 'Brushed, passivated'), ('Pack', f'{PRODUCT} rev {REV}')]
    bx = frame_and_titleblock(fig, PRODUCT + '-ASM', 'BULL BAR  -  ASSEMBLY, BOM & CUT LIST', fields, f'{idx} of {total}', '1:20')
    # assembly images
    im = imread(f'{S}/pdfpng/a150-01.png')
    ax = fig.add_axes([14 / A3[0], 150 / A3[1], 215 / A3[0], 125 / A3[1]]); ax.set_axis_off()
    ax.imshow(im[int(40 * 1.5):int(580 * 1.5), int(90 * 1.5):int(870 * 1.5)])
    ax.text(0, 1.01, 'ASSEMBLY  -  item balloons per source BOM (see table)', transform=ax.transAxes, fontsize=7, fontproperties=FONT, va='bottom')
    ax2 = fig.add_axes([14 / A3[0], 52 / A3[1], 215 / A3[0], 92 / A3[1]]); ax2.set_axis_off()
    ax2.imshow(im[int(340 * 1.5):int(560 * 1.5), int(960 * 1.5):int(1600 * 1.5)])
    ax2.text(0, 1.01, 'FRONT / SIDE  -  overall 1741 mm; centre 835 mm; ends 448 mm', transform=ax2.transAxes, fontsize=7, fontproperties=FONT, va='bottom')
    # BOM table
    tx = mm_axes(fig, 236, 52, 176, 223); tx.set_xlim(0, 176); tx.set_ylim(0, 223)
    tx.add_patch(Rectangle((0, 0), 176, 223, fill=False, lw=0.6, ec=INK))
    tx.add_patch(Rectangle((0, 217), 176, 6, fc=INK, ec='none'))
    tx.text(2, 220, 'BILL OF MATERIALS  /  CUT LIST', color=GOLD, fontsize=7.5, va='center', fontproperties=FONT)
    cols = [('Item', 0), ('VA part no.', 9), ('Description', 34), ('Thk', 96), ('Qty', 108), ('Flat (mm)', 118), ('kg ea', 158)]
    for k, X in cols:
        tx.text(X + 1.5, 213, k, fontsize=6, va='center', fontproperties=FONT)
    tx.plot([0, 176], [210.5, 210.5], color=INK, lw=0.5)
    rows = []
    for r in results:
        rows.append((r['item'], r['no'], r['name'], f"{r['t']:g}", r['qty'], f"{r['W']:.0f} x {r['H']:.0f}", f"{r['mass']:.2f}"))
    for tbe in TUBES:
        L = tbe['cut']; m = math.pi * (tbe['od'] ** 2 - (tbe['od'] - 2 * tbe['wall']) ** 2) / 4 * L * DENSITY
        rows.append((tbe['item'], tbe['no'], tbe['name'], tbe['spec'].replace('CHS ', ''), tbe['qty'], f"L = {L:.0f}" + (' (bent)' if tbe['bends'] else ''), f'{m:.2f}'))
    rows.sort(key=lambda q: q[0])
    y = 206
    for row in rows:
        for (k, X), v in zip(cols, row):
            tx.text(X + 1.5, y, str(v), fontsize=5.8, va='center', color=INK)
        y -= 5.6
    # cut list by thickness
    y -= 3
    tx.plot([0, 176], [y + 3, y + 3], color=INK, lw=0.5)
    tx.text(1.5, y, 'NEST GROUPS BY THICKNESS (laser)', fontsize=6.5, va='center', fontproperties=FONT); y -= 6
    by_t = {}
    for r in results:
        by_t.setdefault(r['t'], []).append(r)
    for t in sorted(by_t):
        parts = by_t[t]
        area = sum(p['area'] * p['qty'] for p in parts) / 1e6
        txt = f"{t:g} mm 304 SS:  " + ', '.join(f"{p['no'][-2:]} x{p['qty']}" for p in parts) + f"   |  net {area:.2f} m2  |  {sum(p['mass']*p['qty'] for p in parts):.1f} kg"
        tx.text(1.5, y, txt, fontsize=5.6, va='center'); y -= 5
    y -= 2
    tx.plot([0, 176], [y + 3, y + 3], color=INK, lw=0.5)
    tx.text(1.5, y, 'PROCESS NOTES', fontsize=6.5, va='center', fontproperties=FONT); y -= 6
    for n in ['1. Laser cut all plate 1:1 from DXF (layer CUT). Layers BEND_UP / BEND_DOWN are bend-line centres - do not cut.',
              '2. Layer ETCH = low-power surface mark (wordmark on centre panel). Layer INFO = reference text only.',
              '3. Flats are developed at K = 0.46 (air bend, 304). 304 springs back 2-3 deg more than mild steel - over-bend and check first-off against the bend table.',
              '4. Laser cut with nitrogen (oxide-free edge). Deburr; break sharp corners 0.5 mm. Stainless-only tooling, films and brushes - no carbon-steel contamination. 12 mm lugs: plasma or 6 kW+ fibre laser.',
              '5. Bend direction is viewed from the flat-pattern face shown on each sheet (UP = flange toward viewer).',
              '6. Tube items 8/9/10/15/16: cut lengths and bend data on the TUBE SCHEDULE sheet, measured from the 1:20 assembly views. Wall 2.0 mm on all tubes.',
              '7. Items 17/18 (face strips): bend as drawn (the source "NO BENDING" note is superseded). The R42 wrap matches the upright top radius.',
              '8. Weld sequence: tack brackets (06) to centre (01) and P2/P3 (12/13); fit uprights (03/14) and lugs (07); add ends (02/04) and end plates (05) last.',
              '9. Several source bend radii are below 1T (red warnings on sheets 05, 06, 11, 03/14, 17/18). Workable in 304 with a sharp-nose punch; confirm on first-off - if it cracks, open the radius.']:
        tx.text(1.5, y, n, fontsize=5.3, va='center'); y -= 4.6
    pdf.savefig(fig); fig.savefig(f'{PDF_DIR}/{PRODUCT}-ASM_assembly_sheet.pdf'); plt.close(fig)



def tube_sheet(pdf, idx, total):
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    tube_mass = sum(math.pi * (t['od'] ** 2 - (t['od'] - 2 * t['wall']) ** 2) / 4 * t['cut'] * DENSITY * t['qty'] for t in TUBES)
    fields = [('Material', '304 SS CHS'), ('Tube items', str(sum(t['qty'] for t in TUBES))), ('Tube mass', f'{tube_mass:.1f} kg'),
              ('Hoop CLR', '80 mm (1.6 D)'), ('Bend method', 'Mandrel / rotary draw'), ('Source scale', '1:20, sheet 1'),
              ('Wall', '2.0 mm all tubes'), ('Fitment', 'TBC'), ('End cuts', 'square unless noted'),
              ('Tol. length', '+/- 1 mm'), ('Tol. angle', '+/- 1 deg'), ('Finish', 'Brushed, passivated')]
    bx = frame_and_titleblock(fig, PRODUCT + '-TUBE', 'TUBE SCHEDULE  -  CUT LENGTHS & BEND DATA', fields, f'{idx} of {total}', '1:5')
    # ---- hoop drawing (true view in bend plane)
    ax = mm_axes(fig, 14, 132, 200, 132)
    legA, legB, clr, od, ang = 180.0, 204.0, 80.0, 50.0, 90.0
    # centreline: start at bottom of vertical leg (0,0) going up, bend to the right
    pts = [(0, 0), (0, legA)]
    n = 24
    for i in range(1, n + 1):
        a = math.radians(ang) * i / n
        pts.append((clr - clr * math.cos(a), legA + clr * math.sin(a)))
    ex, ey = pts[-1]
    pts.append((ex + legB, ey))
    poly = LineString(pts).buffer(od / 2, cap_style=2, join_style=1)
    s = fit_axes(ax, -70, -45, ex + legB + 60, legA + clr + 45, pad=0.05)
    ax.add_patch(MplPolygon(list(poly.exterior.coords), fc='#e3e3e3', ec=INK, lw=0.8))
    xs, ys = zip(*pts); ax.plot(xs, ys, color='#c0392b', lw=0.5, ls='--')
    # dims
    dim_v(ax, 0, legA, -od / 2 - 14 * s, f'{legA:.0f}', s, right=False)
    ext_line(ax, (-od / 2, 0), (-od / 2 - 16 * s, 0)); ext_line(ax, (-od / 2, legA), (-od / 2 - 16 * s, legA))
    dim_h(ax, ex, ex + legB, ey + od / 2 + 12 * s, f'{legB:.0f}', s)
    ext_line(ax, (ex, ey + od / 2), (ex, ey + od / 2 + 14 * s)); ext_line(ax, (ex + legB, ey + od / 2), (ex + legB, ey + od / 2 + 14 * s))
    dim_h(ax, 0, ex + legB, -od / 2 - 12 * s, f'{ex + legB:.0f} overall', s, above=False)
    ext_line(ax, (-od / 2, 0), (0, -od / 2 - 14 * s)); ext_line(ax, (ex + legB, ey - od / 2), (ex + legB, -od / 2 - 14 * s))
    dim_v(ax, 0, ey + od / 2, ex + legB + 10 * s, f'{ey + od / 2:.0f} overall', s)
    ax.plot([0, clr], [legA, legA], color='#888888', lw=0.4); ax.plot([clr, clr], [legA, legA + clr], color='#888888', lw=0.4)
    ax.text(clr + 3 * s, legA + clr / 2, f'CLR {clr:.0f}\n90°', fontsize=6.5, color=INK, fontproperties=FONT)
    ax.text(0.01, 0.99, 'VA-BB-15 / 16  SIDE HOOP  -  TRUE VIEW IN BEND PLANE   (CHS 50 x 2.0, CLR 80, 1 x 90° bend)', transform=ax.transAxes, fontsize=7, va='top', fontproperties=FONT, color=INK)
    ax.text(0.01, 0.955, f'Cut length = {legA:.0f} + {legB:.0f} + (pi/2 x {clr:.0f}) = {legA + legB + math.pi / 2 * clr:.1f} mm  ->  cut 510 (allow +10 for notch trimming at the upright).  Bend plane is rotated 25° rearward of lateral: with the vertical leg plumb, the inboard leg points toward the upright window.  LH and RH are opposite hand.', transform=ax.transAxes, fontsize=5.6, va='top', color='#444444', wrap=True)
    # ---- plan sketch of the bend-plane orientation
    px = mm_axes(fig, 220, 180, 64, 95); px.set_xlim(-10, 100); px.set_ylim(-10, 100); px.set_aspect('equal')
    px.add_patch(Rectangle((0, 0), 1, 1, transform=px.transAxes, fill=False, lw=0.6, ec=INK))
    px.text(0.03, 0.96, 'PLAN (looking down)', transform=px.transAxes, fontsize=6.5, va='top', fontproperties=FONT)
    px.annotate('', xy=(85, 0), xytext=(5, 0), arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#888888')); px.text(60, 3, 'lateral (inboard)', fontsize=5.5, color='#888888')
    px.annotate('', xy=(5, 85), xytext=(5, 5), arrowprops=dict(arrowstyle='-|>', lw=0.8, color='#888888')); px.text(7, 70, 'rearward', fontsize=5.5, color='#888888', rotation=90)
    L = 75; px.plot([5, 5 + L * math.cos(math.radians(25))], [5, 5 + L * math.sin(math.radians(25))], color=INK, lw=3, solid_capstyle='round')
    px.plot(5, 5, 'o', ms=6, color=INK); px.text(5, -6, 'vertical leg', fontsize=5.5, ha='center')
    px.text(45, 30, '25°', fontsize=7, fontproperties=FONT)
    px.text(0.03, 0.06, 'inboard leg direction\n(front view: 362 lateral, side view: 85 rearward)', transform=px.transAxes, fontsize=5, color='#444444')
    # ---- table
    rx, rw = 290, 122
    tx = mm_axes(fig, rx, 120, rw, 155); tx.set_xlim(0, rw); tx.set_ylim(0, 155)
    tx.add_patch(Rectangle((0, 0), rw, 155, fill=False, lw=0.6, ec=INK))
    tx.add_patch(Rectangle((0, 149), rw, 6, fc=INK, ec='none'))
    tx.text(2, 152, 'TUBE SCHEDULE', color=GOLD, fontsize=7.5, va='center', fontproperties=FONT)
    y = 144
    for t in TUBES:
        m = math.pi * (t['od'] ** 2 - (t['od'] - 2 * t['wall']) ** 2) / 4 * t['cut'] * DENSITY
        tx.text(2, y, f"{t['no']}   {t['name']}   x{t['qty']}", fontsize=6.5, va='center', fontproperties=FONT); y -= 4.6
        tx.text(2, y, f"{t['spec']}   cut length {t['cut']:.0f} mm   {m:.2f} kg ea   [{t['conf']}]", fontsize=6, va='center'); y -= 4.2
        for b in t['bends']:
            tx.text(2, y, f"  bend {b['angle']}°, CLR {b['clr']}, legs {b['legA']} / {b['legB']} (tangent to end), bend plane {b['plane']}° rearward", fontsize=5.6, va='center'); y -= 4.2
        tx.text(2, y, t['how'], fontsize=5, va='center', color='#444444', wrap=True); y -= 8.5
        tx.plot([0, rw], [y + 3, y + 3], color='#bbbbbb', lw=0.4)
    tx.text(2, 3, 'Measured from source assembly views at 1:20 (scale set from the 1741.09 dim). Wall 2.0 mm on all tubes per Veld Armour. Verify first-off on the jig.', fontsize=5, va='bottom', color='#b00000')
    # ---- source views
    for i, (nm, lab) in enumerate([('front', 'SOURCE FRONT VIEW (measured)'), ('side', 'SOURCE SIDE VIEW (measured)')]):
        im = imread(f'{S}/png/z_{nm}.png')
        w = 190 if i == 0 else 90
        x0 = 14 if i == 0 else 214
        sub = fig.add_axes([x0 / A3[0], 52 / A3[1], w / A3[0], 62 / A3[1]]); sub.imshow(im); sub.set_axis_off()
        sub.text(0, 1.02, lab, transform=sub.transAxes, fontsize=6.5, va='bottom', fontproperties=FONT)
    nx = mm_axes(fig, 310, 52, 102, 62); nx.add_patch(Rectangle((0, 0), 1, 1, transform=nx.transAxes, fill=False, lw=0.6, ec=INK))
    nx.text(0.03, 0.95, 'HOW THE LENGTHS WERE TAKEN', transform=nx.transAxes, fontsize=6.5, va='top', fontproperties=FONT)
    nx.text(0.03, 0.85, 'Vector geometry extracted from the assembly PDF; the 1741.09 overall width fixes the scale. Hoop: vertical-leg tangent and horizontal-leg tangent found from the tube silhouettes in both views; CLR = 80 from the tangent offsets (72 lateral, 33 rearward, 80 vertical). Inboard leg true length from its two projections (184 lateral / 85 rearward). Centre and spot tubes span between the upright faces/feet. Lift stubs: Ø38/Ø32 circles under the bar, length from the side view.', transform=nx.transAxes, fontsize=5, va='top', color='#444444', wrap=True)
    pdf.savefig(fig); fig.savefig(f'{PDF_DIR}/{PRODUCT}-TUBE_tube_schedule.pdf'); plt.close(fig)

# ------------------------------------------------------------------ main
if __name__ == '__main__':
    results = []
    for P in PARTS:
        R = build_part(P)
        results.append(R)
        print(f"{R['no']} {R['name'][:30]:30s} {R['W']:7.1f} x {R['H']:7.1f}  area {R['area']:8.0f}  mass {R['mass']:.2f} kg  loops closed={R['nclosed']} open={R['nopen']}  bends={[(q['seq'],q['dir'],q['ang'],q['r']) for q in R['groups']]}")
    total = len(results) + 1
    total += 1
    with PdfPages(f'{OUT}/{PRODUCT}_Bull_Bar_Bending_Pack.pdf') as pdf:
        assembly_sheet(pdf, results, 1, total)
        tube_sheet(pdf, 2, total)
        for i, R in enumerate(results):
            part_sheet(pdf, R, i + 3, total)
    with open(f'{OUT}/parts_index.json', 'w') as f:
        json.dump([{k: R[k] for k in ('no', 'name', 't', 'qty', 'item', 'W', 'H', 'area', 'mass', 'dxf')} |
                   {'bends': [{'seq': q['seq'], 'dir': q['dir'], 'angle': q['ang'], 'r_in': q['r']} for q in R['groups']]}
                   for R in results] + [{k: t[k] for k in ('no', 'name', 'qty', 'item', 'od', 'wall', 'cut', 'bends', 'spec', 'conf')} for t in TUBES], f, indent=1)
    print('done')
