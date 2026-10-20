"""Quick 3D preview of the formed rack (matplotlib, no CAD)."""
import math, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import rack_design as D

def plan_outline(inset, n=10):
    """closed plan loop of the wall at given inset from outside, with R corners"""
    hw, hl = D.RACK_W / 2 - inset, D.RACK_L / 2 - inset
    r = D.CORNER_R - inset
    pts = []
    for (cx, cy, a0) in ((hw - r, hl - r, 0), (-hw + r, hl - r, 90), (-hw + r, -hl + r, 180), (hw - r, -hl + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def band(loop_a, loop_b, za, zb, color, alpha=0.9):
    polys = []
    for i in range(len(loop_a)):
        j = (i + 1) % len(loop_a)
        polys.append([(*loop_a[i], za), (*loop_a[j], za), (*loop_b[j], zb), (*loop_b[i], zb)])
    return Poly3DCollection(polys, facecolor=color, edgecolor='none', alpha=alpha)

def build(png):
    fig = plt.figure(figsize=(12, 6.5))
    ax = fig.add_subplot(111, projection='3d')
    o = plan_outline(0); i1 = plan_outline(D.T); f = plan_outline(D.FLANGE_T)
    grey = '#9aa3ad'; dark = '#6b737c'; light = '#c9d0d6'
    ax.add_collection3d(band(o, o, 0, D.WALL_H, grey))                         # wall
    ax.add_collection3d(band(o, f, D.WALL_H, D.WALL_H, light))                 # top flange
    ax.add_collection3d(band(f, f, D.WALL_H, D.WALL_H - D.RETURN_T, dark))    # return
    ax.add_collection3d(band(i1, plan_outline(D.LIP_B), 0, 0, dark))           # bottom lip
    # crosses
    hw = D.RACK_W / 2 - D.T
    for y in D.CROSS_Y:
        x = np.array([-hw, hw]);
        top = [[(-hw, y - D.HAT_TOP / 2, D.HAT_H), (hw, y - D.HAT_TOP / 2, D.HAT_H), (hw, y + D.HAT_TOP / 2, D.HAT_H), (-hw, y + D.HAT_TOP / 2, D.HAT_H)]]
        ax.add_collection3d(Poly3DCollection(top, facecolor='#b8c0c8' if y not in D.MOUNT_Y else '#a7b3c2', edgecolor='#555', lw=0.3))
        for sgn in (-1, 1):
            web = [[(-hw, y + sgn * D.HAT_TOP / 2, 0), (hw, y + sgn * D.HAT_TOP / 2, 0), (hw, y + sgn * D.HAT_TOP / 2, D.HAT_H), (-hw, y + sgn * D.HAT_TOP / 2, D.HAT_H)]]
            ax.add_collection3d(Poly3DCollection(web, facecolor=dark, edgecolor='none', alpha=0.9))
        for xc in (0, 280, -280):
            ax.plot([xc - 25, xc + 25, xc + 25, xc - 25, xc - 25], [y - 5, y - 5, y + 5, y + 5, y - 5], [D.HAT_H + 0.5] * 5, color='#333', lw=0.5)
    # tie slots (draw as dark rectangles on walls)
    for yv in (0, 135, -135, 270, -270, 405, -405, 540, -540):
        for sgn in (-1, 1):
            xw = sgn * (D.RACK_W / 2 + 0.3)
            ax.plot([xw] * 5, [yv - 30, yv + 30, yv + 30, yv - 30, yv - 30], [D.TIE_Z - 10, D.TIE_Z - 10, D.TIE_Z + 10, D.TIE_Z + 10, D.TIE_Z - 10], color='#222', lw=0.8)
    for xs in (100, 250, 400):
        for sgn in (-1, 1):
            for sy in (-1, 1):
                yw = sy * (D.RACK_L / 2 + 0.3); xc = sgn * xs
                ax.plot([xc - 30, xc + 30, xc + 30, xc - 30, xc - 30], [yw] * 5, [D.TIE_Z - 10, D.TIE_Z - 10, D.TIE_Z + 10, D.TIE_Z + 10, D.TIE_Z - 10], color='#222', lw=0.8)
    ax.set_xlim(-700, 700); ax.set_ylim(-700, 700); ax.set_zlim(-350, 350)
    ax.set_box_aspect((1, 1, 0.5))
    ax.view_init(elev=28, azim=-50)
    ax.set_axis_off()
    ax.set_title("RRD-2000-%s  cage-style canopy rack  %.0f x %.0f x %.0f  (304, 1.5 mm)" % (D.__dict__.get('REV', 'Rev-03') if False else 'Rev-03', D.RACK_W, D.RACK_L, D.WALL_H), fontsize=10)
    fig.savefig(png, dpi=140, bbox_inches='tight', facecolor='white')
    return png

if __name__ == '__main__':
    print(build(sys.argv[1]))
