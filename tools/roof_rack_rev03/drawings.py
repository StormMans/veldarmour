"""A3 landscape drawing sheets (matplotlib) : per-part bending sheets + assembly sheet."""
import math, os, datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle, Circle, FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import MultiPolygon
import rack_design as D
import parts as P

A3 = (420, 297)
TODAY = datetime.date.today().isoformat()
LC = '#111111'

def sheet():
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, A3[0]); ax.set_ylim(0, A3[1]); ax.axis('off')
    ax.add_patch(Rectangle((10, 10), 400, 277, fill=False, lw=1.2, ec=LC))
    return fig, ax

def title_block(ax, no, title, scale, qty, sheet_no=1, sheets=1, material="304 (1.4301) 2B", thick=D.T, finish="Brush / passivate after weld",
                mass=None):
    x0, y0, w, h = 225, 10, 185, 48
    ax.add_patch(Rectangle((x0, y0), w, h, fill=False, lw=1.0, ec=LC))
    for yy in (y0 + 12, y0 + 24, y0 + 36): ax.plot([x0, x0 + w], [yy, yy], color=LC, lw=0.6)
    for xx in (x0 + 60, x0 + 120): ax.plot([xx, xx], [y0, y0 + 36], color=LC, lw=0.6)
    ax.plot([x0 + 120, x0 + 120], [y0 + 36, y0 + 48], color=LC, lw=0.6)
    def cell(x, y, label, val, fs=7.5):
        ax.text(x + 1.5, y + 10.2, label, fontsize=4.5, va='top', color='#555')
        ax.text(x + 1.5, y + 1.8, val, fontsize=fs, va='bottom', color=LC, weight='bold' if fs > 8 else None)
    cell(x0, y0 + 36, "COMPANY", "VELD ARMOUR  -  Hilux GD6 DC canopy roof rack", 8)
    cell(x0 + 120, y0 + 36, "DWG NO.", no, 9.5)
    cell(x0, y0 + 24, "TITLE", title, 9)
    cell(x0 + 60, y0 + 24, "MATERIAL", material)
    cell(x0 + 120, y0 + 24, "THICKNESS", "%.1f mm" % thick)
    cell(x0, y0 + 12, "QTY / ASSY", str(qty))
    cell(x0 + 60, y0 + 12, "FINISH", finish)
    cell(x0 + 120, y0 + 12, "MASS (each)", "%.2f kg" % mass if mass else "-")
    cell(x0, y0, "SCALE", scale)
    cell(x0 + 60, y0, "DATE / REV", "%s   %s" % (TODAY, P.REV))
    cell(x0 + 120, y0, "SHEET", "%d of %d   A3" % (sheet_no, sheets))
    ax.text(12, 12, "Unless otherwise stated: dimensions in mm. Linear ±0.5, bend angle ±1°, flat pattern per K=%.2f, inside R%.1f. "
            "Deburr and break sharp edges. Do not scale drawing." % (D.K, D.R_IN), fontsize=5, color='#444')

def draw_flat(ax, part, ox, oy, s, show_labels=True):
    """draw the flat pattern scaled by s with origin at (ox,oy) sheet mm"""
    geom = part['outer']; b = geom.bounds
    polys = list(geom.geoms) if isinstance(geom, MultiPolygon) else [geom]
    def T(x, y): return (ox + (x - b[0]) * s, oy + (y - b[1]) * s)
    for poly in polys:
        ax.add_patch(MPoly([T(x, y) for x, y in poly.exterior.coords], closed=True, fill=False, lw=0.9, ec=LC))
    for o in part['inner']:
        if o['kind'] == 'obround':
            pp = P.obround_poly(o, 10)
            ax.add_patch(MPoly([T(x, y) for x, y in pp.exterior.coords], closed=True, fill=False, lw=0.6, ec=LC))
        else:
            cx, cy = T(o['cx'], o['cy']); ax.add_patch(Circle((cx, cy), o['dia'] / 2 * s, fill=False, lw=0.6, ec=LC))
    for (x0, y0), (x1, y1), lab in part['bend_lines']:
        p0, p1 = T(x0, y0), T(x1, y1)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#c08000', lw=0.7, ls=(0, (6, 2, 1, 2)))
    for s0, s1 in part['corner_marks']:
        for sx in (s0, s1):
            p0, p1 = T(sx, b[1] - 6 / s), T(sx, b[3] + 6 / s)
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#0077aa', lw=0.6, ls='--')
        x0, y0 = T(s0, b[1]); x1, y1 = T(s1, b[3])
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=True, fc='#0077aa', alpha=0.08, ec='none'))
    return T

