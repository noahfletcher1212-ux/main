"""Export assembly meshes (world frame, Z up) for previews: base, cradle/phone/pins at tilts."""
import json
import math
import os
import sys

import cadquery as cq

sys.path.insert(0, os.path.dirname(__file__))
import stand as S  # noqa: E402


def phone_visual():
    body = S.make_phone()
    screen = S.bx(-S.PH_L / 2 + 5.5, S.PH_L / 2 - 5.5, -S.PH_T - 0.15, -S.PH_T + 0.5,
                  4.5, S.PH_W - 4.5).edges("|Y").fillet(6)
    x0, z1 = -S.PH_L / 2 + 4.0, S.PH_W - 5.5
    module = S.bx(x0, x0 + 33, -0.5, 0.9, z1 - 33, z1).edges("|Y").fillet(6)
    lenses = None
    for (lx, lz) in S.LENSES:
        l = cq.Workplane("XZ").workplane(offset=-1.6).center(lx, lz).circle(5.2).extrude(0.9)
        lenses = l if lenses is None else lenses.union(l)
    flash = cq.Workplane("XZ").workplane(offset=-1.0).center(S.LENSES[1][0], S.LENSES[0][1]).circle(2.0).extrude(0.2)
    return dict(phone_body=body, phone_screen=screen, phone_module=module,
                phone_lens=lenses, phone_flash=flash)


def pin_world(y, z, side):
    """Pin with its head on the outside of the cheek on `side` (+1 right / -1 left)."""
    p = S.make_pin().translate((-S.PIN_HEAD_T, 0, -(S.PIN_D / 2 - S.PIN_FLAT)))
    p = p.rotate((0, 0, 0), (0, 0, 1), 180)                  # tip toward -X
    p = p.translate((S.CHEEK_X0 + S.CHEEK_T, y, z))
    if side < 0:
        p = p.mirror("YZ")
    return p


def aligned_cheek_hole(theta):
    for a in S.FIN_HOLES:
        for c in S.CHEEK_HOLES:
            if abs(a + theta - c) < 1e-6:
                return S.pol(c, S.R_IDX)
    raise ValueError(theta)


def export(outdir, tilts=(-15, 0, 10, 25)):
    os.makedirs(outdir, exist_ok=True)
    tol = dict(tolerance=0.03, angularTolerance=0.15)
    manifest = {}

    def save(name, wp):
        cq.exporters.export(wp, os.path.join(outdir, name + ".stl"), **tol)
        manifest.setdefault("files", []).append(name)

    save("base", S.make_base())
    save("pivot_pins", pin_world(*S.P, 1).union(pin_world(*S.P, -1)))
    cr = S.make_cradle()
    ph = phone_visual()
    for th in tilts:
        save(f"cradle_{th:+d}", S.place(cr, th))
        for k, v in ph.items():
            save(f"{k}_{th:+d}", S.place(v, th))
        y, z = aligned_cheek_hole(th)
        save(f"index_pin_{th:+d}", pin_world(y, z, 1))
    # parts in print orientation for the bed previews
    save("print_base", S.base_print_pose(S.make_base()))
    save("print_pins", S.pins_layout(S.make_pin()))
    save("print_cradle", S.cradle_print_pose(cr))
    save("bed", S.bx(-75, 75, -75, 75, -0.6, 0.0))
    manifest["tilts"] = list(tilts)
    with open(os.path.join(outdir, "manifest.json"), "w") as f:
        json.dump(manifest, f)


if __name__ == "__main__":
    export(sys.argv[1])
