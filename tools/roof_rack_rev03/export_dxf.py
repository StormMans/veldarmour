"""DXF export: one file per part (1:1 mm, R2010) + one nested sheet file.
Layers: CUT (white, continuous)  BEND (yellow, DASHED, bend lines + labels)  ROLL (cyan, corner roll zones)
        NOTES (green, text; not for cutting)"""
import math, os
import ezdxf
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import Polygon, MultiPolygon
import rack_design as D
import parts as P

def new_doc():
    doc = ezdxf.new('R2010', setup=True)
    doc.header['$INSUNITS'] = 4          # mm
    doc.header['$MEASUREMENT'] = 1
    doc.layers.add('CUT', color=7)
    doc.layers.add('BEND', color=2, linetype='DASHED')
    doc.layers.add('ROLL', color=4, linetype='CENTER')
    doc.layers.add('NOTES', color=3)
    return doc

def add_ring(msp, coords, dx, dy):
    pts = [(x + dx, y + dy) for x, y in coords]
    if pts[0] == pts[-1]: pts = pts[:-1]
    msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'CUT'})

def add_obround(msp, o, dx, dy):
    r = o['W'] / 2; h = o['L'] / 2 - r
    a = math.radians(o['angle']); ca, sa = math.cos(a), math.sin(a)
    def tr(x, y): return (o['cx'] + dx + x * ca - y * sa, o['cy'] + dy + x * sa + y * ca)
    # 4 vertices with bulge=1 on the arc segments (semi-circles)
    pts = [(*tr(h, -r), 1.0), (*tr(h, r), 0.0), (*tr(-h, r), 1.0), (*tr(-h, -r), 0.0)]
    msp.add_lwpolyline(pts, format='xyb', close=True, dxfattribs={'layer': 'CUT'})

def add_part(msp, part, dx=0.0, dy=0.0, with_notes=True):
    geom = part['outer']
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    for poly in polys:
        poly = poly.simplify(0.005)
        add_ring(msp, list(poly.exterior.coords), dx, dy)
        for ring in poly.interiors:
            add_ring(msp, list(ring.coords), dx, dy)
    for o in part['inner']:
        if o['kind'] == 'obround': add_obround(msp, o, dx, dy)
        else: msp.add_circle((o['cx'] + dx, o['cy'] + dy), o['dia'] / 2, dxfattribs={'layer': 'CUT'})
    for (x0, y0), (x1, y1), lab in part['bend_lines']:
        msp.add_line((x0 + dx, y0 + dy), (x1 + dx, y1 + dy), dxfattribs={'layer': 'BEND'})
        msp.add_text(lab, height=4, dxfattribs={'layer': 'BEND'}).set_placement((x0 + dx + 25, y0 + dy + 1.2))
    for s0, s1 in part['corner_marks']:
        W = part['flat'][1]
        for s in (s0, s1):
            msp.add_line((s + dx, dy - 5), (s + dx, W + dy + 5), dxfattribs={'layer': 'ROLL'})
        msp.add_text("ROLL WEB IN-PLANE TO OUTSIDE R%.0f (90°)" % D.CORNER_R, height=4,
                     dxfattribs={'layer': 'ROLL'}).set_placement(((s0 + s1) / 2 + dx, dy - 12), align=TextEntityAlignment.CENTER)
    if with_notes:
        bx = geom.bounds
        msp.add_text("%s  %s  qty %d  304 2B  t=%.1f" % (part['no'], part['title'], part['qty'], D.T), height=6,
                     dxfattribs={'layer': 'NOTES'}).set_placement((bx[0] + dx, bx[3] + dy + 6))

def export_all(outdir):
    os.makedirs(outdir, exist_ok=True)
    parts = P.all_parts()
    files = []
    for part in parts:
        doc = new_doc(); msp = doc.modelspace()
        b = part['outer'].bounds
        add_part(msp, part, -b[0], -b[1])
        fn = os.path.join(outdir, "%s_%s_FLAT.dxf" % (part['no'], part['title'].replace(' ', '_').replace('(', '').replace(')', '')))
        doc.saveas(fn); files.append(fn)
    # nest on 2500 x 1250 sheet (all qty)
    doc = new_doc(); msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (2500, 0), (2500, 1250), (0, 1250)], close=True, dxfattribs={'layer': 'NOTES'})
    msp.add_text("SHEET 2500 x 1250 x 1.5  304 2B  - nest reference only (re-nest to your machine)", height=10,
                 dxfattribs={'layer': 'NOTES'}).set_placement((10, 1260))
    gap = 12; y = 15
    def place(part, x, y):
        b = part['outer'].bounds
        add_part(msp, part, x - b[0], y - b[1], with_notes=True)
        return b[2] - b[0], b[3] - b[1]
    for part in parts[:2]:
        w, h = place(part, 15, y); y += h + gap + 8
    crosses = [parts[2]] * 5 + [parts[3]] * 2
    x = 15; rowh = 0
    for i, part in enumerate(crosses):
        w, h = part['outer'].bounds[2] - part['outer'].bounds[0], part['outer'].bounds[3] - part['outer'].bounds[1]
        if x + w > 2490: x = 15; y += rowh + gap + 8; rowh = 0
        place(part, x, y); x += w + gap; rowh = max(rowh, h)
    y += rowh + gap + 8; x = 15
    for part, n in ((parts[4], 2), (parts[5], 2), (parts[6], 4)):
        for i in range(n):
            w, h = part['outer'].bounds[2] - part['outer'].bounds[0], part['outer'].bounds[3] - part['outer'].bounds[1]
            if x + w > 2490: x = 15; y += 70
            place(part, x, y); x += w + gap
    fn = os.path.join(outdir, "RRD-2000-%s_NEST_2500x1250.dxf" % P.REV)
    doc.saveas(fn); files.append(fn)
    return files

if __name__ == '__main__':
    import sys
    for f in export_all(sys.argv[1]): print(f)