def dim_h(ax, x0, x1, y, text, off=0, fs=6, color=LC):
    ax.annotate('', xy=(x0, y), xytext=(x1, y), arrowprops=dict(arrowstyle='<->', lw=0.6, color=color, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2, y + 1.2 + off, text, fontsize=fs, ha='center', va='bottom', color=color)

def dim_v(ax, x, y0, y1, text, fs=6, color=LC, side=1):
    ax.annotate('', xy=(x, y0), xytext=(x, y1), arrowprops=dict(arrowstyle='<->', lw=0.6, color=color, shrinkA=0, shrinkB=0))
    ax.text(x + 1.2 * side, (y0 + y1) / 2, text, fontsize=fs, ha='left' if side > 0 else 'right', va='center', color=color, rotation=90)

def profile_path(dims, angle=90.0, direction=-1):
    """outside-dim profile as centreline points for a chain of 90 deg bends, returns list of (x,y)."""
    pts = [(0.0, 0.0)]; ang = 0.0
    for i, d in enumerate(dims):
        x, y = pts[-1]
        pts.append((x + d * math.cos(math.radians(ang)), y + d * math.sin(math.radians(ang))))
        ang += direction * angle
    return pts

def draw_profile(ax, part, cx, cy, s):
    """formed cross-section view from part['profile'] centreline segments; draw with thickness."""
    segs = part['profile']
    xs = [p[0] for sg in segs for p in sg]; ys = [p[1] for sg in segs for p in sg]
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    def T(x, y): return (cx + (x - mx) * s, cy + (y - my) * s)
    for (x0, y0), (x1, y1) in segs:
        p0, p1 = T(x0, y0), T(x1, y1)
        ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=LC, lw=D.T * s * 2.83, solid_capstyle='butt')
    return T, (min(xs), max(xs), min(ys), max(ys))

