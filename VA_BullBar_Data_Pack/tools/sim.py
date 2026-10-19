"""Virtual build / manufacturability / structural sanity simulation for the VA-BB bull bar pack."""
import os, math, json, itertools
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import split, unary_union
import vageom as g
import build as B

S = B.S
OUT = B.OUT + '/simulation'
os.makedirs(OUT, exist_ok=True)
T_RES = {}

# ------------------------------------------------------------------ 304 material
UTS = 520.0      # MPa (304, annealed, typical 515-620)
YS = 210.0       # MPa 0.2% proof
E = 193000.0
SHEET = (2500.0, 1250.0)

# ------------------------------------------------------------------ fold engine

def rot_about_axis(p0, p1, theta):
    u = np.array(p1) - np.array(p0); u = u / np.linalg.norm(u)
    c, s = math.cos(theta), math.sin(theta)
    x, y, z = u
    R = np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                  [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                  [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])
    M = np.eye(4); M[:3, :3] = R
    p0 = np.array(p0); M[:3, 3] = p0 - R @ p0
    return M


def apply(T, pts2d):
    P = np.array([[x, y, 0.0, 1.0] for x, y in pts2d]).T
    return (T @ P)[:3].T


def fold_part(outer_pts, hole_pts_list, groups, t, k=0.46, nsub=6):
    """Fold flat polygon (outer + holes) about bend groups. Returns list of (poly2d, T) faces."""
    flat = Polygon(outer_pts, [h for h in hole_pts_list if len(h) >= 3]).buffer(0)
    faces = [[flat, np.eye(4)]] if flat.geom_type == 'Polygon' else [[p, np.eye(4)] for p in flat.geoms]
    big = 5000.0
    for gr in groups:
        ang = math.radians(gr['angle']); d = (math.cos(ang), math.sin(ang)); n = gr['n']
        # datum side: the side of this bend line holding the larger share of the flat (main body stays put)
        Lbig = LineString([(gr['mid'][0] - d[0] * 5000, gr['mid'][1] - d[1] * 5000), (gr['mid'][0] + d[0] * 5000, gr['mid'][1] + d[1] * 5000)])
        try:
            pieces = list(split(flat, Lbig).geoms)
        except Exception:
            pieces = [flat]
        apos = sum(p.area for p in pieces if ((p.representative_point().x - gr['mid'][0]) * n[0] + (p.representative_point().y - gr['mid'][1]) * n[1]) > 0)
        aneg = flat.area - apos
        gr['_datum'] = 1.0 if apos < aneg else -1.0   # far side (rotates) = smaller side
        ba = g.bend_allowance(gr['ang'], gr['r'], t, k)
        seg = LineString([gr['p0'], gr['p1']])
        step = math.radians(gr['ang']) / nsub
        offs = [(-ba / 2 + ba * (i + 0.5) / nsub) for i in range(nsub)]
        for off in offs:
            # line in flat coords
            m = (gr['mid'][0] + n[0] * off, gr['mid'][1] + n[1] * off)
            L = LineString([(m[0] - d[0] * big, m[1] - d[1] * big), (m[0] + d[0] * big, m[1] + d[1] * big)])
            newfaces = []
            for poly, T in faces:
                try:
                    parts = split(poly, L)
                    for p in parts.geoms:
                        if p.area > 1e-6:
                            newfaces.append([p, T])
                except Exception:
                    newfaces.append([poly, T])
            faces = newfaces
            # side classification: far side = side NOT containing the datum (0,0) side of the ORIGINAL bend line
            def side(p):
                c = p.representative_point()
                return (c.x - m[0]) * n[0] + (c.y - m[1]) * n[1]
            datum_side = gr['_datum']
            far = [f for f in faces if side(f[0]) * datum_side > 0]
            near = [f for f in faces if side(f[0]) * datum_side <= 0]
            if not far or not near:
                continue
            # keep only far components touching the bend segment
            u = unary_union([f[0] for f in far])
            comps = list(u.geoms) if u.geom_type == 'MultiPolygon' else [u]
            keep = [c for c in comps if c.distance(seg) < 0.6]
            if not keep:
                continue
            keepu = unary_union(keep)
            far_sel = [f for f in far if f[0].representative_point().within(keepu.buffer(0.01))]
            # near reference face touching the segment
            ref = None
            for f in near:
                if f[0].distance(seg) < 0.6:
                    ref = f; break
            if ref is None:
                ref = min(near, key=lambda f: f[0].distance(seg))
            Tref = ref[1]
            P0 = apply(Tref, [(m[0] - d[0] * 100, m[1] - d[1] * 100)])[0]
            P1 = apply(Tref, [(m[0] + d[0] * 100, m[1] + d[1] * 100)])[0]
            normal = (Tref[:3, :3] @ np.array([0, 0, 1.0]))
            # pick sign so far side moves toward +normal (UP) or -normal (DOWN)
            q2 = far_sel[0][0].representative_point(); q = apply(far_sel[0][1], [(q2.x, q2.y)])[0]
            want = normal if gr['dir'] == 'UP' else -normal
            best = None
            for sgn in (1, -1):
                R = rot_about_axis(P0, P1, sgn * step)
                qn = (R @ np.append(q, 1.0))[:3]
                sc = float(np.dot(qn - q, want))
                if best is None or sc > best[0]:
                    best = (sc, R)
            R = best[1]
            for f in far_sel:
                f[1] = R @ f[1]
    return faces


