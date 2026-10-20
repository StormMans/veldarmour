"""
Veld Armour - Hilux GD6 Double Cab canopy roof rack, Rev-03 ("cage" style).
Parametric geometry + structural checks. All units mm, N, MPa.

Coordinate convention (vehicle): X across vehicle (+ = driver side), Y along vehicle
(+ = front), Z up.  Rack centre = (0,0), rack sits flat on canopy roof panel 40105.
"""
import math

# ---------------------------------------------------------------- material / process
T = 1.5                      # sheet thickness
R_IN = 1.5                   # inside bend radius (1t, standard V-die for 1.5 SS)
K = 0.44                     # K-factor for 304 at R=1t
FY = 205.0                   # 304 / 1.4301 min 0.2% proof (ASTM A240)
FU = 515.0
E = 193000.0
RHO = 7.93e-6                # kg/mm3

def bend_allowance(angle_deg, r=R_IN, t=T, k=K):
    return math.radians(angle_deg) * (r + k * t)

def bend_deduction(angle_deg, r=R_IN, t=T, k=K):
    a = math.radians(angle_deg)
    ossb = (r + t) * math.tan(a / 2)          # outside setback
    return 2 * ossb - bend_allowance(angle_deg, r, t, k)

BA90 = bend_allowance(90)
BD90 = bend_deduction(90)

# ---------------------------------------------------------------- rack envelope
RACK_W = 1130.0      # across vehicle, outside of side walls (same as Rev-02)
RACK_L = 1350.0      # along vehicle, outside of end walls (same as Rev-02)
CORNER_R = 60.0      # plan radius, outside of wall
WALL_H = 100.0       # wall height (outside)
LIP_B = 15.0         # bottom lip, inward
FLANGE_T = 25.0      # top flange, inward
RETURN_T = 25.0      # top return, down (deep return = stiff boxed-look top rail)

# cross member (top-hat, open bottom, sits on roof skin)
HAT_TOP = 60.0
HAT_H = 45.0
HAT_FOOT = 15.0
CROSS_Y = [0.0, 240.0, -240.0, 470.0, -470.0, 595.0, -595.0]   # along vehicle
MOUNT_Y = [470.0, -470.0]                                       # rows that bolt to roof
MOUNT_X = 435.7      # canopy roof rib top-flat centre, from 40105 flat pattern (VERIFY ON VEHICLE)

TAB_Z0, TAB_Z1 = 4.0, 41.0           # cross web tab height band
TAB_PROUD = 2.5                      # tab protrusion past outer wall face
SLOT_W = 1.8                         # tab slot width in wall
TIE_SLOT = (60.0, 20.0)              # wall tie-down slot L x W (full round ends)
TIE_Z = 65.0                         # tie slot centre height (slot z 55..75)
ACC_SLOT = (50.0, 10.0)              # accessory slot in cross top flange

# ---------------------------------------------------------------- flat-pattern maths
def flat_from_outside(dims, angles):
    """dims = list of outside dims (n), angles = list of bend angles (n-1).
    Returns (flat_total, bend_line_positions)."""
    pos = []
    s = 0.0
    for i, d in enumerate(dims[:-1]):
        bd = bend_deduction(angles[i])
        s += d - bd / 2 if i == 0 else d - bd
        pos.append(s)
    # fix cumulative: first bend at d0 - bd0/2, next at prev + d_i - bd_{i-1}/2 - bd_i/2
    pos = []
    s = 0.0
    for i in range(len(angles)):
        bd_prev = bend_deduction(angles[i - 1]) / 2 if i > 0 else 0.0
        bd = bend_deduction(angles[i]) / 2
        s += dims[i] - bd_prev - bd
        pos.append(s)
    total = s + dims[-1] - bend_deduction(angles[-1]) / 2
    return total, pos

# side rail profile: bottom lip | wall | top flange | return   (all 90 deg, same sense)
RAIL_DIMS = [LIP_B, WALL_H, FLANGE_T, RETURN_T]
RAIL_FLAT, RAIL_BENDS = flat_from_outside(RAIL_DIMS, [90, 90, 90])
# cross profile: foot | web | top | web | foot
CROSS_DIMS = [HAT_FOOT, HAT_H, HAT_TOP, HAT_H, HAT_FOOT]
CROSS_FLAT, CROSS_BENDS = flat_from_outside(CROSS_DIMS, [90, 90, 90, 90])

