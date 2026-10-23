"""Parametric iPhone 13 tilting tabletop stand (CadQuery).

Coordinate system (the "cradle frame"; identical to the world frame at 0 deg tilt):
  +Y  points from the phone toward the scene (rear-camera direction)
  +Z  up,  +X to the user's right when looking at the screen
  Phone (in case): x in [-74.3, 74.3], y in [-14, 0] (y=0 is the camera/back face),
  z in [0, 76.8] (z=0 is the lower long edge).  Camera module is at top-left as
  seen from the screen, i.e. at -X, +Z.
Tilt theta > 0 = camera aims UP; it is a rotation about +X through the pivot P.

Parts: base (1), cradle (1), snap pin (print 4: 2 pivot, 1 index, 1 spare).
"""
import math
import os

import cadquery as cq
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

# ----------------------------------------------------------------------------
# Parameters (mm, deg)
# ----------------------------------------------------------------------------
PH_L, PH_W, PH_T = 148.6, 76.8, 14.0      # measured phone + case
PH_CORNER_R = 10.0                        # in-plane corner radius (assumed)
CL_X = 0.5                                # end clearance, each end
CL_Y = 0.6                                # total thickness clearance
Y_SCR = -(PH_T + CL_Y)                    # screen-side contact plane
X_IN = PH_L / 2 + CL_X                    # inner face of end walls (74.8)
END_T = 1.5                               # 1.5 mm = exactly 2 perimeters (fast)
X_OUT = X_IN + END_T                      # 77.2

Z_BED = -4.0                              # cradle bottom (print bed for cradle)
BEAM_T, BEAM_TOP = 1.5, 14.0              # camera-side beam y in [0, 1.5]
END_WALL_TOP = 14.0
LIP_W = 4.0                               # screen-lip overlap onto phone end
LIP_T = 1.5
LIP_TOP = 45.0
LEG_Y = -12.0                             # end leg of the screen lip stops here
END_CHAMFER = 4.0                         # rear-bottom chamfer of end assemblies

P = (12.0, 2.5)                           # pivot axis (y, z)
HUB_R = 6.5
HOLE_D = 5.35                             # pin holes (pin is 5.0)
TEAR_TOP = 0.35                           # teardrop truncation above circle
FIN_X0, FIN_T = 38.0, 4.0                 # fins: |x| in [38, 42]
GAP = 0.3
CHEEK_X0 = FIN_X0 + FIN_T + GAP           # 42.3
CHEEK_T = 4.0                             # cheeks: |x| in [42.3, 46.3]
REST_TOP_R, REST_TOP_L = 42.0, 28.0       # fin back edges = camera-side rest
PAD_RIB_X = -(PH_L / 2 - 10.0)            # left pad rib, 10 mm from the camera end

R_IDX = 30.0
FIN_HOLES = [5, 20, 35, 50, 65]           # cradle-frame angles (from +Y toward +Z)
CHEEK_HOLES = [20, 40, 60]                # world angles
TILTS = list(range(-15, 30, 5))           # indexed positions
PTR_A = 45.0                              # pointer notch angle on cheek (world)
FIN_FAN_R = 35.5
CHEEK_FAN_R = 35.4
SCALE_R1 = 46.0                           # outer radius of the scale band on the fin
SCALE_TXT = 4.0
THETA_MIN_STOP, THETA_MAX_STOP = -17.5, 27.5

# Base
Z_TABLE = -16.6                           # table plane (refined by validate.py)
BASE_X = 70.0
Y_FRONT = 45.0
Y_REAR = -64.0
RIB_T = 1.5
RIB_H = 7.0
MID_RIB_Y = 24.0
FOOT_D, FOOT_H = 14.0, 1.2                # corner feet (adhesion / optional bumpers)
CUP_ID, CUP_H, CUP_WALL = 26.5, 10.0, 1.5  # optional coin/washer ballast cups
CUP_X = 18.0
WITH_FEET, WITH_CUPS = True, False        # cups: optional base variant