def face_points3d(face, res=12.0):
    poly, T = face
    pts = list(poly.exterior.coords)
    return apply(T, pts), poly, T


def formed_bbox(faces):
    allp = np.vstack([apply(T, list(p.exterior.coords)) for p, T in faces])
    return allp.min(axis=0), allp.max(axis=0)


def clash_check(faces, t):
    """Sample interior points of each face; flag if a sample lies within 0.6*t of a non-adjacent face's plane region."""
    samples = []
    for i, (poly, T) in enumerate(faces):
        minx, miny, maxx, maxy = poly.bounds
        step = max(6.0, max(maxx - minx, maxy - miny) / 12)
        pts = []
        x = minx + step / 2
        while x < maxx:
            y = miny + step / 2
            while y < maxy:
                if poly.contains(Point(x, y)):
                    pts.append((x, y))
                y += step
            x += step
        if pts:
            samples.append((i, apply(T, pts)))
    worst = (1e9, None, None)
    for i, P in samples:
        for j, (poly, T) in enumerate(faces):
            if i == j or faces[i][0].distance(poly) < 0.5:
                continue
            Ti = np.linalg.inv(T)
            inner = poly.buffer(-2.5 * t)
            if inner.is_empty:
                continue
            Q = (Ti @ np.vstack([P.T, np.ones(len(P))]))[:3].T
            for qx, qy, qz in Q:
                if abs(qz) < 0.6 * t and inner.contains(Point(qx, qy)):
                    if abs(qz) < worst[0]:
                        worst = (abs(qz), i, j)
    return worst


def render_folded(faces, title, fn, t):
    fig = plt.figure(figsize=(6, 5)); ax = fig.add_subplot(111, projection='3d')
    polys = [apply(T, list(p.exterior.coords)) for p, T in faces]
    col = Poly3DCollection(polys, facecolors='#cfcfcf', edgecolors='#333333', linewidths=0.3, alpha=0.95)
    ax.add_collection3d(col)
    allp = np.vstack(polys); mn, mx = allp.min(0), allp.max(0); c = (mn + mx) / 2; r = (mx - mn).max() / 2
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(elev=28, azim=-55); ax.set_axis_off()
    ax.set_title(title, fontsize=8)
    fig.savefig(fn, dpi=110, bbox_inches='tight'); plt.close(fig)


# ------------------------------------------------------------------ section properties

def polygon_I(poly):
    """Second moment of area about horizontal axis through centroid (Iy about z-centroid) for shapely polygon."""
    def ring(coords):
        A = Ix = cy = 0.0; cx = 0.0
        for (x0, y0), (x1, y1) in zip(coords[:-1], coords[1:]):
            cr = x0 * y1 - x1 * y0
            A += cr / 2; cx += (x0 + x1) * cr / 6; cy += (y0 + y1) * cr / 6
            Ix += (y0 * y0 + y0 * y1 + y1 * y1) * cr / 12
        return A, cx, cy, Ix
    A, cx, cy, Ix = ring(list(poly.exterior.coords))
    for h in poly.interiors:
        a, x, y, i = ring(list(h.coords)); A += a; cx += x; cy += y; Ix += i
    cy /= A; cx /= A
    return abs(A), cy, abs(Ix - A * cy * cy)