# z (height on formed wall, from roof) -> flat y in rail web zone
# straight web starts at z = R_IN + T = 3.0 which is BA/2 past bend line 1
def rail_z_to_flat(z):
    return RAIL_BENDS[0] + BA90 / 2 + (z - (R_IN + T))

# plan-view developed length of one half rail (one long side + 2 corners + 2 half ends)
CORNER_ARC = math.pi / 2 * (CORNER_R - T / 2)              # web mid-plane
LONG_STRAIGHT = RACK_L - 2 * CORNER_R
HALF_END = RACK_W / 2 - CORNER_R
RAIL_LEN = LONG_STRAIGHT + 2 * CORNER_ARC + 2 * HALF_END

# cross member length (between inner wall faces) and tabs
CROSS_LEN = RACK_W - 2 * T
CROSS_INNER = HAT_TOP - 2 * T

def cross_x_to_rail_y(y_vehicle):
    """vehicle y of a cross -> developed position s along the half rail flat (from front end)"""
    return HALF_END + CORNER_ARC + (LONG_STRAIGHT / 2 - y_vehicle)

# ---------------------------------------------------------------- thin-wall section properties
def section_props(segs, t=T):
    """segs: list of ((x0,y0),(x1,y1)) centreline segments of uniform thickness t.
    Returns dict A, cx, cy, Ixx, Iyy (about centroid), ymax/ymin extents."""
    A = 0; Sx = 0; Sy = 0
    for (x0, y0), (x1, y1) in segs:
        L = math.hypot(x1 - x0, y1 - y0); a = L * t
        A += a; Sx += a * (y0 + y1) / 2; Sy += a * (x0 + x1) / 2
    cx, cy = Sy / A, Sx / A
    Ixx = Iyy = 0
    for (x0, y0), (x1, y1) in segs:
        L = math.hypot(x1 - x0, y1 - y0); a = L * t
        ym = (y0 + y1) / 2 - cy; xm = (x0 + x1) / 2 - cx
        dy = y1 - y0; dx = x1 - x0
        Ixx += a * dy * dy / 12 + a * ym * ym + (L * t ** 3 / 12) * (dx / L) ** 2
        Iyy += a * dx * dx / 12 + a * xm * xm + (L * t ** 3 / 12) * (dy / L) ** 2
    ys = [p[1] for s in segs for p in s]; xs = [p[0] for s in segs for p in s]
    return dict(A=A, cx=cx, cy=cy, Ixx=Ixx, Iyy=Iyy,
                ytop=max(ys) - cy + t / 2, ybot=cy - min(ys) + t / 2,
                xmax=max(xs) - cx + t / 2, xmin=cx - min(xs) + t / 2)

def rail_profile_segs():
    """centreline, x inward (+), z up. Wall outer face at x=0."""
    xw = T / 2
    return [((xw, T / 2), (LIP_B, T / 2)),                       # bottom lip
            ((xw, T / 2), (xw, WALL_H - T / 2)),                 # wall
            ((xw, WALL_H - T / 2), (FLANGE_T, WALL_H - T / 2)),  # top flange
            ((FLANGE_T - T / 2, WALL_H - T / 2), (FLANGE_T - T / 2, WALL_H - RETURN_T))]  # return

def cross_profile_segs():
    """centreline, x across (centred), z up from roof."""
    h = HAT_H - T / 2; xw = HAT_TOP / 2 - T / 2
    return [((-xw - HAT_FOOT + T / 2, T / 2), (-xw, T / 2)),
            ((-xw, T / 2), (-xw, h)),
            ((-xw, h), (xw, h)),
            ((xw, h), (xw, T / 2)),
            ((xw, T / 2), (xw + HAT_FOOT - T / 2, T / 2))]

CLOSER_W = 54.0
def cross_with_closer_segs():
    """mount cross: hat + closing plate welded inside the hat flush with the feet -> box section"""
    segs = cross_profile_segs()
    segs.append(((-CLOSER_W / 2, T / 2), (CLOSER_W / 2, T / 2)))
    return segs

# ---------------------------------------------------------------- structural checks
PAYLOAD_KG = 250.0
G = 9.81
DYN_V = 3.0        # vertical dynamic factor (corrugations / pot-holes)
DYN_LAT = 1.0
DYN_LONG = 1.5
PERSON_KG = 120.0
CARGO_CG_H = 300.0  # cargo c.g. above deck (tent / box)

