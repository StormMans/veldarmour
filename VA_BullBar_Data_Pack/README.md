# VA-BB Bull Bar – CNC & Press-Brake Data Pack (Rev A)

Veld Armour re-issue of a sourced 4x4 steel bull bar design. Every sheet-metal part has been
re-drawn as a clean 1:1 flat pattern DXF with bend lines on their own layers, plus an A3 bend
sheet. The combined PDF is the shop-floor document.

## Contents

| Path | What it is |
|---|---|
| `VA-BB_Bull_Bar_Bending_Pack.pdf` | Combined A3 pack: assembly / BOM / cut-list sheet, tube schedule, one bend sheet per part (15 sheets) |
| `dxf/` | One DXF per plate part, mm, closed LWPOLYLINE profiles, origin at bottom-left of the flat |
| `pdf/` | The same sheets as individual PDFs |
| `parts_index.json` | Machine-readable part list: size, mass, bend table |
| `source/` | The original flat patterns and assembly drawing the pack was derived from (unmodified) |
| `tools/` | Python build scripts (`build.py`, `vageom.py`) – regenerate everything from `source/` |

## DXF layer convention

| Layer | Use |
|---|---|
| `CUT` | Laser/plasma profile. Outer contour + holes, closed polylines (true arcs as bulges). |
| `BEND_UP` | Bend-line centre, flange bends **toward** the viewer of the flat (red). Do not cut. |
| `BEND_DOWN` | Bend-line centre, flange bends **away** from the viewer (blue). Do not cut. |
| `ETCH` | Low-power surface mark (Veld Armour wordmark on the centre panel). |
| `INFO` | Reference text only – part number, material, bend callouts. Delete before nesting if your CAM objects. |

Flat patterns are shown from the bend-note face, exactly as the source SolidWorks flats. The
Veld Armour monogram and wordmark on the centre panel are therefore **mirrored in the flat** so
they read correctly on the outside face of the finished bar.

## Parts

| VA part no. | Description | Thk | Qty | Flat (mm) | Bends |
|---|---|---|---|---|---|
| VA-BB-01 | Centre panel (VA monogram cut-through) | 3 | 1 | 835 x 209 | 3 |
| VA-BB-02 | End panel (source item 2) | 3 | 1 | 688 x 687 | 6 |
| VA-BB-03 | Upright RH | 5 | 1 | 307 x 769 | 2 |
| VA-BB-04 | End panel, opposite hand (source item 4) | 3 | 1 | 688 x 687 | 6 |
| VA-BB-05 | End plate | 3 | 2 | 269 x 78 | 1 |
| VA-BB-06 | Bracket 1 (chassis bracket) | 5 | 2 | 184 x 258 | 2 |
| VA-BB-07 | Recovery lug (redrawn from assy sheet 8) | 8 | 4 | 91 x 92 | 0 |
| VA-BB-11 | Spot bracket (light mount) | 2 | 2 | 60 x 89 | 2 |
| VA-BB-12 | Centre panel P2 (top plate) | 3 | 1 | 835 x 289 | 2 |
| VA-BB-13 | Centre panel P3 (lower channel) | 3 | 1 | 835 x 153 | 2 |
| VA-BB-14 | Upright LH (mirror of 03, generated) | 5 | 1 | 307 x 769 | 2 |
| VA-BB-17 | Face 1 trim strip | 2 | 1 | 860 x 87 | 3 |
| VA-BB-18 | Face 1 LH trim strip (mirror of 17, generated) | 2 | 1 | 860 x 87 | 3 |

### Tube schedule (sheet `VA-BB-TUBE`, measured from the 1:20 assembly views)

| VA part no. | Description | Section | Cut length | Bends |
|---|---|---|---|---|
| VA-BB-08 | Pipe lift (jacking stub) x2 | CHS 38.1 x 2.0 | 100 (approx.) | – |
| VA-BB-09 | Pipe centre (top hoop) | CHS 63.5 x 2.0 | 702 | – |
| VA-BB-10 | Pipe spot (light bar) | CHS 38.1 x 2.0 | 805 | – |
| VA-BB-15/16 | Tube 50 side hoop LH / RH | CHS 50 x 2.0 | 510 | 1 x 90°, CLR 80, legs 180 / 204, bend plane 25° rearward |

Scale was fixed from the 1741.09 mm overall dimension. Wall is 2.0 mm on all tubes (Veld Armour
spec). Verify on the jig before cutting a batch.

## Engineering assumptions (change in `tools/build.py` and rebuild)

- Material **304 stainless steel (1.4301), 2B finish**. Density 7.93 g/cm³.
- **K-factor 0.46**, air bending (304). V-die = 8T. Expect roughly 1.5x mild-steel tonnage and 2–3° extra springback; over-bend and prove on a first-off. Flats are the developed lengths from the source model; the bend
  table on each sheet gives bend allowance / deduction and a recommended V-die so a first-off can
  be checked before batch forming.
- Bend angles follow the SolidWorks bend-note convention (90° = right angle, 162° = 18° included).
- Laser cut with nitrogen for an oxide-free edge; stainless-only tooling and brushes; TIG/MIG with ER308L, passivate after welding.

## Known caveats (also printed on the sheets)

1. **Face strips (17/18):** bend as drawn (the source "NO BENDING" note is superseded by Veld
   Armour). The 162° R42 bend wraps the R42 top radius of the upright – roll/bump-form it.
2. **Handing:** end panels 02/04 are named by source item number; which is LH/RH on the vehicle
   depends on fitment, which the source does not state.
3. **Fitment / vehicle:** not stated in the source. Overall width 1741 mm, centre 835 mm.
4. Several source inside radii are below 1T (R1.25 on 2 mm, R1.5 on 3 mm, R3 on 5 mm). Sheets carry a red warning; workable in 304 with a sharp-nose punch but confirm on first-off.
5. The source Upright and Spot-bracket flats contained duplicated zero-width relief geometry from
   the SolidWorks export; it has been removed and the outlines rebuilt as single closed contours.

## Rebuild

```
pip install ezdxf matplotlib shapely
python3 tools/build.py      # paths at the top of the script point at scratch/source dirs
```