def part_sheet(pdf, part, idx, n, mass):
    import textwrap
    fig, ax = sheet()
    L, W = part['flat']; b = part['outer'].bounds
    fl, fw = b[2] - b[0], b[3] - b[1]
    # ---- flat pattern view (top band)
    avail_w, avail_h = 345, 80
    s = min(avail_w / fl, avail_h / max(fw, 1), 1.0)
    ox, oy = 50, 185
    T = draw_flat(ax, part, ox, oy, s)
    ax.text(ox, oy + fw * s + 16, "FLAT PATTERN  (viewed from OUTSIDE / top face - all bends DOWN)  scale %s" %
            ("1:%.0f" % (1 / s) if s < 0.999 else "1:1"), fontsize=7, weight='bold')
    dim_h(ax, ox, ox + fl * s, oy - 7, "%.1f" % fl, fs=6.5)
    dim_v(ax, ox + fl * s + 5, oy, oy + fw * s, "%.1f" % fw, fs=6.5)
    if part['bend_lines']:
        for i, ((x0, y0), (x1, y1), lab) in enumerate(part['bend_lines']):
            yy = oy + (y0 - b[1]) * s
            ax.plot([ox - 2, ox - 8], [yy, yy], color='#c08000', lw=0.4)
            ax.text(ox - 9, yy, "%.2f" % (y0 - b[1]), fontsize=5, ha='right', va='center', color='#c08000')
            ax.text(ox + fl * s / 2, yy + 0.8, lab, fontsize=5.5, ha='center', va='bottom', color='#c08000', weight='bold')
        ax.text(ox - 9, oy - 1, "datum\nedge", fontsize=4.5, ha='right', va='top', color='#c08000')
    # ---- bend table (bottom left)
    bx, by = 20, 160
    ax.text(bx, by, "BEND TABLE", fontsize=7, weight='bold')
    rows = [("No.", "Pos. from datum edge", "Angle", "Dir.", "Inside R", "Formed (outside)")]
    if part['bend_lines']:
        for i, ((x0, y0), _, lab) in enumerate(part['bend_lines']):
            rows.append((str(i + 1), "%.2f" % (y0 - b[1]), lab.split()[1], lab.split()[0], lab.split()[2],
                         part['profile_dims'][i][0] + " %.0f" % part['profile_dims'][i][1]))
        rows.append(("", "edge %.2f" % fw, "", "", "", part['profile_dims'][-1][0] + " %.0f" % part['profile_dims'][-1][1]))
    else:
        rows.append(("-", "no bends - flat part", "", "", "", ""))
    for r, row in enumerate(rows):
        for c, txt in enumerate(row):
            ax.text(bx + [0, 10, 50, 64, 80, 100][c], by - 6 - r * 5.2, txt, fontsize=5.5, weight='bold' if r == 0 else None)
    yk = by - 8 - len(rows) * 5.2
    ax.text(bx, yk, "K-factor %.2f, BA(90°)=%.2f, BD(90°)=%.2f.  Adjust flat to your tooling if your BD differs." % (D.K, D.BA90, D.BD90), fontsize=5, color='#444')
    ax.text(bx, yk - 6, "Bend sequence: 1 then %s (long bends first, lip/return last). Check first-off against FORMED SECTION." %
            (", ".join(str(i + 2) for i in range(len(part['bend_lines']) - 1)) if len(part['bend_lines']) > 1 else "-"), fontsize=5, color='#444')
    # ---- formed section (bottom middle, above title block)
    if part['profile']:
        xs_ = [p[0] for sg in part['profile'] for p in sg]; ys_ = [p[1] for sg in part['profile'] for p in sg]
        hgt = max(ys_) - min(ys_) + D.T; wdt = max(xs_) - min(xs_) + D.T
        ps = min(1.2, 75 / hgt, 90 / wdt)
        T2, ext = draw_profile(ax, part, 175, 110, ps)
        ax.text(175, 110 + hgt / 2 * ps + 9, "FORMED SECTION  (scale %s)" % ("1:1" if abs(ps - 1) < 0.01 else "%.1f:1" % ps), fontsize=7, weight='bold', ha='center')
        x0, y0 = T2(ext[0], ext[2]); x1, y1 = T2(ext[1], ext[3])
        dim_h(ax, x0 - D.T / 2 * ps, x1 + D.T / 2 * ps, y0 - D.T / 2 * ps - 7, "%.0f" % wdt)
        dim_v(ax, x1 + D.T / 2 * ps + 8, y0 - D.T / 2 * ps, y1 + D.T / 2 * ps, "%.0f" % hgt)
        ax.text(175, y0 - 14, "  |  ".join("%s %.0f" % (nn, v) for nn, v in part['profile_dims']) + "   (outside dims)", fontsize=5.5, ha='center')
    # ---- notes (bottom right)
    nx, ny = 240, 160
    ax.text(nx, ny, "NOTES", fontsize=7, weight='bold')
    lines = []
    allnotes = part['notes'] + ["Material: 304 stainless 2B, %.1f mm. Laser cut from DXF '%s_FLAT.dxf' (1:1, mm), layer CUT only; BEND/ROLL/NOTES layers are reference." %
                                (D.T, part['no'] + "_" + part['title'].replace(' ', '_').replace('(', '').replace(')', ''))]
    for i, note in enumerate(allnotes):
        wrapped = textwrap.wrap("%d. %s" % (i + 1, note), 78)
        lines += wrapped
    for j, ln in enumerate(lines):
        ax.text(nx, ny - 6 - j * 4.2, ln, fontsize=5.0)
    title_block(ax, part['no'], part['title'], "1:%.0f" % (1 / s) if s < 0.999 else "1:1", part['qty'], idx, n, mass=mass)
    pdf.savefig(fig); plt.close(fig)

