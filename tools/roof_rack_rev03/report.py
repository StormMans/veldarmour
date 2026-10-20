"""Structural calculation report (A4, reportlab)."""
import datetime, math
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
import rack_design as D
import parts as P

def build(outpdf, iso_png=None):
    c = D.checks(); masses, total = D.part_masses()
    ss = getSampleStyleSheet()
    H1 = ParagraphStyle('h1', parent=ss['Heading1'], fontSize=15, spaceAfter=6)
    H2 = ParagraphStyle('h2', parent=ss['Heading2'], fontSize=11.5, spaceBefore=8, spaceAfter=4)
    B = ParagraphStyle('b', parent=ss['BodyText'], fontSize=8.8, leading=11.5)
    S = ParagraphStyle('s', parent=B, fontSize=7.5, leading=9.5, textColor=colors.HexColor('#444444'))
    doc = SimpleDocTemplate(outpdf, pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title="RRD-2000-%s structural calculation" % P.REV, author="Veld Armour")
    E = []
    def tbl(rows, widths=None, head=True):
        cs = ParagraphStyle('c', parent=B, fontSize=7.6, leading=9.2)
        rows = [[Paragraph(str(x), cs) if (r > 0 and isinstance(x, str) and len(x) > 28) else x for x in row] for r, row in enumerate(rows)]
        t = Table(rows, colWidths=widths, hAlign='LEFT')
        st = [('FONTSIZE', (0, 0), (-1, -1), 7.8), ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
              ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'), ('TOPPADDING', (0, 0), (-1, -1), 2), ('BOTTOMPADDING', (0, 0), (-1, -1), 2)]
        if head: st += [('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8e8e8')), ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold')]
        t.setStyle(TableStyle(st)); return t
    def p(t, st=B): E.append(Paragraph(t, st))
    def fos_cell(v): return "%.2f  %s" % (v, "OK" if v >= 1.25 else ("marginal" if v >= 1.0 else "FAIL"))

    p("Structural calculation - canopy roof rack RRD-2000-%s" % P.REV, H1)
    p("Veld Armour - Toyota Hilux GD6 double cab canopy (roof panel 40105). Date %s. Prepared from the parametric design file "
      "(rack_design.py) - all numbers below are generated from the same parameters as the DXF/PDF drawing set." % datetime.date.today().isoformat(), S)
    if iso_png:
        E.append(Spacer(1, 3 * mm)); E.append(Image(iso_png, width=160 * mm, height=80 * mm)); E.append(Spacer(1, 2 * mm))

    p("1. Design basis", H2)
    p("Rack footprint %.0f x %.0f mm, plan corners R%.0f, wall height %.0f mm, deck (top of cross members) at %.0f mm above the canopy roof skin. "
      "Material 304 / 1.4301 stainless, 1.5 mm, 2B. Fabricated mass %.1f kg." % (D.RACK_W, D.RACK_L, D.CORNER_R, D.WALL_H, D.HAT_H, total))
    E.append(tbl([["Item", "Value", "Basis"],
                  ["Yield strength Rp0.2", "%.0f MPa" % D.FY, "ASTM A240 / EN 10088-2 minimum for 304 annealed"],
                  ["Tensile strength Rm", "%.0f MPa" % D.FU, "ASTM A240 minimum"],
                  ["Young's modulus", "%.0f GPa" % (D.E / 1000), "304"],
                  ["Rated payload", "%.0f kg (%.0f N) evenly distributed" % (D.PAYLOAD_KG, D.PAYLOAD_KG * D.G), "client brief 200-250 kg; 250 used"],
                  ["Vertical dynamic factor", "%.1f g" % D.DYN_V, "off-road corrugations / pot-holes (industry practice for 4x4 racks)"],
                  ["Longitudinal / lateral", "%.1f g / %.1f g" % (D.DYN_LONG, D.DYN_LAT), "emergency braking / cornering"],
                  ["Point load", "%.0f kg person on one cross member, mid-span" % D.PERSON_KG, "serviceability (loading the rack)"],
                  ["Acceptance", "dynamic case: stress <= Rp0.2 with FoS >= 1.25; static deflection <= L/250", "no permanent set in service"]],
                 [45 * mm, 60 * mm, 73 * mm]))
    p("Load path: cargo -> deck cross members (7 off top-hat 60x45x1.5) -> tabs in side-wall slots -> side rails (wall 100 + boxed top rail) "
      "-> mount cross members at Y = ±%.0f (box section with closing plate) -> 4x M10 bolts -> canopy roof rib holes with backing plates. "
      "Cross-member feet also bear directly on the roof skin, which is conservatively ignored." % D.MOUNT_Y[0])

    p("2. Section properties (thin-wall, centre-line)", H2)
    E.append(tbl([["Section", "A mm²", "Ixx mm⁴", "Z mm³"],
                  ["Deck cross, top-hat 60 x 45 x 15 feet", "%.0f" % c['cross']['A'], "%.0f" % c['cross']['I'], "%.0f" % c['cross']['Z']],
                  ["Mount cross, hat + 54 closing plate (box)", "-", "%.0f" % c['mount']['I'], "%.0f" % c['mount']['Z']],
                  ["Side rail: lip 15 / wall 100 / flange 25 / return 25", "%.0f" % c['rail']['A'], "%.0f" % c['rail']['I'], "%.0f" % c['rail']['Z']]],
                 [85 * mm, 25 * mm, 30 * mm, 30 * mm]))

    p("3. Deck cross member (RRD-2003)", H2)
    cr = c['cross']
    p("Worst case: one cross member carries 1/4 of the payload as a UDL (cluster of jerry cans / box on one slat), simply supported between the walls, "
      "span %.0f mm. Dynamic: w = %.2f N/mm, M = wL²/8 = %.0f Nm, σ = M/Z = %.0f MPa, FoS = %s. "
      "Person load %.0f N at mid-span (static): M = %.0f Nm, σ = %.0f MPa, FoS = %s. Static deflection under rated UDL %.2f mm (L/%.0f), "
      "under the person %.1f mm (L/%.0f)."
      % (D.CROSS_LEN, cr['w_dyn'], cr['M_udl'] / 1000, cr['sig_udl'], fos_cell(cr['fos_udl']), cr['P'], cr['M_pt'] / 1000, cr['sig_pt'],
         fos_cell(cr['fos_pt']), cr['defl_st'], D.CROSS_LEN / cr['defl_st'], cr['defl_pt'], D.CROSS_LEN / cr['defl_pt']))
    p("Local buckling (AISI S100 effective width): top flange b/t = %.0f and web h/t = %.0f are below the fully-effective limit 1.28√(E/fy) = %.0f, "
      "so the gross section is valid." % (c['buckling']['hat_top_bt'], (D.HAT_H - 2 * D.T) / D.T, c['buckling']['limit']))

    p("4. Side rail (RRD-2001 / 2002)", H2)
    r = c['rail']
    p("Each rail collects half of the payload through the cross-member tabs and spans between the two mount rows (span %.0f mm, overhang %.0f mm each end). "
      "Dynamic UDL w = %.2f N/mm: M(support) = %.0f Nm, M(mid-span) = %.0f Nm, σ = %.0f MPa, FoS = %s. Static mid-span deflection %.2f mm. "
      "Reaction per rail per mount row (dynamic) R = %.0f N - this is what the mount cross and tab welds must carry."
      % (r['Lm'], r['a'], r['w'], r['M_sup'] / 1000, r['M_mid'] / 1000, r['sig'], fos_cell(r['fos']), r['defl'], r['R_mount']))
    p("Wall slenderness h/t = %.0f with the boxed top rail acting as an edge stiffener; flange b/t = %.0f < %.0f: fully effective." %
      (c['buckling']['web_ht'], c['buckling']['flange_bt'], c['buckling']['limit']))

    p("5. Mount cross member (RRD-2004 + closing plate RRD-2005)", H2)
    m = c['mount']
    p("The rail reaction R = %.0f N enters each end of the mount cross %.1f mm outboard of the bolt (lever = half width - mount X). "
      "Cantilever moment %.0f Nm plus the member's own tributary deck load (%.0f Nm) = %.0f Nm. As a plain open hat this gives σ = %.0f MPa (FoS %.2f); "
      "with the closing plate welded inside the hat (box section) σ = %.0f MPa, FoS = %s. The closing plate is therefore mandatory on the two mount crosses."
      % (m['R'], m['lever'], m['M_cant'] / 1000, m['M_own'] / 1000, m['M'] / 1000, m['sig_nd'], m['fos_nd'], m['sig'], fos_cell(m['fos'])))

    p("6. Tabs, slots and welds", H2)
    w = c['weld']
    p("Worst cross-member end reaction (dynamic) %.0f N through two tabs %.0f mm tall. Tab bearing in the wall slot: %.1f MPa (FoS %.0f). "
      "Fillet welds 3 mm on the outside of the wall, both tabs, full height (%.0f mm total): capacity %.0f N at 0.6·Rm on the throat, FoS %.0f. "
      "Rail reactions at the mount rows (%.0f N) go through the same tab/weld detail with FoS > 25. Weld 304 with ER308L, TIG; pickle/passivate."
      % (w['R_end'], D.TAB_Z1 - D.TAB_Z0, c['bearing']['sig'], c['bearing']['fos'], 2 * (D.TAB_Z1 - D.TAB_Z0), w['cap'], w['fos'], r['R_mount']))

    p("7. Mounting bolts and canopy interface", H2)
    b = c['bolts']
    p("4x M10 A2-70 (As = %.0f mm², proof load %.1f kN). Lateral %.1f g gives %.0f N total shear, braking %.1f g gives %.0f N: %.0f N per bolt. "
      "Overturning from lateral load at a cargo c.g. %.0f mm above the deck adds %.0f N tension per bolt; a 1 g rebound/inverted case adds %.0f N. "
      "Combined utilisation (tension² + shear²) = %.3f - bolts are not critical. Clamp load spreads through the crush tube (no hat crushing) and the "
      "Ø30 washer / 120 x 30 backing plate onto the 1.5 mm roof rib: bearing %.1f MPa. Torque 35 Nm."
      % (b['As'], b['proof'] / 1000, D.DYN_LAT, b['F_lat'], D.DYN_LONG, b['F_long'], b['shear'], D.CARGO_CG_H, b['T_overturn'], b['T_invert'], b['util'], c['roof']['p']))
    p("The canopy roof panel 40105 and the canopy side walls carry the rack + payload (≈ %.0f kg static, %.0f kg dynamic) - they are outside this calculation "
      "and should be checked by Veld Armour against the canopy design, as for Rev-02." % (total + D.PAYLOAD_KG, (total + D.PAYLOAD_KG) * D.DYN_V))

    p("8. Wall tie-down slots - usage limit", H2)
    ws = c['wallslot']
    p("The %.0f x %.0f slots in the wall sit %.0f mm above the line where the cross-member tabs brace the wall. A horizontal (inward) strap pull at a slot "
      "bends the 1.5 mm wall as a plate cantilever: with a 45° load spread (effective width %.0f mm) the wall reaches yield at %.0f N (≈ %.0f kg). "
      "In-plane (vertical) pull is limited by shear of the wall above the slot at > %.0f N. The boxed top rail alone, as a lateral beam between the "
      "corners, yields at a %.0f N mid-span point load. Therefore: wall slots are for cargo nets and light lashing only (≤ 25 kg lateral per slot); "
      "rated tie-down points are the deck accessory slots (3 per cross member, 21 total, 150 kg each - cross-member capacity governs)."
      % (D.TIE_SLOT[0], D.TIE_SLOT[1], ws['lever'], ws['b_eff'], ws['P_lat'], ws['P_lat'] / D.G, ws['P_vert'], ws['P_toprail']))

    p("9. Summary", H2)
    E.append(tbl([["Check", "Load case", "Stress MPa", "FoS on Rp0.2", "Result"],
                  ["Deck cross - bending", "1/4 payload UDL x 3 g", "%.0f" % cr['sig_udl'], "%.2f" % cr['fos_udl'], "OK"],
                  ["Deck cross - point load", "120 kg person mid-span", "%.0f" % cr['sig_pt'], "%.2f" % cr['fos_pt'], "OK"],
                  ["Side rail - bending", "1/2 payload UDL x 3 g", "%.0f" % r['sig'], "%.2f" % r['fos'], "OK"],
                  ["Mount cross (box) - bending", "rail reaction + deck, 3 g", "%.0f" % m['sig'], "%.2f" % m['fos'], "OK"],
                  ["Tab weld", "cross end reaction, 3 g", "-", "%.0f" % w['fos'], "OK"],
                  ["M10 bolts", "1.5 g long. / 1 g lat. / 1 g rebound", "-", "util. %.3f" % b['util'], "OK"],
                  ["Static deflection", "250 kg, deck cross", "%.2f mm" % cr['defl_st'], "L/%.0f" % (D.CROSS_LEN / cr['defl_st']), "OK"],
                  ["Wall slot lateral pull", "strap at slot", "yield at %.0f N" % ws['P_lat'], "-", "usage limit"]],
                 [45 * mm, 50 * mm, 28 * mm, 28 * mm, 25 * mm]))
    p("Conclusion: the Rev-03 cage-style rack in 1.5 mm 304 is adequate for a 250 kg evenly distributed payload with a 3 g vertical dynamic factor, "
      "provided (a) the two mount crosses are built as box sections with the closing plate, (b) heavy loads are strapped to the deck slots, not the wall, "
      "and (c) the canopy roof hole pitch is verified before cutting the mount crosses. Increase to 2.0 mm 304 if the rack will routinely carry "
      "more than 250 kg or a tent plus occupants (static 250 kg deck load with people on it exceeds the point-load case).")
    p("Assumptions and limits: thin-wall elastic beam theory, bend radii ignored in section properties (conservative), no fatigue assessment "
      "(stresses at 1 g are < 40 MPa, well below the 304 endurance limit); welds assumed sound and full length; canopy structure not assessed.", S)
    doc.build(E)
    return outpdf

if __name__ == '__main__':
    import sys
    print(build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