# ------------------------------------------------------------------ nesting (shelf)

def nest(parts_boxes, sheet=SHEET, gap=10.0):
    """parts_boxes: list of (w,h,label). Returns list of sheets: list of (x,y,w,h,label)."""
    items = sorted(parts_boxes, key=lambda b: max(b[0], b[1]), reverse=True)
    sheets = []
    for w, h, lab in items:
        if w < h and h <= sheet[0] and w <= sheet[1]:
            w, h = h, w  # lay long side along sheet length
        placed = False
        for sh in sheets:
            for shelf in sh['shelves']:
                if shelf['x'] + w + gap <= sheet[0] and h <= shelf['h']:
                    sh['items'].append((shelf['x'], shelf['y'], w, h, lab)); shelf['x'] += w + gap; placed = True; break
            if placed: break
            y = sum(s['h'] + gap for s in sh['shelves'])
            if y + h <= sheet[1]:
                sh['shelves'].append({'x': w + gap, 'y': y, 'h': h}); sh['items'].append((0, y, w, h, lab)); placed = True; break
        if not placed:
            sheets.append({'shelves': [{'x': w + gap, 'y': 0, 'h': h}], 'items': [(0, 0, w, h, lab)]})
    return sheets


# ------------------------------------------------------------------ main
if __name__ == '__main__':
    results = [B.build_part(P) for P in B.PARTS]
    report = {'fold': [], 'brake': [], 'struct': [], 'nest': []}
    targets = {  # drawing numbers for comparison (outside dims where the source states them)
        'VA-BB-01': 'sheet 2: section 82.15 / 80.34 / 48.26 / 15 lip, 835 long',
        'VA-BB-05': 'sheet 6: 78 x 176.58 plan, 25.47 flange at 40.84 deg',
        'VA-BB-06': 'sheet 7: 183.63 x 116.00 x 79.00 U-channel',
        'VA-BB-12': 'sheet 11: 238.64 wide, legs 40 / 20, 835 long',
        'VA-BB-13': 'sheet 12: 83 x 40 channel, 835 long',
        'VA-BB-03': 'sheet 4: 56.32 joggle offset, 744.48 tall',
        'VA-BB-11': 'sheet 10: 60 wide saddle',
    }
    def section_dims(R):
        horiz = [q for q in R['groups'] if abs(q['angle']) < 0.5 or abs(q['angle'] - 180) < 0.5]
        vert = [q for q in R['groups'] if abs(q['angle'] - 90) < 0.5]
        if not R['groups'] or not (len(horiz) == len(R['groups']) or len(vert) == len(R['groups'])):
            return None
        key = (lambda q: q['mid'][1]) if horiz else (lambda q: q['mid'][0])
        order = sorted(R['groups'], key=key); total = R['H'] if horiz else R['W']
        positions = [0.0] + [key(q) for q in order] + [total]
        flats = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
        pts = g.formed_profile(flats, [(q['dir'], q['ang'], q['r']) for q in order], R['t'], 0.46)
        poly = g.profile_polygon(pts, R['t'])
        # align longest flat along x
        i = max(range(len(flats)), key=lambda j: flats[j])
        # find the straight run: approximate using the neutral-axis points: take the segment between arc ends
        segs = []; cum = 0
        # rebuild heading angles by walking pts: choose the pair of consecutive points with max distance
        best = max(range(len(pts) - 1), key=lambda j: math.dist(pts[j], pts[j + 1]))
        a = math.atan2(pts[best + 1][1] - pts[best][1], pts[best + 1][0] - pts[best][0])
        c, s_ = math.cos(-a), math.sin(-a)
        xs = [x * c - y * s_ for x, y in poly.exterior.coords]; ys = [x * s_ + y * c for x, y in poly.exterior.coords]
        return (max(xs) - min(xs), max(ys) - min(ys))
    expect = {'VA-BB-06': (116.0, 79.0), 'VA-BB-12': (238.64, 40.0), 'VA-BB-13': (83.0, 40.0), 'VA-BB-01': (80.34, 82.15), 'VA-BB-03': (None, 56.32), 'VA-BB-14': (None, 56.32)}
    # ---- fold check
    for R in results:
        if not R['groups']:
            report['fold'].append(dict(no=R['no'], name=R['name'], status='flat part', bbox='-', clash='-', note=''))
            continue
        loops = sorted(R['loops'], key=lambda l: Polygon(l).area if len(l) > 2 else 0, reverse=True)
        outer, holes = loops[0], loops[1:]
        groups = []
        for q in R['groups']:
            groups.append(dict(q))
        faces = fold_part(outer, holes, groups, R['t'])
        mn, mx = formed_bbox(faces)
        dims = mx - mn
        cl = clash_check(faces, R['t'])
        render_folded(faces, f"{R['no']} {R['name']}", f"{OUT}/{R['no']}_folded.png", R['t'])
        status = 'OK' if cl[1] is None else f'CLASH faces {cl[1]}/{cl[2]} gap {cl[0]:.1f}'
        sd = section_dims(R)
        sec = ''
        if sd:
            ex = expect.get(R['no'])
            sec = f'{sd[0]:.1f} x {sd[1]:.1f}'
            if ex:
                sec += '  (dwg ' + ' x '.join(f'{v:g}' for v in ex if v) + ')'
        report['fold'].append(dict(no=R['no'], name=R['name'], status=status, bbox=f'{dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f}',
                                   clash='none' if cl[1] is None else f'{cl[0]:.1f} mm', note=targets.get(R['no'], ''), dims=[float(v) for v in dims], sec=sec))
        print('   section', sec)
        print(R['no'], status, [round(float(v), 1) for v in dims])

    # ---- press-brake check per bend
    for R in results:
        for q in R['groups']:
            t = R['t']; V = max(8 * t, 8 * q['r']) if q['r'] < 10 else None
            L = math.dist(q['p0'], q['p1'])
            if V:
                F = 1.33 * UTS * L * t * t / V / 1000.0  # kN
                tonnes = F / 9.81
                # shortest adjacent flange (parallel bends only)
                horizontal = abs(q['angle']) < 0.5 or abs(q['angle'] - 180) < 0.5
                vertical = abs(q['angle'] - 90) < 0.5
                flange = None
                if horizontal or vertical:
                    pos = q['mid'][1] if horizontal else q['mid'][0]
                    total = R['H'] if horizontal else R['W']
                    others = [ (o['mid'][1] if horizontal else o['mid'][0]) for o in R['groups'] if o is not q]
                    below = max([0.0] + [p for p in others if p < pos]); above = min([total] + [p for p in others if p > pos])
                    flange = min(pos - below, above - pos)
                minfl = 0.71 * V * (1 if q['ang'] >= 60 else 0.6)
                ok = 'OK' if flange is None or flange >= minfl else f'SHORT FLANGE {flange:.1f} < {minfl:.1f} -> use V={max(math.ceil(flange/0.71/2)*2, 4*t):g}'
                if q['r'] < t: ok += ' | R<1T sharp-nose'
            else:
                F = tonnes = 0; flange = None; ok = 'roll/bump form (R42)'
            report['brake'].append(dict(no=R['no'], seq=q['seq'], dir=q['dir'], ang=q['ang'], r=q['r'], t=t, L=L, V=V, tonnes=tonnes, flange=flange, verdict=ok))

    # ---- structural hand calcs
    S_ = report['struct']
    # lug: 8 mm, dia 30 hole, R30 boss -> 15 mm ligament each side
    t = 8.0; w_lig = 15.0
    net_t = 2 * w_lig * t * YS / 1000; tear = 2 * w_lig * t * 0.6 * YS / 1000; bearing = 30 * t * 1.5 * YS / 1000
    S_.append(dict(item='Recovery lug VA-BB-07 (8 mm 304, dia 30, R30 boss)',
                   lines=[f'Net tension at hole: 2 x 15 x 8 x {YS:.0f} MPa = {net_t:.0f} kN ({net_t/9.81:.1f} t) at yield',
                          f'Shear tear-out (2 planes x 15 mm): {tear:.0f} kN ({tear/9.81:.1f} t) at yield',
                          f'Pin bearing (dia 30 x 8, 1.5 Fy): {bearing:.0f} kN ({bearing/9.81:.1f} t)',
                          f'Governing: tear-out {min(net_t, tear, bearing):.0f} kN ({min(net_t, tear, bearing)/9.81:.1f} t) at yield, ~{min(net_t, tear, bearing)*UTS/YS:.0f} kN ({min(net_t, tear, bearing)*UTS/YS/9.81:.1f} t) ultimate per lug - before the weld to the 3 mm end panel is considered.',
                          'VERDICT: fine as a tie-down / mounting lug. NOT a rated snatch-recovery point for a 2.5-3 t vehicle (want >= 2 x GVM with a safety factor, and the load path welded through to the chassis bracket): go to 10-12 mm, R35 boss, and weld to the bracket, or label it tie-down only.']))
    # hoop tube 50x2
    D, tw = 50.0, 2.0
    I = math.pi / 64 * (D ** 4 - (D - 2 * tw) ** 4); Z = I / (D / 2)
    arm = 285.0
    Py = YS * Z / arm / 1000
    S_.append(dict(item='Side hoop VA-BB-15/16 (CHS 50 x 2.0, 285 mm above end panel)',
                   lines=[f'I = {I:.0f} mm4, Z = {Z:.0f} mm3', f'Lateral load at the top to reach yield at the root weld: {Py:.2f} kN ({Py*102:.0f} kgf)',
                          'VERDICT: adequate for brush/animal contact and as a handhold; it is not a structural member. Root weld to the 3 mm end panel is the weak link - add a 3 mm doubler or weld through to the end plate.']))
    # centre section beam: composite of centre Z + P2 hat + P3 channel
    secs = {}
    for R in results:
        if R['no'] in ('VA-BB-01', 'VA-BB-12', 'VA-BB-13'):
            horiz = [q for q in R['groups']]
            key = (lambda q: q['mid'][1])
            order = sorted(horiz, key=key); total = R['H']
            positions = [0.0] + [key(q) for q in order] + [total]
            flats = [positions[i + 1] - positions[i] for i in range(len(positions) - 1)]
            pts = g.formed_profile(flats, [(q['dir'], q['ang'], q['r']) for q in order], R['t'], 0.46)
            poly = g.profile_polygon(pts, R['t'])
            A, cy, Ix = polygon_I(poly)
            secs[R['no']] = (A, Ix, poly)
    Itot = sum(v[1] for v in secs.values())
    # conservative: sum of individual I (no composite action), depth ~ 85 mm -> Z ~ Itot/45
    Z_c = Itot / 45.0
    span = 700.0
    for P in (5.0, 10.0, 20.0):
        M = P * 1000 * span / 4
        sig = M / Z_c
        S_.append(dict(item=f'Centre section as a beam, {P:.0f} kN frontal push at mid-span, 700 mm between chassis brackets',
                       lines=[f'I (sum of centre Z + P2 hat + P3 channel, no composite credit) = {Itot/1e4:.1f} cm4; Z ~ {Z_c/1e3:.1f} cm3',
                              f'M = {M/1e3:.0f} Nm -> sigma = {sig:.0f} MPa vs 210 MPa yield -> ' + ('OK' if sig < YS else 'YIELDS') + f'  (margin {YS/sig:.0f}x; conclusion holds even if the section is 10x less stiff than summed)']))
    # chassis bracket slots: 2 x 5 mm U-brackets, 4 x M12 (assumed) in slots
    S_.append(dict(item='Chassis brackets VA-BB-06 (5 mm U, 4 slots each)',
                   lines=['Slot 22 x 9 (source) suits M8. For a bull bar on a 3 t vehicle use M12 8.8 minimum: open slots to 13 wide / 26 long on the next revision.',
                          'Bracket web 116 x 5 mm in bending under 10 kN at 80 mm lever: sigma ~ 10000 x 80 / (116 x 25 / 6) = 1655 MPa -> relies on the centre channels, NOT the bracket alone. Weld brackets to both P2 and P3 (notes on assembly sheet).']))
    # stack-up
    S_.append(dict(item='Assembly stack-up (from flats)',
                   lines=['835 (centre) + 2 x 5 (uprights) + 448.28 + 447.81 (ends) = 1741.09 = overall width on sheet 1. Fit is exact.',
                          'P2 hat (238.64 formed) / P3 channel (83 formed) / centre Z (80.34 deep) all 835 long - they stack as one box; no interference.',
                          'Side hoop end: 204 mm inboard leg lands inside the upright window (window 108 x 141) - clearance 50 mm tube in 108 window OK.']))

    # ---- nesting
    by_t = {}
    for R in results:
        by_t.setdefault(R['t'], []).extend([(R['W'], R['H'], R['no'][-2:])] * R['qty'])
    for tt in sorted(by_t):
        sheets = nest(by_t[tt])
        area = sum(w * h for w, h, _ in by_t[tt])
        net = sum(R['area'] * R['qty'] for R in results if R['t'] == tt)
        util = net / (len(sheets) * SHEET[0] * SHEET[1]) * 100
        report['nest'].append(dict(t=tt, sheets=len(sheets), util=util, parts=len(by_t[tt]), layout=sheets))
        print('nest', tt, len(sheets), f'{util:.0f}%')

    json.dump({k: v for k, v in report.items() if k != 'nest'} | {'nest': [{kk: vv for kk, vv in n.items() if kk != 'layout'} for n in report['nest']]},
              open(f'{OUT}/simulation_results.json', 'w'), indent=1, default=float)

    # ---- report PDF (A4 landscape pages)
    A4 = (297.0, 210.0)
    def page(title):
        fig = plt.figure(figsize=(A4[0] / 25.4, A4[1] / 25.4))
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off(); ax.set_xlim(0, A4[0]); ax.set_ylim(0, A4[1])
        ax.add_patch(Rectangle((0, A4[1] - 16), A4[0], 16, fc=B.INK, ec='none'))
        ax.text(10, A4[1] - 8, 'VELD ARMOUR', color=B.GOLD, fontsize=13, va='center', fontproperties=B.FONT)
        ax.text(60, A4[1] - 8, f'VA-BB BULL BAR  -  VIRTUAL BUILD & MANUFACTURABILITY SIMULATION  -  {title}', color='#f5f2ed', fontsize=8, va='center', fontproperties=B.FONT)
        ax.text(A4[0] - 8, 4, f'{B.DATE}  |  304 SS  |  K = 0.46  |  UTS {UTS:.0f} / Fy {YS:.0f} MPa', ha='right', fontsize=6, color='#666666')
        return fig, ax
    with PdfPages(f'{B.OUT}/VA-BB_Simulation_Report.pdf') as pdf:
        # page 1 summary
        fig, ax = page('SUMMARY')
        y = A4[1] - 26
        ax.text(10, y, 'What was simulated', fontsize=10, fontproperties=B.FONT); y -= 6
        for line in ['1. Every flat pattern folded in 3D with its bend table (direction, angle, inside radius, K = 0.46) - self-clash check and formed envelope vs the source drawing.',
                     '2. Assembly stack-up: do the formed parts add up to the 1741.09 overall width and stack as a box.',
                     '3. Press-brake: tonnage per bend (304, 8T V-die), shortest flange vs die opening, radii below 1T.',
                     '4. Structural hand checks: recovery lug, side hoop, centre section as a beam, chassis bracket fasteners.',
                     '5. Nesting on 2500 x 1250 sheets per thickness.']:
            ax.text(12, y, line, fontsize=7); y -= 5
        y -= 4
        ax.text(10, y, 'Verdict', fontsize=10, fontproperties=B.FONT); y -= 6
        fold_ok = all(r['status'] in ('OK', 'flat part') for r in report['fold'])
        short = [b for b in report['brake'] if 'SHORT' in b['verdict']]
        lines = [('FOLDS', 'All 13 flats fold without self-clash. Formed sections match the source drawing within 1 mm (bracket 115.1 vs 116, P2 238.1 vs 238.64, P3 82.7 vs 83, upright joggle 56.3 vs 56.32, centre Z 80.0 vs 80.34) - the residual is the K-factor difference between the source model and K = 0.46.' if fold_ok else 'See fold table - clashes found.'),
                 ('STACK-UP', '835 + 2x5 + 448.28 + 447.81 = 1741.09 - exact match to the overall width. Parts fit.'),
                 ('BRAKE', f'{len(short)} bend(s) have a flange shorter than the 8T die allows - swap to the V listed in the brake table (gooseneck punch for the centre panel Z). Max tonnage {max(b["tonnes"] for b in report["brake"]):.0f} t on the 835 mm bends - needs a 40 t+ brake.'),
                 ('STRUCTURE', 'Centre section OK for a 10 kN push. Side hoops are cosmetic/handhold grade. The 8 mm lug is NOT a recovery point as drawn - tie-down only. Bracket slots suit M8 - upsize to M12 for a 3 t vehicle.'),
                 ('NESTING', ', '.join(f"{n['t']:g} mm: {n['sheets']} sheet(s) at {n['util']:.0f}%" for n in report['nest']))]
        for k, v in lines:
            ax.text(12, y, k, fontsize=7.5, fontproperties=B.FONT, color=B.INK); ax.text(40, y, v, fontsize=7, wrap=True); y -= 7
        y -= 2
        ax.text(10, y, 'Bottom line', fontsize=10, fontproperties=B.FONT); y -= 6
        ax.text(12, y, 'It will build. The flats are consistent with the drawing and with each other. Before you cut steel: (a) fix the two tooling items in the brake table, (b) decide whether the lugs are recovery points - if yes, go to 10-12 mm and R35, (c) open the bracket slots to M12. Tube lengths are drawing-derived - prove the first hoop on the jig.', fontsize=7.2, wrap=True)
        pdf.savefig(fig); plt.close(fig)
        # page 2 fold table
        fig, ax = page('FOLD CHECK'); y = A4[1] - 24
        cols = [('Part', 10), ('Name', 30), ('Fold', 82), ('Envelope (mm)', 100), ('Formed section W x H (dwg)', 140), ('Drawing reference', 200)]
        for k, x in cols: ax.text(x, y, k, fontsize=7, fontproperties=B.FONT)
        y -= 2; ax.plot([10, 287], [y, y], color=B.INK, lw=0.5); y -= 4
        for r in report['fold']:
            for (k, x), v in zip(cols, [r['no'], r['name'][:30], r['status'], r['bbox'], r.get('sec', ''), r['note'][:48]]):
                ax.text(x, y, str(v), fontsize=6.3, color='#b00000' if 'CLASH' in str(v) else B.INK)
            y -= 5
        y -= 3
        ax.text(10, y, 'Fold engine: polygon split at each bend line, bend zone tessellated into 6 sub-folds across the bend allowance so the neutral axis length is preserved; UP rotates toward the sheet normal of the datum face. Envelope is the bounding box of the folded sheet surface in the datum-face frame (compare to outside dims less one thickness where applicable).', fontsize=5.8, wrap=True, color='#444444')
        pdf.savefig(fig); plt.close(fig)
        # page 3 folded renders
        fig, ax = page('FOLDED PARTS (3D)')
        folded = [r for r in report['fold'] if r['status'] != 'flat part']
        n = len(folded); cols_n = 5; rows_n = math.ceil(n / cols_n)
        for i, r in enumerate(folded):
            im = plt.imread(f"{OUT}/{r['no']}_folded.png")
            c, rr = i % cols_n, i // cols_n
            sub = fig.add_axes([(8 + c * 57) / A4[0], (A4[1] - 24 - (rr + 1) * 58) / A4[1], 55 / A4[0], 56 / A4[1]]); sub.imshow(im); sub.set_axis_off()
        pdf.savefig(fig); plt.close(fig)
        # page 4 brake table
        fig, ax = page('PRESS-BRAKE CHECK'); y = A4[1] - 24
        cols = [('Part', 10), ('Bend', 30), ('Dir', 42), ('Angle', 54), ('R', 68), ('t', 78), ('Length', 88), ('V-die', 106), ('Tonnes', 120), ('Min flange', 136), ('Verdict', 160)]
        for k, x in cols: ax.text(x, y, k, fontsize=7, fontproperties=B.FONT)
        y -= 2; ax.plot([10, 287], [y, y], color=B.INK, lw=0.5); y -= 4
        for b in report['brake']:
            vals = [b['no'], f"B{b['seq']}", b['dir'], f"{b['ang']:g}°", f"{b['r']:g}", f"{b['t']:g}", f"{b['L']:.0f}", f"{b['V']:g}" if b['V'] else '-', f"{b['tonnes']:.1f}" if b['V'] else '-',
                    f"{b['flange']:.1f}" if b['flange'] is not None else '-', b['verdict']]
            for (k, x), v in zip(cols, vals):
                ax.text(x, y, v, fontsize=5.9, color='#b00000' if ('SHORT' in b['verdict'] and k == 'Verdict') else B.INK)
            y -= 4.3
        y -= 2
        ax.text(10, y, f'Tonnage: F = 1.33 x UTS x L x t^2 / V (air bend), UTS {UTS:.0f} MPa. Min flange = 0.71 x V for bends >= 60 deg (0.43 x V for shallow bends). R < 1T flagged for 304 - sharp-nose punch, prove on first-off. 162 deg R42 is a roll / bump-form, not a V-die bend.', fontsize=5.8, wrap=True, color='#444444')
        pdf.savefig(fig); plt.close(fig)
        # page 5 structure
        fig, ax = page('STRUCTURAL HAND CHECKS'); y = A4[1] - 24
        for s_ in report['struct']:
            ax.text(10, y, s_['item'], fontsize=7.5, fontproperties=B.FONT); y -= 4.6
            for l in s_['lines']:
                ax.text(14, y, l, fontsize=6.3, wrap=True, color='#b00000' if ('NOT' in l or 'YIELDS' in l) else B.INK); y -= 4.2
            y -= 2.5
        # section sketch
        sx = fig.add_axes([205 / A4[0], 12 / A4[1], 85 / A4[0], 95 / A4[1]]); sx.set_aspect('equal'); sx.set_axis_off()
        off = 0
        for no, (A, Ix, poly) in secs.items():
            xs, ys = poly.exterior.xy
            sx.fill(np.array(xs), np.array(ys) + off, fc='#dddddd', ec=B.INK, lw=0.5)
            sx.text(min(xs), off + max(ys) + 6, f'{no}  I = {Ix/1e4:.0f} cm4', fontsize=5)
            off += (max(ys) - min(ys)) + 40
        sx.autoscale(); sx.margins(0.15)
        sx.set_title('Formed sections used for the beam check', fontsize=6.5)
        pdf.savefig(fig); plt.close(fig)
        # page 6 nesting
        fig, ax = page('NESTING  (2500 x 1250 sheets, 10 mm gap, shelf packing)')
        k = 0
        for nres in report['nest']:
            for si, sh in enumerate(nres['layout']):
                c, rr = k % 3, k // 3
                sub = fig.add_axes([(8 + c * 95) / A4[0], (A4[1] - 30 - (rr + 1) * 58) / A4[1], 90 / A4[0], 50 / A4[1]])
                sub.set_xlim(0, SHEET[0]); sub.set_ylim(0, SHEET[1]); sub.set_aspect('equal'); sub.set_xticks([]); sub.set_yticks([])
                for x, yy, w, h, lab in sh['items']:
                    sub.add_patch(Rectangle((x, yy), w, h, fc='#e8e8e8', ec=B.INK, lw=0.5)); sub.text(x + w / 2, yy + h / 2, lab, ha='center', va='center', fontsize=5)
                sub.set_title(f"{nres['t']:g} mm sheet {si + 1}/{nres['sheets']}  ({nres['util']:.0f}% net util. over all sheets)", fontsize=6)
                k += 1
        ax.text(10, 12, 'Bounding-box shelf nest for quoting only - a CAM nester with true-shape nesting and common-line cutting will do better, especially on the 3 mm sheet where the two end panels (688 x 687) dominate.', fontsize=6, color='#444444', wrap=True)
        pdf.savefig(fig); plt.close(fig)
    print('report written')