# ------------------------------------------------------------------ assembly sheet
def assembly_sheet(pdf, idx, n, total_mass):
    fig, ax = sheet()
    s = 0.115
    cx, cy = 105, 192
    def T(x, y): return (cx + x * s, cy + y * s)
    def rr(x0, y0, x1, y1, r, **kw):
        ax.add_patch(FancyBboxPatch(T(x0, y0), (x1 - x0) * s, (y1 - y0) * s, boxstyle="round,pad=0,rounding_size=%f" % (r * s), **kw))
    hw, hl = D.RACK_W / 2, D.RACK_L / 2
    rr(-hw, -hl, hw, hl, D.CORNER_R, fill=False, lw=1.0, ec=LC)
    rr(-hw + D.T, -hl + D.T, hw - D.T, hl - D.T, D.CORNER_R - D.T, fill=False, lw=0.4, ec=LC)
    rr(-hw + D.FLANGE_T, -hl + D.FLANGE_T, hw - D.FLANGE_T, hl - D.FLANGE_T, D.CORNER_R - D.FLANGE_T, fill=False, lw=0.4, ec=LC)
    for y in D.CROSS_Y:
        x0, y0 = T(-hw + D.T, y - D.HAT_TOP / 2)
        ax.add_patch(Rectangle((x0, y0), (D.RACK_W - 2 * D.T) * s, D.HAT_TOP * s, fill=True, fc='#e8e8e8', ec=LC, lw=0.5))
        for xc in (0, 280, -280):
            px, py = T(xc, y); ax.add_patch(Rectangle((px - 25 * s, py - 5 * s), 50 * s, 10 * s, fill=False, lw=0.3, ec=LC))
        if y in D.MOUNT_Y:
            for xc in (D.MOUNT_X, -D.MOUNT_X):
                px, py = T(xc, y); ax.add_patch(Circle((px, py), 5.5 * s, fill=False, lw=0.5, ec='#a00'))
                ax.plot([px - 3, px + 3], [py, py], color='#a00', lw=0.3); ax.plot([px, px], [py - 3, py + 3], color='#a00', lw=0.3)
        px, py = T(hw + 6, y); ax.text(px, py, "Y=%+.0f" % y + ("  (item 4)" if y in D.MOUNT_Y else "  (item 3)"), fontsize=4.5, va='center')
    for y in (hl, -hl):
        p0, p1 = T(0, y - D.FLANGE_T), T(0, y); ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=LC, lw=0.5)
    ax.text(cx, cy + hl * s + 12, "PLAN VIEW (from above)  scale 1:%.1f" % (1 / s), fontsize=7, weight='bold', ha='center')
    ax.text(T(0, hl + 2)[0], T(0, hl + 2)[1] + 1, "butt joint PS/DS (splice plate item 6 inside)", fontsize=4.5, ha='center', va='bottom')
    dim_h(ax, T(-hw, 0)[0], T(hw, 0)[0], T(0, -hl)[1] - 8, "%.0f" % D.RACK_W)
    dim_v(ax, T(hw, 0)[0] + 32, T(0, -hl)[1], T(0, hl)[1], "%.0f" % D.RACK_L)
    dim_h(ax, T(-D.MOUNT_X, 0)[0], T(D.MOUNT_X, 0)[0], T(0, D.MOUNT_Y[0])[1] + 4, "%.1f mount centres - VERIFY on canopy" % (2 * D.MOUNT_X), fs=5, color='#a00')
    dim_v(ax, T(-hw, 0)[0] - 6, T(0, -D.MOUNT_Y[0])[1], T(0, D.MOUNT_Y[0])[1], "%.0f" % (2 * D.MOUNT_Y[0]), color='#a00', side=-1)
    ax.text(cx, cy - hl * s - 15, "front of vehicle = +Y (top of view).  Rack symmetric front/rear.  Item 1 = left (PS) half, item 2 = right (DS) half.", fontsize=5, ha='center', color='#444')
    # ---- section A-A, full width, scale 0.14
    s2 = 0.14; ex, ey = 318, 250
    def T2(x, y): return (ex + x * s2, ey + y * s2)
    segs = D.rail_profile_segs()
    for sign in (-1, 1):
        for (x0, y0), (x1, y1) in segs:
            p0, p1 = T2(sign * (hw - x0), y0), T2(sign * (hw - x1), y1)
            ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=LC, lw=max(0.8, D.T * s2 * 2.83))
    for (x0, y0), (x1, y1) in ((( -hw + D.T, D.HAT_H), (hw - D.T, D.HAT_H)), ((-hw + D.T, 0), (hw - D.T, 0))):
        p0, p1 = T2(x0, y0), T2(x1, y1); ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#555', lw=0.6)
    rw = 1072 / 2
    p0, p1 = T2(-rw, -2), T2(rw, -2); ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#888', lw=0.6, ls='--')
    for sign in (-1, 1):
        p0, p1 = T2(sign * rw, -2), T2(sign * rw, -57); ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#888', lw=0.6, ls='--')
    ax.text(ex, ey + D.WALL_H * s2 + 7, "SECTION A-A  (looking along vehicle)  scale 1:%.1f" % (1 / s2), fontsize=6.5, weight='bold', ha='center')
    ax.text(ex, ey - 12, "canopy roof 40105 (1072 wide, side flanges down) - rack walls overhang roof edge by 29 each side", fontsize=4.8, ha='center', color='#666')
    dim_v(ax, T2(hw, 0)[0] + 6, T2(0, 0)[1], T2(0, D.WALL_H)[1], "%.0f" % D.WALL_H, fs=5)
    dim_h(ax, T2(-hw, 0)[0], T2(hw, 0)[0], ey + D.WALL_H * s2 + 2, "%.0f" % D.RACK_W, fs=5)
    # ---- detail B  wall + cross end, scale 1.0
    s3 = 1.0; dx, dy = 262, 105
    def T3(x, y): return (dx + x * s3, dy + y * s3)
    for (x0, y0), (x1, y1) in segs:
        p0, p1 = T3(x0, y0), T3(x1, y1); ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color=LC, lw=D.T * s3 * 2.83)
    # cross end: foot notched 16, web with tab through wall, top flange
    hx = D.T  # inner wall face
    web_pts = [((hx - D.TAB_PROUD, D.TAB_Z0), (hx - D.TAB_PROUD, D.TAB_Z1)),      # tab outside wall (proud)
               ((hx + 0.75, 3), (hx + 0.75, D.HAT_H - 0.75)), ((hx + 0.75, D.HAT_H - 0.75), (hx + 120, D.HAT_H - 0.75)),
               ((hx + D.LIP_B + 1, 0.75), (hx + 120, 0.75))]
    for (x0, y0), (x1, y1) in web_pts:
        p0, p1 = T3(x0, y0), T3(x1, y1); ax.plot([p0[0], p1[0]], [p0[1], p1[1]], color='#1f5fa0', lw=D.T * s3 * 2.83)
    p0 = T3(hx + 0.75, D.TAB_Z0); p1 = T3(hx - D.TAB_PROUD, D.TAB_Z0)
    ax.add_patch(Rectangle((p1[0], p1[1]), (D.TAB_PROUD + 0.75 + D.T) * s3, (D.TAB_Z1 - D.TAB_Z0) * s3, fill=True, fc='#1f5fa0', ec='none', alpha=0.9))
    px, py = T3(0.75, D.TIE_Z)
    ax.add_patch(Rectangle((px - 1.2, py - D.TIE_SLOT[1] / 2 * s3), 2.4, D.TIE_SLOT[1] * s3, fill=True, fc='white', ec='#a00', lw=0.6))
    ax.text(dx + 60, dy + D.WALL_H * s3 + 8, "DETAIL B - wall / cross member end (scale 1:1)", fontsize=6.5, weight='bold', ha='center')
    ax.text(px - 5, py, "tie slot\n%.0fx%.0f\nz=%.0f" % (D.TIE_SLOT[0], D.TIE_SLOT[1], D.TIE_Z), fontsize=4.5, ha='right', va='center', color='#a00')
    ax.text(T3(hx + 25, D.HAT_H / 2)[0], T3(0, D.HAT_H / 2)[1], "cross hat (item 3/4) web section\ntab %.0f tall x %.1f thk through wall slot,\nproud %.1f - weld outside, grind flush\nfoot notched %.0f clears lip" %
            (D.TAB_Z1 - D.TAB_Z0, D.T, D.TAB_PROUD, D.LIP_B + 1), fontsize=4.5, va='center', color='#1f5fa0')
    dim_v(ax, T3(D.FLANGE_T + 110, 0)[0], T3(0, D.HAT_H)[1], T3(0, D.WALL_H)[1], "%.0f" % (D.WALL_H - D.HAT_H), fs=5)
    dim_v(ax, T3(D.FLANGE_T + 110, 0)[0], T3(0, 0)[1], T3(0, D.HAT_H)[1], "%.0f deck" % D.HAT_H, fs=5)
    dim_h(ax, T3(0, 0)[0], T3(D.FLANGE_T, 0)[0], T3(0, D.WALL_H)[1] + 3, "%.0f" % D.FLANGE_T, fs=5)
    dim_h(ax, T3(0, 0)[0], T3(D.LIP_B, 0)[0], T3(0, 0)[1] - 6, "%.0f" % D.LIP_B, fs=5)
    # ---- key data box (left bottom)
    kx, ky = 20, 84
    ax.text(kx, ky, "KEY DATA", fontsize=7, weight='bold')
    kd = ["Overall %.0f (W) x %.0f (L) x %.0f (H), plan corners R%.0f - same footprint as Rev-02, bolts to existing canopy roof holes." % (D.RACK_W, D.RACK_L, D.WALL_H, D.CORNER_R),
          "Deck at Z=%.0f (7 top-hat crosses 60x45), wall lip %.0f above deck, boxed top rail (25 flange + 25 return)." % (D.HAT_H, D.WALL_H - D.HAT_H),
          "Material: 304 (1.4301) 2B, 1.5 mm throughout. Fabricated mass ≈ %.1f kg. Rated payload 250 kg evenly distributed (see RRD-2000 calc report)." % total_mass,
          "Rated tie-down points: deck accessory slots (3 per cross, 21 total), 150 kg each. Wall slots: lashing / cargo net only (≤ 25 kg lateral, 150 kg vertical).",
          "Mount: 4x M10 at X=±%.1f, Y=±%.0f through mount crosses (item 4) into canopy roof rib holes. VERIFY hole pitch on canopy before cutting item 4." % (D.MOUNT_X, D.MOUNT_Y[0])]
    import textwrap
    j = 0
    for t in kd:
        for ln in textwrap.wrap("• " + t, 110):
            ax.text(kx, ky - 6 - j * 4.4, ln, fontsize=5.0); j += 1
    title_block(ax, "RRD-2000-" + P.REV, "Roof Rack DC - cage style - GA", "1:%.1f" % (1 / s), 1, idx, n, material="304 (1.4301) 2B all parts", mass=total_mass)
    pdf.savefig(fig); plt.close(fig)

