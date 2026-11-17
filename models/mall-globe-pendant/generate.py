"""Build a ribbed opaline globe pendant with a scalloped spun-brass gallery."""
from pathlib import Path
import math
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/"scripts"))
from mall_ceiling_profiles import disc, group, material, revolve, screw
from mall_lighting_delivery import deliver

ROOT="ASSET_MallGlobePendant"
VIEW=(.85,-.32,1.5)


def build(lod):
    root=group(ROOT)
    brass=material("Brushed honey brass","B58A52",.75,.31)
    patina=material("Aged bronze recess","594D3F",.57,.38)
    cord=material("Espresso textile flex","352E29",.03,.65)
    opal=material("Ribbed vanilla opaline","FFF0D4",.04,.28,.16)
    sides=24 if lod else 48
    ceiling=group("Stepped ceiling rose",root)
    revolve("Spun brass canopy",ceiling,brass,[(0,-.031),(.014,-.031),(.018,-.026),
        (.022,-.022),(.043,-.018),(.052,-.012),(.055,-.008),(.055,-.0015),(.053,0),(0,0)],sides)
    disc("Canopy accent seam",ceiling,patina,.0548,-.007,-.005,sides,.0003)
    disc("Upper cord grip",ceiling,patina,.009,-.043,-.030,16 if lod else 32,.0012)
    for sign in [-1,1]:
        if not lod:
            screw("Canopy fixing",ceiling,patina,(sign*.035,0,-.0200),(math.pi,0,0),.003)
    disc("Textile suspension",root,cord,.0033,-.222,-.041,10 if lod else 20,.00035)
    crown=group("Opaline gallery and keeper",root)
    disc("Lower strain relief",crown,patina,.0078,-.230,-.217,16 if lod else 24,.0007)
    # A flared brass cap closes around the glass neck, with scalloping at the lower edge.
    def scallop(radius,z,angle):
        return .0014*math.cos(12*angle)*min(1,max(0,(radius-.026)/.026))
    revolve("Scalloped brass crown",crown,brass,[(0,-.269),(.057,-.269),(.060,-.266),
        (.060,-.262),(.057,-.258),(.045,-.255),(.034,-.250),(.025,-.243),
        (.016,-.230),(.012,-.227),(0,-.227)],32 if lod else 96,scallop=scallop)
    disc("Crown finial",crown,brass,.012,-.231,-.224,16 if lod else 32,.0012)
    disc("Crown shadow bead",crown,patina,.057,-.2705,-.2675,sides,.0007)
    body=group("Moulded glass",root)
    # Analytic meridians converge at one bottom pole; the neck finishes beneath the brass cap.
    centre=-.373
    radius=.118
    stack=12 if lod else 25
    profile=[(0,centre-radius)]
    for i in range(1,stack+1):
        a=-math.pi/2+math.radians(158)*i/stack
        profile.append((radius*math.cos(a),centre+radius*math.sin(a)))
    profile.extend([(.045,centre+.115),(0,centre+.115)])
    def ribs(r,z,angle):
        return (.0033 if not lod else .0024)*(r/radius)**1.6*math.cos(16*angle)
    revolve("Sixteen-rib opal globe",body,opal,profile,32 if lod else 96,scallop=ribs)
    return root


if __name__ == "__main__":
    deliver(HERE,ROOT,build,VIEW)
