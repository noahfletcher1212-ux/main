"""Geometric validation of the tilt stand (calculated checks only - not physical tests).

Run:  python cad/validate.py  [stl_dir]   -> prints a report and writes validation_report.json
"""
import json
import math
import os
import sys
import tempfile

import numpy as np
import trimesh
from shapely.geometry import MultiPoint, Point

sys.path.insert(0, os.path.dirname(__file__))
import stand as S  # noqa: E402

BED = (150.0, 150.0, 150.0)
PHONE_MASS_G = 300.0      # conservative: iPhone 13 173 g + heavy case (measured case adds ~6 mm)
CRADLE_G, BASE_G = 14.2, 13.6      # PrusaSlicer filament mass, PLA, AD3 profile
BALLAST_G = 68.0          # optional cups: 2 x 4 two-euro coins (8.5 g each)
BALLAST_XYZ = (0.0, S.Y_REAR + S.RIB_T + S.CUP_WALL + S.CUP_ID / 2 - 0.5, S.Z_TABLE + 5.4)
G = 9.81


def mesh_of(wp, tol=0.02):
    import cadquery as cq
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "m.stl")
        cq.exporters.export(wp, p, tolerance=tol, angularTolerance=0.1)
        return trimesh.load(p)


def rot_x(theta_deg):
    """4x4 transform: rotation about the pivot axis (x-direction through P)."""
    t = math.radians(theta_deg)
    c, s = math.cos(t), math.sin(t)
    py, pz = S.P
    M = np.eye(4)
    M[1:3, 1:3] = [[c, -s], [s, c]]
    M[1, 3] = py - (c * py - s * pz)
    M[2, 3] = pz - (s * py + c * pz)
    return M


def inter_vol(a, b):
    try:
        i = trimesh.boolean.intersection([a, b], engine="manifold")
        return float(i.volume) if i is not None and len(i.faces) else 0.0
    except Exception:
        return float("nan")


def min_dist(a, b, n=6000, seed=0):
    pts, _ = trimesh.sample.sample_surface_even(a, n, seed=seed)
    _, d, _ = trimesh.proximity.closest_point(b, pts)
    pts2, _ = trimesh.sample.sample_surface_even(b, n, seed=seed)
    _, d2, _ = trimesh.proximity.closest_point(a, pts2)
    return float(min(d.min(), d2.min()))