def bom_sheet(pdf, idx, n, total_mass):
    import textwrap
    fig, ax = sheet()
    bx, by = 20, 275
    ax.text(bx, by, "BILL OF MATERIALS  -  RRD-2000-%s" % P.REV, fontsize=8, weight='bold')
    bom = [("ITEM", "PART NO.", "DESCRIPTION", "QTY", "MASS kg", "DXF / SOURCE"),
           ("1", "RRD-2001-" + P.REV, "Side rail PS (left half): long side + 2 corners + 2 half end walls", "1", "", "RRD-2001 FLAT.dxf"),
           ("2", "RRD-2002-" + P.REV, "Side rail DS (right half) - mirror of item 1", "1", "", "RRD-2002 FLAT.dxf"),
           ("3", "RRD-2003-" + P.REV, "Deck cross member, top-hat 60x45, at Y = 0, ±240, ±595", "5", "", "RRD-2003 FLAT.dxf"),
           ("4", "RRD-2004-" + P.REV, "Mount cross member, as item 3 + mount slots, at Y = ±470", "2", "", "RRD-2004 FLAT.dxf"),
           ("5", "RRD-2005-" + P.REV, "Mount cross closing plate 54 x 1000 (makes item 4 a box section)", "2", "", "RRD-2005 FLAT.dxf"),
           ("6", "RRD-2006-" + P.REV, "Rail splice plate 60 x 90", "2", "", "RRD-2006 FLAT.dxf"),
           ("7", "RRD-2007-" + P.REV, "Roof backing plate 120 x 30, slot 24 x 11", "4", "", "RRD-2007 FLAT.dxf"),
           ("8", "bought", "M10 x 110 A2-70 hex bolt + nyloc nut + 2x Ø30 x 3 washers", "4", "", "hardware"),
           ("9", "bought", "Spacer tube Ø16 x 1.5 x 20.5 long, 304 (between closing plate and roof rib)", "4", "", "hardware"),
           ("10", "bought", "Crush tube Ø12.7 x 1.6 x 42 long, 304 (welded inside item 4)", "4", "", "hardware"),
           ("11", "bought", "TIG filler ER308L; pickling paste / passivation", "-", "", "consumable")]
    masses = D.part_masses()[0]
    mm = {"1": masses['rail'], "2": masses['rail'], "3": masses['cross'], "4": masses['cross'], "5": masses['closer'], "6": masses['splice'], "7": masses['backing']}
    for r, row in enumerate(bom):
        for c, txt in enumerate(row):
            if c == 4 and row[0] in mm: txt = "%.2f" % mm[row[0]]
            ax.text(bx + [0, 14, 52, 215, 232, 255][c], by - 8 - r * 5.4, txt, fontsize=5.6, weight='bold' if r == 0 else None)
    yb = by - 10 - len(bom) * 5.4
    ax.text(bx, yb, "Total fabricated mass ≈ %.1f kg (excl. hardware).  One 2500 x 1250 x 1.5 sheet nests the complete set (see RRD-2000 NEST dxf, ~%.0f%% utilisation)." %
            (total_mass, 100 * (2 * 378146 + 7 * 190377 + 2 * 53992 + 2 * 5392 + 4 * 3592) / (2500 * 1250)), fontsize=5.8, weight='bold')
    ny = yb - 14
    notes = [("ASSEMBLY SEQUENCE", None),
             ("1", "Laser cut all parts from the DXF files (layer CUT). Deburr. Press-brake per each part sheet (all bends DOWN as drawn, inside R1.5). Check first-off of items 1 and 3 against the formed section before running the batch."),
             ("2", "Item 4: slide closing plate (5) inside the hat flush with the feet, stitch weld 25/100 both webs from below. Weld crush tubes (10) between closing plate hole and top slot."),
             ("3", "Rails (1)(2): roll both corner zones in-plane around a R60 former (web only - lip, flange and return are V-notched). Close every V-notch seam with TIG, grind flush outside."),
             ("4", "Jig halves on a flat table, outside faces to stops: tack PS to DS at front and rear centre butt joints. Fit splice plates (6) inside the wall across each joint; full weld joints inside and outside, grind outside flush."),
             ("5", "Insert the 7 crosses from inside: tabs through the wall slots, deck faces flush at Z=45, feet on the table. Measure diagonals (equal within 1.5 mm) and width 1130 at every cross before welding."),
             ("6", "Weld every tab on the outside of the wall (3 mm fillet full tab height, both tabs each end), grind flush. Stitch weld 20/150 cross feet-to-lip where they touch (optional) and the mount crosses full length."),
             ("7", "Clean, pickle and passivate (or brush and passivate). Fit rubber/EPDM strip 3 mm under all cross feet and the lip to protect the canopy paint."),
             ("8", "Fit to canopy: M10 bolt (8) down through mount cross slot, crush tube, spacer (9), roof rib hole, backing plate (7) inside the canopy, washer, nyloc. Torque 35 Nm. Re-torque after 500 km."),
             ("LOAD RATING", None),
             ("•", "Rated payload 250 kg static, evenly distributed on the deck; dynamic design factor 3.0 g vertical (off-road), 1.5 g braking, 1.0 g lateral - see calculation report RRD-2000-CALC."),
             ("•", "Tie down to the deck accessory slots (rated 150 kg per slot). Wall slots are for lashing and cargo nets only - do not ratchet heavy loads against the wall (plate yield limit ≈ 25 kg lateral per slot)."),
             ("•", "Check the canopy roof panel (40105) and canopy side walls for the 250 kg + 27 kg rack load - this report covers the rack only.")]
    j = 0
    for tag, txt in notes:
        if txt is None:
            ax.text(bx, ny - j * 4.4 - 2, tag, fontsize=6.5, weight='bold'); j += 1.4; continue
        for k, ln in enumerate(textwrap.wrap(txt, 170)):
            ax.text(bx + (0 if k == 0 else 6), ny - j * 4.4, ("%s. " % tag if k == 0 else "") + ln, fontsize=5.0); j += 1
    title_block(ax, "RRD-2000-" + P.REV, "Roof Rack DC - BOM & assembly notes", "-", 1, idx, n, material="304 (1.4301) 2B all parts", mass=total_mass)
    pdf.savefig(fig); plt.close(fig)

def build(outpdf):
    parts = P.all_parts(); masses = D.part_masses(); total = masses[1]
    n = len(parts) + 2
    with PdfPages(outpdf) as pdf:
        assembly_sheet(pdf, 1, n, total)
        bom_sheet(pdf, 2, n, total)
        for i, part in enumerate(parts):
            part_sheet(pdf, part, i + 3, n, part['outer'].area * D.T * D.RHO)
    return outpdf

if __name__ == '__main__':
    import sys
    print(build(sys.argv[1]))