# Pin
PIN_D = 5.0
PIN_HEAD_D, PIN_HEAD_T = 10.0, 2.5
STACK = FIN_T + GAP + CHEEK_T             # 8.3
PIN_FLAT = 0.5

ARC_SEG = 96


# ----------------------------------------------------------------------------
# 2D helpers (shapely, in the YZ plane: coords = (y, z))
# ----------------------------------------------------------------------------
def pol(a_deg, r, c=P):
    a = math.radians(a_deg)
    return (c[0] + r * math.cos(a), c[1] + r * math.sin(a))


def circle(c, r):
    return Point(c).buffer(r, resolution=ARC_SEG // 4)


def sector(c, r0, r1, a0, a1, n=60):
    pts = [pol(a0 + (a1 - a0) * i / n, r1, c) for i in range(n + 1)]
    if r0 > 0:
        pts += [pol(a1 - (a1 - a0) * i / n, r0, c) for i in range(n + 1)]
    else:
        pts.append(c)
    return Polygon(pts)


def teardrop(c, d):
    """Horizontal-axis hole profile: circle + 45 deg roof, truncated."""
    r = d / 2
    k = r / math.sqrt(2)
    roof = Polygon([(c[0] - k, c[1] + k), (c[0], c[1] + r * math.sqrt(2)),
                    (c[0] + k, c[1] + k)])
    td = circle(c, r).union(roof)
    return td.intersection(box(c[0] - r - 1, c[1] - r - 1, c[0] + r + 1, c[1] + r + TEAR_TOP))


def rotate_yz(geom, theta_deg, about=P):
    return affinity.rotate(geom, theta_deg, origin=about)


def extrude_x(poly2d, x0, x1):
    """Extrude a shapely polygon in the YZ plane between x0 and x1."""
    geoms = getattr(poly2d, "geoms", [poly2d])
    solid = None
    for g in geoms:
        g = g.simplify(0.01)
        ext = list(g.exterior.coords)[:-1]
        wp = cq.Workplane("YZ").workplane(offset=x0).polyline(ext).close().extrude(x1 - x0)
        for hole in g.interiors:
            h = list(hole.coords)[:-1]
            wp = wp.cut(cq.Workplane("YZ").workplane(offset=x0 - 1).polyline(h).close()
                        .extrude(x1 - x0 + 2))
        solid = wp if solid is None else solid.union(wp)
    return solid


def bx(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


# ----------------------------------------------------------------------------
# Cradle
# ----------------------------------------------------------------------------
def fin_ticks():
    """(cradle-frame angle, tilt) for every scale tick on the right fin."""
    return [(PTR_A - th, th) for th in TILTS]


def fin_profile(right):
    rest = REST_TOP_R if right else REST_TOP_L
    parts = [box(0.0, Z_BED, BEAM_T, rest), circle(P, HUB_R),
             box(0.0, Z_BED, P[0] + HUB_R, P[1])]          # square lower hub: no overhang
    if right:
        a_lo = min(a for a, _ in fin_ticks()) - 3
        a_hi = max(a for a, _ in fin_ticks()) + 3
        parts += [sector(P, 0, FIN_FAN_R, -4, 72),
                  sector(P, 0, SCALE_R1, a_lo, a_hi),
                  box(P[0], Z_BED, P[0] + FIN_FAN_R, P[1])]
    prof = unary_union(parts).convex_hull
    # lead-in chamfer at the top of the rest edge
    prof = prof.difference(Polygon([(-1, rest - 2.0), (1.2, rest + 0.01), (-1, rest + 1)]))
    if right:   # phone pad under the slot (button-free half of the lower edge)
        pad = Polygon([(Y_SCR, 0.0), (0.5, 0.0), (0.5, Z_BED), (Y_SCR + END_CHAMFER, Z_BED),
                       (Y_SCR, Z_BED + END_CHAMFER)])
        prof = prof.union(pad)
    holes = [teardrop(P, HOLE_D)]
    if right:
        holes += [teardrop(pol(a, R_IDX), HOLE_D) for a in FIN_HOLES]
    return prof.difference(unary_union(holes))


def rear_chamfer_yz():
    """Triangle removing the rear-bottom edge of the end assemblies (swing clearance)."""
    return Polygon([(Y_SCR - LIP_T - 1, Z_BED + END_CHAMFER),
                    (Y_SCR - LIP_T + END_CHAMFER, Z_BED - 0.01),
                    (Y_SCR - LIP_T - 1, Z_BED - 1)])


def engrave_yz(wp_x, center, angle_deg, text=None, rect=None, depth=0.5, size=3.4):
    """Cutter for an engraving on a +X-facing face at x = wp_x (reads from +X)."""
    w = (cq.Workplane("YZ").workplane(offset=wp_x - depth).center(*center)
         .transformed(rotate=(0, 0, angle_deg)))
    if text is not None:
        return w.text(text, size, depth + 1, combine=False, halign="center", valign="center",
                      font="DejaVu Sans", kind="bold")
    return w.rect(*rect).extrude(depth + 1)


def make_cradle():
    c = bx(-X_OUT, X_OUT, 0.0, BEAM_T, Z_BED, BEAM_TOP)              # camera-side beam
    for s in (1, -1):
        def m(x0, x1):
            return (min(s * x0, s * x1), max(s * x0, s * x1))
        xa, xb = m(X_IN, X_OUT)
        end = bx(xa, xb, Y_SCR - LIP_T, BEAM_T, Z_BED, END_WALL_TOP)  # end wall
        xa3, xb3 = m(X_IN - LIP_W, X_OUT)
        end = end.union(bx(xa3, xb3, Y_SCR - LIP_T, Y_SCR, Z_BED, LIP_TOP))   # screen lip
        end = end.union(bx(xa, xb, Y_SCR - LIP_T, LEG_Y, Z_BED, LIP_TOP))     # lip leg
        lead = Polygon([(Y_SCR + 0.01, LIP_TOP - 2.5), (Y_SCR + 0.01, LIP_TOP + 0.01),
                        (Y_SCR - 1.5, LIP_TOP + 0.01)])
        end = end.cut(extrude_x(lead, xa3 - 0.5, xb3 + 0.5))
        end = end.cut(extrude_x(rear_chamfer_yz(), xa3 - 0.5, xb3 + 0.5))
        c = c.union(end)
    # left phone pad: a single rib 10 mm from the phone's camera end (outside button zone)
    pad = Polygon([(Y_SCR, 0.0), (0.5, 0.0), (0.5, Z_BED), (Y_SCR + END_CHAMFER, Z_BED),
                   (Y_SCR, Z_BED + END_CHAMFER)])
    c = c.union(extrude_x(pad, PAD_RIB_X - RIB_T / 2, PAD_RIB_X + RIB_T / 2))
    for s in (1, -1):
        prof = fin_profile(right=(s > 0))
        x0, x1 = (FIN_X0, FIN_X0 + FIN_T) if s > 0 else (-FIN_X0 - FIN_T, -FIN_X0)
        c = c.union(extrude_x(prof, x0, x1))
    # tilt scale engraved on the outer (+X) face of the right fin, read against the cheek notch
    xo = FIN_X0 + FIN_T
    for a, th in fin_ticks():
        long_tick = th % 10 == 0
        r0 = SCALE_R1 - (4.2 if long_tick else 2.4)
        c = c.cut(engrave_yz(xo, pol(a, (r0 + SCALE_R1 + 1) / 2), a,
                             rect=(SCALE_R1 + 1 - r0, 0.8)))
        if long_tick:
            c = c.cut(engrave_yz(xo, pol(a, SCALE_R1 - 7.0), a - 90,
                                 text=(f"{th:+d}" if th else "0"), size=SCALE_TXT))
    return c


# ----------------------------------------------------------------------------
# Base
# ----------------------------------------------------------------------------
def swept_region(parts_yz, th0, th1, step=0.5):
    """Union of a YZ profile rotated about P over [th0, th1]."""
    shapes = []
    n = int(math.ceil((th1 - th0) / step))
    for i in range(n + 1):
        th = th0 + (th1 - th0) * i / n
        shapes.append(rotate_yz(parts_yz, th))
    out = []
    for a, b in zip(shapes[:-1], shapes[1:]):   # hulls of consecutive copies: continuous sweep
        for ga in getattr(a, "geoms", [a]):
            for gb in getattr(b, "geoms", [b]):
                out.append(ga.union(gb).convex_hull)
    return unary_union(out + shapes)


def phone_yz():
    return box(-PH_T - CL_Y, 0.0, 0.0, PH_W)     # include the slot play


def beam_yz():
    return box(0.0, Z_BED, BEAM_T, BEAM_TOP)


def moving_sweep(clear=1.0):
    moving = unary_union([beam_yz(), phone_yz()])
    return swept_region(moving, THETA_MIN_STOP - 0.5, THETA_MAX_STOP + 0.5).buffer(clear)


def stop_bump():
    """Region under the beam that the beam lands on exactly at THETA_MAX_STOP."""
    zt = Z_TABLE
    beam_sw = swept_region(beam_yz(), THETA_MIN_STOP - 0.5, THETA_MAX_STOP, 0.25)
    ztop = rotate_yz(beam_yz(), THETA_MAX_STOP).bounds[1]
    zone = box(-1.0, zt, 9.0, ztop + 0.01).difference(beam_sw)
    phone_sw = swept_region(phone_yz(), THETA_MIN_STOP - 0.5, THETA_MAX_STOP + 0.5).buffer(1.0)
    return zone.difference(phone_sw)


def cheek_profile(right):
    zt = Z_TABLE
    parts = [circle(P, HUB_R + 1.0), box(P[0] - 6.0, zt, P[0] + 8.0, P[1])]
    if right:
        parts += [sector(P, 0, CHEEK_FAN_R, 8, 72), box(P[0] - 6.0, zt, Y_FRONT, P[1])]
    prof = unary_union(parts).convex_hull.difference(moving_sweep())
    prof = unary_union([prof, stop_bump()])
    if prof.geom_type == "MultiPolygon":
        prof = max(prof.geoms, key=lambda g: g.area)
    holes = [teardrop(P, HOLE_D)]
    if right:
        holes += [teardrop(pol(a, R_IDX), HOLE_D) for a in CHEEK_HOLES]
        # pointer notch on the fan edge at PTR_A
        holes.append(Polygon([pol(PTR_A - 2.2, CHEEK_FAN_R + 0.5), pol(PTR_A, CHEEK_FAN_R - 1.8),
                              pol(PTR_A + 2.2, CHEEK_FAN_R + 0.5)]))
    return prof.difference(unary_union(holes))


def rail_profile():
    zt = Z_TABLE
    prof = box(Y_REAR, zt, Y_FRONT, zt + RIB_H).difference(moving_sweep())
    prof = unary_union([prof, stop_bump()])
    if prof.geom_type == "MultiPolygon":
        prof = max(prof.geoms, key=lambda g: g.area)
    return prof


def front_stop_height():
    """Top of the front rib in the right fin's slab: fin lands on it at THETA_MIN_STOP."""
    rot = rotate_yz(fin_profile(True), THETA_MIN_STOP)
    seg = rot.intersection(box(Y_FRONT - RIB_T - 0.2, -100, Y_FRONT + 0.2, 100))
    return seg.bounds[1] if not seg.is_empty else Z_TABLE + RIB_H


def make_base():
    zt = Z_TABLE
    b = None
    rail = rail_profile()
    for s in (1, -1):
        x0, x1 = (CHEEK_X0, CHEEK_X0 + CHEEK_T) if s > 0 else (-CHEEK_X0 - CHEEK_T, -CHEEK_X0)
        xm = (x0 + x1) / 2
        part = extrude_x(cheek_profile(right=(s > 0)), x0, x1)
        part = part.union(extrude_x(rail, xm - RIB_T / 2, xm + RIB_T / 2))
        # outer gusset under the pivot (stays below the pivot pin head)
        gx = x1 if s > 0 else x0
        tri = [(0, zt), (13, zt), (13, zt + 2.5), (0, P[1] - 7.0)]
        g = cq.Workplane("XZ").polyline(tri).close().extrude(-RIB_T)
        g = g.translate((gx, P[0] + 6.0, 0)) if s > 0 else \
            g.mirror("YZ").translate((gx, P[0] + 6.0, 0))
        part = part.union(g)
        b = part if b is None else b.union(part)
    front = bx(-BASE_X, BASE_X, Y_FRONT - RIB_T, Y_FRONT, zt, zt + RIB_H)
    ztop = min(front_stop_height(), zt + RIB_H)
    front = front.cut(bx(FIN_X0 - 0.7, CHEEK_X0, Y_FRONT - RIB_T - 1,
                         Y_FRONT + 1, ztop, zt + RIB_H + 1))
    b = b.union(front)
    b = b.union(bx(-BASE_X, BASE_X, Y_REAR, Y_REAR + RIB_T, zt, zt + RIB_H))
    xm = CHEEK_X0 + CHEEK_T / 2
    b = b.union(bx(-xm, xm, MID_RIB_Y, MID_RIB_Y + RIB_T, zt, zt + 5.0))
    # corner feet
    for sx in ((1, -1) if WITH_FEET else ()):
        for yc in (Y_FRONT - FOOT_D / 2, Y_REAR + FOOT_D / 2):
            b = b.union(cq.Workplane("XY").workplane(offset=zt)
                        .center(sx * (BASE_X - FOOT_D / 2), yc).circle(FOOT_D / 2).extrude(FOOT_H))
    # optional ballast cups behind the phone, against the rear rib
    yc = Y_REAR + RIB_T + CUP_WALL + CUP_ID / 2 - 0.5
    for sx in ((1, -1) if WITH_CUPS else ()):
        cup = (cq.Workplane("XY").workplane(offset=zt).center(sx * CUP_X, yc)
               .circle(CUP_ID / 2 + CUP_WALL).extrude(CUP_H))
        cup = cup.cut(cq.Workplane("XY").workplane(offset=zt + 1.0).center(sx * CUP_X, yc)
                      .circle(CUP_ID / 2).extrude(CUP_H))
        b = b.union(cup)
    # engraved index line from the pointer notch
    xo = CHEEK_X0 + CHEEK_T
    b = b.cut(engrave_yz(xo, pol(PTR_A, 33.2), PTR_A, rect=(2.4, 0.8)))   # overlaps notch
    return b


# ----------------------------------------------------------------------------
# Snap pin (built in print orientation: axis along X, flat on z = 0)
# ----------------------------------------------------------------------------
def make_pin():
    r = PIN_D / 2
    L_sh = STACK + 0.4
    head = cq.Workplane("YZ").circle(PIN_HEAD_D / 2).extrude(-PIN_HEAD_T).edges().chamfer(0.4)
    shank = cq.Workplane("YZ").circle(r).extrude(L_sh + 0.3)
    bump_pts = [(L_sh, 0), (L_sh, r), (L_sh + 0.3, r + 0.3), (L_sh + 0.7, r + 0.3),
                (L_sh + 2.3, r - 0.35), (L_sh + 2.3, 0)]
    bump = (cq.Workplane("XY").polyline(bump_pts).close()
            .revolve(360, (0, 0, 0), (1, 0, 0)))
    bump = bump.intersect(bx(L_sh - 0.1, L_sh + 3, -5, 5, -1.5, 1.5)).union(
        bump.intersect(cq.Workplane("YZ").workplane(offset=L_sh - 0.1)
                       .circle(r).extrude(3)))
    pin = head.union(shank).union(bump)
    slot = bx(4.0, L_sh + 3, -0.7, 0.7, -5, 5)
    pin = pin.cut(slot)
    flat_z = -(r - PIN_FLAT)
    pin = pin.cut(bx(-10, 20, -10, 10, -10, flat_z))
    return pin.translate((PIN_HEAD_T, 0, -flat_z))


# ----------------------------------------------------------------------------
# Phone (reference only, for previews/validation)
# ----------------------------------------------------------------------------
def make_phone():
    ph = (cq.Workplane("XZ").rect(PH_L, PH_W).extrude(PH_T)   # XZ extrudes toward -Y
          .edges("|Y").fillet(PH_CORNER_R).edges().fillet(2.5)
          .translate((0, 0, PH_W / 2)))
    return ph


def camera_module():
    """Camera keep-out/visual on the phone back (camera at top-left from screen side)."""
    x0 = -PH_L / 2 + 4.0
    z1 = PH_W - 5.5
    return bx(x0, x0 + 35.0, -0.6, 0.6, z1 - 35.5, z1)


LENSES = [(-PH_L / 2 + 13.5, PH_W - 15.2), (-PH_L / 2 + 28.5, PH_W - 30.2)]   # (x, z)


def place(shape, theta):
    """Rotate a cradle-frame shape to tilt theta about the pivot axis."""
    return shape.rotate((0, P[0], P[1]), (1, P[0], P[1]), theta)


def cradle_print_pose(cradle):
    """Upright (as used at 0 deg), rotated 45 deg about Z so the 152.6 mm length fits."""
    yc = (Y_SCR - LIP_T + P[1] + SCALE_R1 * math.cos(math.radians(PTR_A - 25))) / 2
    return cradle.translate((0, -yc, -Z_BED)).rotate((0, 0, 0), (0, 0, 1), 45)


def base_print_pose(base):
    return base.translate((0, -(Y_FRONT + Y_REAR) / 2, -Z_TABLE))


def pins_layout(pin, n=4, y=None):
    """n pins side by side; default spot is inside the base's open rear bay."""
    y = -(Y_FRONT + Y_REAR) / 2 + Y_REAR + 22.0 if y is None else y
    out = None
    for i in range(n):
        p = pin.translate((-PIN_HEAD_T - 5.5 + (i - (n - 1) / 2) * 20.0, y, 0))
        out = p if out is None else out.union(p)
    return out


def export_all(outdir):
    global WITH_CUPS
    os.makedirs(outdir, exist_ok=True)
    tol = dict(tolerance=0.02, angularTolerance=0.1)
    cradle = make_cradle()
    base = make_base()
    pin = make_pin()
    pins = pins_layout(pin)
    cq.exporters.export(cradle_print_pose(cradle), f"{outdir}/cradle.stl", **tol)
    cq.exporters.export(base_print_pose(base), f"{outdir}/base.stl", **tol)
    cq.exporters.export(pin, f"{outdir}/pin_single.stl", tolerance=0.01, angularTolerance=0.1)
    cq.exporters.export(pins_layout(pin, y=0.0), f"{outdir}/pins_x4.stl", tolerance=0.01,
                        angularTolerance=0.1)
    os.makedirs(f"{outdir}/plates", exist_ok=True)
    cq.exporters.export(base_print_pose(base).union(pins), f"{outdir}/plates/plate1_base_plus_4_pins.stl", **tol)
    cq.exporters.export(cradle_print_pose(cradle), f"{outdir}/plates/plate2_cradle.stl", **tol)
    WITH_CUPS = True
    base_cups = make_base()
    WITH_CUPS = False
    cq.exporters.export(base_print_pose(base_cups), f"{outdir}/optional/base_with_ballast_cups.stl", **tol) \
        if os.makedirs(f"{outdir}/optional", exist_ok=True) is None else None
    return dict(cradle=cradle, base=base, pin=pin, phone=make_phone(), base_cups=base_cups)


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "stl")
    parts = export_all(out)
    for k, v in parts.items():
        bb = v.val().BoundingBox()
        print(f"{k:7s} bbox {bb.xlen:6.1f} x {bb.ylen:6.1f} x {bb.zlen:6.1f}  vol {v.val().Volume()/1000:6.2f} cm3")