def main(stl_dir):
    rep = {}
    print("=" * 72)
    print("1. Exported STL integrity and build-volume fit (print orientation)")
    for name in ["cradle", "base", "pin_single", "pins_x4", "plates/plate1_base_plus_4_pins",
                 "plates/plate2_cradle", "optional/base_with_ballast_cups"]:
        m = trimesh.load(os.path.join(stl_dir, f"{name}.stl"))
        bodies = m.split(only_watertight=False)
        ext = m.bounds[1] - m.bounds[0]
        fits = all(ext[i] <= BED[i] for i in range(3))
        # diamond check for diagonal placement: all vertices inside the 150x150 bed
        # when the part is centred on the bed
        c = (m.bounds[0] + m.bounds[1]) / 2
        xy = m.vertices[:, :2] - c[:2]
        margin = 75.0 - np.abs(xy).max()
        r = dict(watertight=bool(m.is_watertight), winding=bool(m.is_winding_consistent),
                 volume_cm3=round(m.volume / 1000, 2), bodies=len(bodies),
                 extent_mm=[round(float(e), 1) for e in ext], fits_bed=bool(fits),
                 bed_margin_mm=round(float(margin), 1), min_z=round(float(m.bounds[0][2]), 3))
        # printability: downward-facing area steeper than ~47 deg, above the first layer
        n = m.face_normals
        cz = m.triangles_center[:, 2] - m.bounds[0][2]
        over = (n[:, 2] < -0.74) & (cz > 0.3)
        r["overhang_area_mm2"] = round(float(m.area_faces[over].sum()), 1)
        if over.any():
            # report biggest overhang spots (print frame)
            idx = np.argsort(-m.area_faces * over)[:3]
            r["overhang_spots"] = [[round(float(v), 1) for v in m.triangles_center[i]] for i in idx]
        rep[f"stl_{name}"] = r
        print(f"   {name:34s} watertight={r['watertight']} bodies={r['bodies']} "
              f"extent={r['extent_mm']} fits={r['fits_bed']} margin={r['bed_margin_mm']} mm "
              f"overhang>47deg={r['overhang_area_mm2']} mm2")

    print("2. Building meshes in the assembly frame")
    cradle = mesh_of(S.make_cradle())
    base = mesh_of(S.make_base())
    phone = mesh_of(S.make_phone())
    pin = mesh_of(S.make_pin())
    # phone envelope including slot play (for clearance to the base)
    phone_env = trimesh.creation.box(extents=(S.PH_L, S.PH_T + S.CL_Y, S.PH_W))
    phone_env.apply_translation((0, -(S.PH_T + S.CL_Y) / 2, S.PH_W / 2))

    # ---------------------------------------------------------------- phone fit
    print("3. Phone fit in the cradle (theta = 0)")
    v = inter_vol(cradle, phone)
    slot = dict(phone_cradle_overlap_mm3=round(v, 3),
                x_clear_each_end=S.CL_X, thickness_clear_total=S.CL_Y,
                min_gap_phone_to_cradle=round(min_dist(phone, cradle), 3))
    rep["phone_fit"] = slot
    print(f"   overlap phone/cradle = {v:.3f} mm3 (should be 0); "
          f"min gap {slot['min_gap_phone_to_cradle']} mm")

    # keep-out zones on the phone (bottom-edge buttons, camera module on the back)
    # buttons protrude from the long edge faces (z=0 bottom, z=PH_W top) within y in [-14, 0]
    btn = trimesh.creation.box(extents=(60.0, S.PH_T - 0.2, 2.5))     # x in [-61.3,-1.3]
    btn.apply_translation((-31.3, -S.PH_T / 2, -0.25))
    btn_top = trimesh.creation.box(extents=(60.0, S.PH_T - 0.2, 2.5))
    btn_top.apply_translation((-31.3, -S.PH_T / 2, S.PH_W + 0.25))
    cam = trimesh.creation.box(extents=(40.0, 16.0, 44.0))            # x[-73,-33] z[33,77]
    cam.apply_translation((-53.0, 8.0, 55.0))
    rep["keepouts"] = dict(
        bottom_button_zone_gap=round(min_dist(btn, cradle, 3000), 2),
        top_button_zone_gap=round(min_dist(btn_top, cradle, 3000), 2),
        camera_zone_overlap_mm3=round(inter_vol(cam, cradle), 3))
    print(f"   cradle gap to bottom-edge button zone x[-61,-1]: "
          f"{rep['keepouts']['bottom_button_zone_gap']} mm, top edge "
          f"{rep['keepouts']['top_button_zone_gap']} mm; camera zone overlap "
          f"{rep['keepouts']['camera_zone_overlap_mm3']} mm3")

    # Lightning plug envelope at the +X end (boot up to 12.5 x 9 mm, 30 mm long)
    plug = trimesh.creation.box(extents=(30.0, 9.0, 12.5))
    plug.apply_translation((S.PH_L / 2 + 15.0 + 0.3, -S.PH_T / 2, S.PH_W / 2))
    rep["lightning_plug_overlap_mm3"] = round(inter_vol(plug, cradle), 3)
    print(f"   Lightning plug envelope overlap with cradle: {rep['lightning_plug_overlap_mm3']} mm3")

    # ---------------------------------------------------------------- tilt sweep
    print("4. Tilt sweep: cradle + phone vs base (and table plane)")
    sweep = []
    worst = None
    for th in np.arange(-22.0, 32.01, 0.5):
        M = rot_x(th)
        c = cradle.copy().apply_transform(M)
        p = phone_env.copy().apply_transform(M)
        vc = inter_vol(c, base)
        vp = inter_vol(p, base)
        zmin = min(c.bounds[0][2], p.bounds[0][2]) - S.Z_TABLE
        sweep.append((float(th), vc, vp, float(zmin)))
    free = [s for s in sweep if s[1] < 1e-3 and s[2] < 1e-3 and s[3] > 0]
    lo = min(s[0] for s in free)
    hi = max(s[0] for s in free)
    first_hit_lo = max(s for s in sweep if s[0] < lo)
    first_hit_hi = min(s for s in sweep if s[0] > hi)
    rep["sweep"] = dict(collision_free_range_deg=[lo, hi],
                        lower_stop=first_hit_lo, upper_stop=first_hit_hi,
                        min_table_clearance_in_range=round(min(s[3] for s in sweep
                                                               if -15 <= s[0] <= 25), 2))
    print(f"   collision-free from {lo:+.1f} to {hi:+.1f} deg (required -15..+25)")
    print(f"   first contact below: {first_hit_lo}   above: {first_hit_hi}  (deg, cradle mm3, phone mm3, z-clear)")
    print(f"   min clearance of moving parts above table in -15..+25: "
          f"{rep['sweep']['min_table_clearance_in_range']} mm")

    # minimum running clearance cradle<->base at the indexed positions
    gaps = {}
    for th in S.TILTS:
        c = cradle.copy().apply_transform(rot_x(th))
        p = phone_env.copy().apply_transform(rot_x(th))
        gaps[th] = (round(min_dist(c, base, 5000), 2), round(min_dist(p, base, 4000), 2))
    rep["index_position_min_gaps_cradle_phone_to_base"] = gaps
    print("   min gap at indexed positions (cradle-base, phone-base):",
          ", ".join(f"{k:+d}:{v[0]}/{v[1]}" for k, v in gaps.items()))

    # ---------------------------------------------------------------- vernier / pins
    print("5. Index pin alignment (vernier) and pin engagement")
    hole_c = [S.pol(a, S.R_IDX) for a in S.CHEEK_HOLES]
    align = {}
    for th in S.TILTS:
        best = []
        for k, a in enumerate(S.FIN_HOLES):
            fy, fz = S.pol(a + th, S.R_IDX)
            for j, (cy, cz) in enumerate(hole_c):
                best.append((math.hypot(fy - cy, fz - cz), k, j))
        best.sort()
        align[th] = dict(pair=(best[0][1], best[0][2]), offset_mm=round(best[0][0], 4),
                         next_nearest_mm=round(best[1][0], 2))
    rep["vernier"] = align
    ok = all(v["offset_mm"] < 1e-6 and v["next_nearest_mm"] > S.HOLE_D - S.PIN_D + 0.5
             for v in align.values())
    rep["vernier_unique"] = ok
    print(f"   every 5 deg position has exactly one hole pair a 5 mm pin can enter: {ok} "
          f"(other pairs are >= {min(v['next_nearest_mm'] for v in align.values())} mm misaligned; "
          f"pin enters only below {S.HOLE_D - S.PIN_D:.2f} mm)")
    for th, v in align.items():
        print(f"     tilt {th:+3d}: fin hole {v['pair'][0]+1}/5 + cheek hole "
              f"{'ABC'[v['pair'][1]]}  (next nearest pair {v['next_nearest_mm']} mm off)")
    # angular play from hole/pin clearance at the index radius
    dia_clear = S.HOLE_D - S.PIN_D
    play = math.degrees((dia_clear + dia_clear) / S.R_IDX)   # both holes, pivot pin ignored
    rep["index_play_deg_worst_case"] = round(play, 2)
    print(f"   worst-case angular backlash from hole clearance (index + pivot both "
          f"slack): about {play:.2f} deg (torque never reverses in range - see below)")

    # pin placement checks: pin axis along +X in the pin model, head at x in [0,2.5]
    pin_checks = {}
    for label, (yc, zc) in [("pivot", S.P)] + [(f"index_{t:+d}", S.pol(
            S.CHEEK_HOLES[align[t]['pair'][1]], S.R_IDX)) for t in (-15, 0, 25)]:
        # pin inserted from +X side: head outside cheek, tip pointing -X
        pm = pin.copy()
        pm.apply_translation((-S.PIN_HEAD_T, 0, -(S.PIN_D / 2 - S.PIN_FLAT)))  # head face at x=0, axis at z=0
        R = trimesh.transformations.rotation_matrix(math.pi, (0, 0, 1))
        pm.apply_transform(R)                       # tip now toward -X
        pm.apply_translation((S.CHEEK_X0 + S.CHEEK_T, yc, zc))
        th = 0 if label == "pivot" else int(label.split("_")[1])
        c = cradle.copy().apply_transform(rot_x(th))
        vb, vc = inter_vol(pm, base), inter_vol(pm, c)
        tip_x = float(pm.bounds[0][0])
        pin_checks[label] = dict(pin_base_overlap_mm3=round(vb, 3), pin_cradle_overlap_mm3=round(vc, 3),
                                 snap_bump_beyond_fin_inner_face_mm=round(S.FIN_X0 - (S.CHEEK_X0 + S.CHEEK_T - (S.STACK + 0.4 + 0.3)), 2),
                                 tip_x=round(tip_x, 2))
    rep["pins_in_holes"] = pin_checks
    for k, v in pin_checks.items():
        print(f"   {k:10s} pin-base overlap {v['pin_base_overlap_mm3']} mm3, pin-cradle overlap "
              f"{v['pin_cradle_overlap_mm3']} mm3")
    print(f"   pin shank length {S.STACK + 0.4:.1f} mm vs plate stack {S.STACK:.1f} mm: the snap shoulder "
          f"sits 0.4 mm past the fin's inner face; tip clear of all geometry (overlaps above)")
    # pin interference by design (prong flex): bump radius vs hole radius
    bump_r = S.PIN_D / 2 + 0.3
    rep["snap_bump_interference_mm_per_side"] = round(bump_r - S.HOLE_D / 2, 3)
    print(f"   snap bump radial interference (prongs flex): {rep['snap_bump_interference_mm_per_side']} mm/side")

    # ---------------------------------------------------------------- camera view
    print("6. Rear-camera field of view (16:9 video, full-sensor-width = conservative)")
    fovs = {"ultra_wide_13mm": (53.1, 36.8), "wide_26mm": (33.6, 20.5),
            "ultra_wide_4:3_photo": (53.1, 45.0)}
    pts_base, _ = trimesh.sample.sample_surface_even(base, 20000, seed=1)
    pts_base = np.vstack([pts_base, base.vertices])
    pts_cr, _ = trimesh.sample.sample_surface_even(cradle, 20000, seed=2)
    pts_cr = np.vstack([pts_cr, cradle.vertices])
    view = {}
    for fname, (hh, vh) in fovs.items():
        worst_margin = 1e9
        hits = []
        for th in S.TILTS:
            Minv = np.linalg.inv(rot_x(th))
            pb = trimesh.transform_points(pts_base, Minv)       # base in cradle frame
            for (lx, lz) in S.LENSES:
                for pts, nm in ((pb, "base"), (pts_cr, "cradle")):
                    d = pts - np.array([lx, 1.0, lz])
                    fwd = d[:, 1]
                    m = fwd > 0.5
                    ah = np.degrees(np.arctan2(np.abs(d[m, 0]), fwd[m]))
                    av = np.degrees(np.arctan2(np.abs(d[m, 2]), fwd[m]))
                    # angular margin outside the frustum (positive = outside)
                    marg = np.maximum(ah - hh, av - vh)
                    if marg.size:
                        mm = float(marg.min())
                        worst_margin = min(worst_margin, mm)
                        if mm < 0:
                            hits.append((th, nm, round(mm, 1)))
        view[fname] = dict(min_angular_margin_deg=round(worst_margin, 1), intrusions=hits[:6])
        print(f"   {fname:22s} closest stand point is {worst_margin:+.1f} deg outside the frame"
              + ("" if worst_margin >= 0 else f"  INTRUSIONS: {hits[:4]}"))
    rep["camera_view"] = view

    # ---------------------------------------------------------------- stability
    for scen, ballast_g in (("no_ballast", 0.0), ("ballast_cups_68g", BALLAST_G)):
        print(f"7. Stability (phone + case assumed {PHONE_MASS_G:.0f} g) - {scen}")
        m_cr, m_base = CRADLE_G, BASE_G           # PrusaSlicer filament mass (PLA)
        foot = base.vertices[np.abs(base.vertices[:, 2] - S.Z_TABLE) < 1e-3][:, :2]
        hull = MultiPoint([tuple(p) for p in foot]).convex_hull
        stab = {}
        for th in S.TILTS:
            M = rot_x(th)
            ph_c = trimesh.transform_points([[0, -S.PH_T / 2, S.PH_W / 2]], M)[0]
            cr_c = trimesh.transform_points([cradle.center_mass], M)[0]
            tot = PHONE_MASS_G + m_cr + m_base + ballast_g
            cg = (PHONE_MASS_G * ph_c + m_cr * cr_c + m_base * base.center_mass
                  + ballast_g * np.array(BALLAST_XYZ)) / tot
            p = Point(cg[0], cg[1])
            inside = hull.contains(p)
            marg = hull.exterior.distance(p) * (1 if inside else -1)
            h = cg[2] - S.Z_TABLE
            # margins front/back along y
            ys = [q[1] for q in hull.exterior.coords]
            front, back = max(ys) - cg[1], cg[1] - min(ys)
            # pivot torque from phone + cradle weight (sign: + tends to tilt camera up)
            mom = ((PHONE_MASS_G * (S.P[0] - ph_c[1]) + m_cr * (S.P[0] - cr_c[1])) * 1e-3 * G)
            stab[th] = dict(phone_cog_height_mm=round(ph_c[2] - S.Z_TABLE, 1),
                            tip_force_at_phone_top_N=round(min(front, back) * tot * 1e-3 * G /
                                                           (S.PH_W + S.P[1] + 14.0 - S.Z_TABLE), 2),
                            cog_xyz_rel_table=[round(cg[0], 1), round(cg[1], 1), round(h, 1)],
                            inside=bool(inside), min_margin_mm=round(marg, 1),
                            margin_front_mm=round(front, 1), margin_back_mm=round(back, 1),
                            tip_angle_front_deg=round(math.degrees(math.atan2(front, h)), 1),
                            tip_angle_back_deg=round(math.degrees(math.atan2(back, h)), 1),
                            pivot_torque_Nmm=round(mom, 1),
                            index_pin_force_N=round(mom / S.R_IDX, 2))
        rep[f"stability_{scen}"] = stab
        rep["masses_g_estimate"] = dict(phone=PHONE_MASS_G, cradle=round(m_cr, 1), base=round(m_base, 1))
        rep["footprint_mm"] = [round(hull.bounds[2] - hull.bounds[0], 1), round(hull.bounds[3] - hull.bounds[1], 1)]
        print(f"   footprint (convex hull of table contact) {rep['footprint_mm']} mm")
        for th, v in stab.items():
            print(f"   tilt {th:+3d}: CoG height {v['cog_xyz_rel_table'][2]:5.1f} mm, inside={v['inside']}, "
                  f"margin front {v['margin_front_mm']:5.1f} / back {v['margin_back_mm']:5.1f} mm, "
                  f"tip angle F {v['tip_angle_front_deg']:4.1f} / B {v['tip_angle_back_deg']:4.1f} deg, "
                  f"push to tip at phone top {v['tip_force_at_phone_top_N']} N, "
                  f"pivot torque {v['pivot_torque_Nmm']:6.1f} N.mm -> index pin {v['index_pin_force_N']} N")
        print(f"   phone CoG height above table: {stab[0]['phone_cog_height_mm']} mm at 0 deg")
        signs = {np.sign(v["pivot_torque_Nmm"]) for v in stab.values()}
        rep["torque_never_reverses"] = len(signs) == 1
        print(f"   gravity torque keeps one sign over the whole range: {rep['torque_never_reverses']} "
              "(pin always loaded the same way -> repeatable angle)")
    return rep


if __name__ == "__main__":
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "stl")
    r = main(d)
    with open(os.path.join(os.path.dirname(__file__), "..", "validation_report.json"), "w") as f:
        json.dump(r, f, indent=1, default=str)