def checks():
    out = {}
    Wst = PAYLOAD_KG * G
    Wdyn = Wst * DYN_V
    # --- cross member: worst single cross carries 1/4 of payload as UDL across CROSS_LEN
    cp = section_props(cross_profile_segs())
    Zc = cp['Ixx'] / max(cp['ytop'], cp['ybot'])
    L = CROSS_LEN
    w_dyn = Wdyn / 4 / L; w_st = Wst / 4 / L
    M_udl = w_dyn * L ** 2 / 8
    sig_udl = M_udl / Zc
    defl_st = 5 * w_st * L ** 4 / (384 * E * cp['Ixx'])
    P = PERSON_KG * G
    M_pt = P * L / 4
    sig_pt = M_pt / Zc
    defl_pt = P * L ** 3 / (48 * E * cp['Ixx'])
    out['cross'] = dict(I=cp['Ixx'], Z=Zc, A=cp['A'], M_udl=M_udl, sig_udl=sig_udl, fos_udl=FY / sig_udl,
                        defl_st=defl_st, M_pt=M_pt, sig_pt=sig_pt, fos_pt=FY / sig_pt, defl_pt=defl_pt,
                        w_dyn=w_dyn, w_st=w_st, P=P)
    # --- side rail: each rail carries half of payload, supported at mount rows
    rp = section_props(rail_profile_segs())
    Zr = rp['Ixx'] / max(rp['ytop'], rp['ybot'])
    wr = Wdyn / 2 / RACK_L
    a = RACK_L / 2 - MOUNT_Y[0]           # overhang beyond mount row
    Lm = 2 * MOUNT_Y[0]                   # span between mount rows
    M_sup = wr * a ** 2 / 2
    M_mid = wr * Lm ** 2 / 8 - M_sup
    M_rail = max(M_sup, M_mid)
    sig_rail = M_rail / Zr
    wr_st = Wst / 2 / RACK_L
    # mid-span deflection of beam with overhangs (approx: simple span minus end-moment relief)
    d_simple = 5 * wr_st * Lm ** 4 / (384 * E * rp['Ixx'])
    d_relief = (wr_st * a ** 2 / 2) * Lm ** 2 / (8 * E * rp['Ixx'])
    defl_rail = d_simple - d_relief
    R_mount = wr * RACK_L / 2             # reaction per rail per mount row (dynamic)
    out['rail'] = dict(I=rp['Ixx'], Z=Zr, A=rp['A'], M_sup=M_sup, M_mid=M_mid, sig=sig_rail, fos=FY / sig_rail,
                       defl=defl_rail, R_mount=R_mount, a=a, Lm=Lm, w=wr)
    # --- mount cross: rail reaction at each end on a cantilever from the bolt + own tributary UDL
    mp = section_props(cross_with_closer_segs())
    Zm = mp['Ixx'] / max(mp['ytop'], mp['ybot'])
    lever = RACK_W / 2 - MOUNT_X
    M_cant = R_mount * lever
    trib = 0.5 * (CROSS_Y[1] - 0) / RACK_L  # tributary share of this cross (approx)
    w_m = Wdyn * (240.0 / RACK_L) / CROSS_LEN
    Lb = 2 * MOUNT_X
    M_own = w_m * Lb ** 2 / 8
    M_mount = M_cant + M_own
    sig_mount = M_mount / Zm
    sig_mount_nodoubler = M_mount / Zc
    out['mount'] = dict(I=mp['Ixx'], Z=Zm, lever=lever, M_cant=M_cant, M_own=M_own, M=M_mount,
                        sig=sig_mount, fos=FY / sig_mount, sig_nd=sig_mount_nodoubler, fos_nd=FY / sig_mount_nodoubler,
                        R=R_mount)
    # --- bolts M10 A2-70 (4 off)
    As = 58.0; proof = 450.0 * As  # N  (A2-70: Rp0.2 = 450 MPa)
    F_lat = Wst * DYN_LAT; F_long = Wst * DYN_LONG
    shear_bolt = max(F_lat, F_long) / 4
    Mo = F_lat * (CARGO_CG_H + HAT_H)
    T_overturn = Mo / (2 * MOUNT_X) / 2     # per bolt on tension side
    T_invert = Wst * 1.0 / 4                # 1g upward (inverted / rebound) per bolt
    T_bolt = T_overturn + T_invert
    shear_cap = 0.6 * proof
    util = (T_bolt / proof) ** 2 + (shear_bolt / shear_cap) ** 2
    out['bolts'] = dict(As=As, proof=proof, shear=shear_bolt, tension=T_bolt, util=util,
                        T_overturn=T_overturn, T_invert=T_invert, F_lat=F_lat, F_long=F_long)
    # --- tab welds: 2 tabs per end, fillet 3 mm x 37 long each (both sides of wall) -> use throat 0.7a
    R_end = w_dyn * L / 2                    # worst cross end reaction (dynamic)
    weld_len = 2 * TAB_Z1 - 2 * TAB_Z0       # 2 tabs x height
    weld_cap = 0.7 * 3.0 * weld_len * (0.6 * FU)
    out['weld'] = dict(R_end=R_end, cap=weld_cap, fos=weld_cap / R_end)
    # --- bearing of tabs in wall slots
    bearing = R_end / (2 * T * (TAB_Z1 - TAB_Z0))
    out['bearing'] = dict(sig=bearing, fos=FY / bearing)
    # --- top rail lateral strap load (2 kN at mid of long wall, acting inward at top)
    # wall tie slot: horizontal (inward) pull at slot top edge, wall braced by cross tabs up to TAB_Z1.
    lever = (TIE_Z + TIE_SLOT[1] / 2) - TAB_Z1
    b_eff = TIE_SLOT[0] + 2 * lever                 # 45 deg spread to the braced line
    Zp = b_eff * T ** 2 / 6
    P_allow_lat = FY * Zp / lever
    # vertical (in-plane) pull: net section each side of slot in shear/bearing
    P_allow_vert = 0.6 * FY * 2 * T * (WALL_H - TIE_Z - TIE_SLOT[1] / 2 - 3)   # shear of web above slot, both ends
    # top rail (flange + return + 30 mm wall) as lateral beam between corners
    tp = section_props([((0, 0), (FLANGE_T - T, 0)), ((FLANGE_T - T, 0), (FLANGE_T - T, -RETURN_T + T)),
                        ((0, 0), (0, -30.0))])
    Ls = LONG_STRAIGHT
    Zs = tp['Iyy'] / max(tp['xmax'], tp['xmin'])
    P_toprail = FY * Zs * 4 / Ls
    out['wallslot'] = dict(lever=lever, b_eff=b_eff, P_lat=P_allow_lat, P_vert=P_allow_vert,
                           I_top=tp['Iyy'], P_toprail=P_toprail)
    # --- local buckling (AISI effective width): flange b/t
    lim = 1.28 * math.sqrt(E / FY)
    out['buckling'] = dict(flange_bt=(FLANGE_T - 2 * T) / T, web_ht=(WALL_H - 2 * T) / T, hat_top_bt=(HAT_TOP - 2 * T) / T,
                           limit=lim)
    # --- canopy roof skin bearing under crush tube washer (M10, 30 mm OD washer)
    out['roof'] = dict(p=T_bolt / (math.pi / 4 * (30 ** 2 - 11 ** 2)))
    return out

# ---------------------------------------------------------------- mass
def part_masses():
    m = {}
    m['rail'] = RAIL_LEN * RAIL_FLAT * T * RHO
    m['cross'] = (CROSS_LEN + 2 * TAB_PROUD) * CROSS_FLAT * T * RHO
    m['closer'] = CLOSER_W * 1000 * T * RHO
    m['splice'] = 60 * 95 * T * RHO
    m['backing'] = 30 * 120 * T * RHO
    total = 2 * m['rail'] + 7 * m['cross'] + 2 * m['closer'] + 2 * m['splice'] + 4 * m['backing']
    return m, total

if __name__ == '__main__':
    print('BA90 %.3f BD90 %.3f' % (BA90, BD90))
    print('rail flat %.2f bends %s' % (RAIL_FLAT, [round(b, 2) for b in RAIL_BENDS]))
    print('cross flat %.2f bends %s' % (CROSS_FLAT, [round(b, 2) for b in CROSS_BENDS]))
    print('rail developed length %.1f (corner arc %.1f, half end %.1f)' % (RAIL_LEN, CORNER_ARC, HALF_END))
    c = checks()
    for k, v in c.items():
        print(k, {kk: round(vv, 2) for kk, vv in v.items()})
    print(part_masses())
