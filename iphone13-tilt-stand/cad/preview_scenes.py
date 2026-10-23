"""Scene list for the three.js/Playwright preview renderer (see cad/render/)."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import stand as S  # noqa: E402

COL = dict(base="#e07a2f", cradle="#2f6fd6", pin="#f4f1e8", body="#3a3d42", screen="#0d0f14",
           module="#1b1c1f", lens="#060606", flash="#e6dfc4")


def assembly(th, phone=True, ghost_phone=False):
    m = [dict(file="base", color=COL["base"], rough=0.6),
         dict(file=f"cradle_{th:+d}", color=COL["cradle"], rough=0.55),
         dict(file="pivot_pins", color=COL["pin"], rough=0.5),
         dict(file=f"index_pin_{th:+d}", color=COL["pin"], rough=0.5)]
    if phone:
        op = dict(opacity=0.35) if ghost_phone else {}
        m += [dict(file=f"phone_body_{th:+d}", color=COL["body"], rough=0.45, **op),
              dict(file=f"phone_screen_{th:+d}", color=COL["screen"], rough=0.15, metal=0.3, **op),
              dict(file=f"phone_module_{th:+d}", color=COL["module"], rough=0.4, **op),
              dict(file=f"phone_lens_{th:+d}", color=COL["lens"], rough=0.1, metal=0.5, **op),
              dict(file=f"phone_flash_{th:+d}", color=COL["flash"], rough=0.3, **op)]
    return m


def scenes(outdir):
    zt = S.Z_TABLE
    sc = []
    sc.append(dict(out=f"{outdir}/assembled_front.png", size=[1400, 950], ground=zt,
                   meshes=assembly(0),
                   camera=dict(pos=[-250, 330, 175], target=[0, -2, 22], fov=30)))
    sc.append(dict(out=f"{outdir}/assembled_rear.png", size=[1400, 950], ground=zt,
                   meshes=assembly(10),
                   camera=dict(pos=[230, -360, 200], target=[0, -8, 22], fov=30)))
    for th in (-15, 0, 25):
        sc.append(dict(out=f"{outdir}/side_{th:+d}.png", size=[900, 820], ground=zt,
                       meshes=assembly(th), light=[300, -100, 300],
                       camera=dict(pos=[600, -5, 25], target=[0, -5, 25], ortho=70)))
    sc.append(dict(out=f"{outdir}/index_closeup.png", size=[1300, 950], ground=zt,
                   meshes=assembly(10, ghost_phone=True), light=[250, 100, 300],
                   camera=dict(pos=[215, 150, 85], target=[44, 22, 12], fov=24)))
    sc.append(dict(out=f"{outdir}/mechanism_no_phone.png", size=[1400, 950], ground=zt,
                   meshes=assembly(0, phone=False),
                   camera=dict(pos=[-240, 280, 220], target=[0, -5, 5], fov=30)))
    for name, files in (("plate1_base_pins", [("print_base", COL["base"]), ("print_pins", COL["pin"])]),
                        ("plate2_cradle", [("print_cradle", COL["cradle"])])):
        meshes = [dict(file="bed", color="#d9dde3", rough=0.9)] + \
                 [dict(file=f, color=c, rough=0.55) for f, c in files]
        sc.append(dict(out=f"{outdir}/{name}.png", size=[1000, 860], ground=-0.6,
                       meshes=meshes, light=[-60, -120, 300],
                       camera=dict(pos=[-170, -230, 250], target=[0, 0, 10], fov=32)))
    return sc


if __name__ == "__main__":
    out = sys.argv[1]
    json.dump(scenes(sys.argv[2]), open(out, "w"), indent=1)
