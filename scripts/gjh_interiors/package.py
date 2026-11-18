"""Assemble the reviewed catalog and staging delivery. --check compares without writing."""
import argparse
from hashlib import sha256
import json
import re
from textwrap import indent
from pathlib import Path

from measure import inspect, require

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROGRAM = json.loads((HERE/"program.json").read_text())
STAGE = ROOT/"exports/gjh-v11-interiors"
AUTHOR = "Yap Wei Jun project / agent-assisted procedural modeling"
REFERENCE = "packing-station"
VIEWS = ["front","side","3q"]
METHODS = {
    "S01":"Loft the walnut case and recess above a brass-edged rim. Hinge two independently removable leaves forward and bake their carving into the oxblood swatch.",
    "S04":"Extrude three folded leaf profiles with returned corners, perforation shading and a level front sample ledge on a stepped ash counter.",
    "S06":"Loft staggered solid ribbon banks across three drying combs and brace two beech trestles. Vary ribbon count, curvature and edge detail by tier.",
    "S05":"Build six stepped cabinet sections and a turned porcelain bowl above an open niche. Keep three projecting drawers on every tier and bake the Low grid and pulls.",
    "S10":"Loft two closed, fluted shell valves about a hinged shelf on a turned teak foot. Bake radial shading across continuous projected face UVs.",
    "S12":"Extrude four staggered index profiles over a recessed base. Give the front fin a level sample shelf and bake the opaque edge emission mask.",
    "S16":"Loft three annular eyelets over the bench. Bake the peg perforations and tint the looped lanyard at its vertices beside the blank sample.",
    "S17":"Build a shallow cork and felt lining under an asymmetric two-piece gable. Provide a floating ledge and bake seam shading on the Low faces.",
    "S02":"Retain the duct, sloped housing and filter banks from the original named meshes. Remove bevel loops on Low and add edge relief on Balanced.",
    "S03":"Retain the three-wheel chassis and chest. Retrace the source canopy rings and replace hubs with radial profiles. Drop the inactive collider, wafer scoring and small fittings on Low.",
    "S07":"Trace each of the six source tin courses as a closed scalloped outline on Low. Rebuild all 91 cans from their source centres and dimensions on Balanced.",
    "S08":"Recover all 24 body/lid pairs from the source display and rebuild their turned profiles. Preserve the original risers, pedestal and sign positions.",
    "S09":"Freeze the carrier at the original start frame. Dissolve redundant roller faces, retain the trestles and rails, and restore small edge bevels on Balanced.",
    "S11":"Rebuild the paper roll around the original spindle. Retain the open carton, cutter, rails and bench panels, and simplify their edge profiles.",
    "S13":"Resample six source headbands and six J hooks along their original sections. Rebuild oval cups, frame and header from the editable parts.",
    "S14":"Retopologise the three source assemblies from their measured extents into a layered housing, recessed wall bracket and opaque, softly shaded standby panel. Preserve screen aspect.",
    "S15":"Resample the open lid, curved rim and soundboard in the original hinge pose. Bake key patterns on Low and retain all 88 key positions on Balanced. Preserve the bench and pedal assembly.",
}
ORIGIN = "Bottom centre of the installed envelope, +Y up and +Z display front in glTF."


def dump(value):
    return json.dumps(value,indent=2,ensure_ascii=False)+"\n"


def emit(path, data, check):
    if isinstance(data,str):
        data = data.encode()
    if path.is_file() and path.read_bytes()==data:
        return
    require(not check,f"Stale or missing delivery file: {path.relative_to(ROOT)}")
    path.parent.mkdir(exist_ok=True,parents=True)
    path.write_bytes(data)


def source_record(spec):
    anchor = spec["anchor"]
    new = anchor["source"]=="NEW"
    slug = REFERENCE if new else anchor["asset_id"]
    source_dir = ROOT/"models"/slug
    record = json.loads((source_dir/"metadata"/(slug+".json")).read_text())
    license_bytes = (source_dir/"LICENSE.md").read_bytes()
    licence = record["rights"]
    require("reuse in the owner's projects is authorized" in licence and bool(record["author"]),
            f"Missing owner-project grant or author in {slug}")
    if new:
        credit = [{"credit":"Original procedural fixture geometry, colour atlas and material finishes created for this project."}]
        provenance = {"kind":"NEW","author":AUTHOR,"credit":credit,
                      "method":METHODS[spec["slot"]],"generator":f"models/{spec['slug']}/generate.py",
                      "licence_reference":f"models/{REFERENCE}/LICENSE.md"}
    else:
        require(sha256(license_bytes).hexdigest()==spec["rights_sha256"],f"Rights record changed: {slug}")
        for path,key in ((anchor["source"],"source_sha256"),(spec["source_blend"],"blend_sha256")):
            require(sha256((ROOT/path).read_bytes()).hexdigest()==spec[key],f"Source bytes changed: {path}")
        credit = record["attribution"]
        provenance = {"kind":"derivative","source_slug":slug,"source_glb":anchor["source"],
                      "source_glb_sha256":spec["source_sha256"],"source_blend":spec["source_blend"],
                      "source_blend_sha256":spec["blend_sha256"],"author":record["author"],
                      "licence":licence,"licence_reference":f"models/{slug}/LICENSE.md",
                      "licence_text":license_bytes.decode(),"credit":credit,
                      "source_metadata":f"models/{slug}/metadata/{slug}.json",
                      "source_creation_method":record["creation_method"],
                      "method":METHODS[spec["slot"]]+" Rebuild shared opaque PBR finishes in the assigned store palette and fit the bottom-centred anchor within its installation envelope."}
    provenance.update(generator=f"models/{spec['slug']}/generate.py",
                      editable_source=f"models/{spec['slug']}/sources/{spec['slug']}.blend",
                      licence_text=license_bytes.decode())
    return licence,license_bytes,provenance,credit


def package_model(spec,check):
    slug = spec["slug"]
    folder = ROOT/"models"/slug
    slot = spec["slot"]
    a = spec["anchor"]
    new = a["source"]=="NEW"
    name = a["asset_id"].replace("-"," ").title()
    if not new:
        name += " · "+spec["style"]
    title = a["name"]
    licence,license_bytes,provenance,credit = source_record(spec)
    emit(folder/"LICENSE.md",license_bytes,check)
    reports = json.loads((folder/"reports/khronos.json").read_text())
    preview_path = folder/"reports/previews.json"
    captures = json.loads(preview_path.read_text())
    for receipt in captures:
        for f,digest in {receipt["source"]:receipt["sha256"],**receipt["views"]}.items():
            require(sha256((folder/f).read_bytes()).hexdigest()==digest,f"Stale preview evidence: {slug}/{f}")
    tiers = ["Low","Balanced","Detailed"] if new else ["Low","Balanced"]
    entries,lods = [],{}
    for tier in tiers:
        filename = ("lod1.glb" if tier=="Low" else "optimized.glb" if tier==tiers[-1] else "balanced.glb")
        path = folder/"exports"/filename
        metric = inspect(path,spec,tier)
        report = reports[filename]
        require(report["sha256"]==metric["sha256"] and not report["issues"]["numErrors"],"Khronos report mismatch")
        metric["triangle_cap"] = a["triangles_per_instance"][tier]
        metric["validator"] = {"version":report["validatorVersion"],"errors":report["issues"]["numErrors"],
                               "warnings":report["issues"]["numWarnings"]}
        lods[tier] = {"file":"exports/"+filename,**metric}
        runtime = f"{slot.lower()}-{a['asset_id']}-{tier.lower()}.glb"
        emit(STAGE/runtime,path.read_bytes(),check)
        entries.append(dict(file=runtime,store=slot,brand=spec["brand"],model=slug,
                            source="NEW" if new else a["asset_id"],tier=tier,licence=licence,
                            provenance=provenance,**metric))
    default = lods[tiers[-1]]
    paths = {"glb":default["file"],"source":"sources/"+slug+".blend","preview":"previews/hero.webp",
             "additional_previews":["previews/"+v+".webp" for v in VIEWS]}
    tags = ["mall","interior","GJH",slot,a["asset_id"],"unbranded","metres"]
    metadata = dict(id=slug,name=name,summary=title,description=title+". "+spec["style"]+".",
                    category="Mall Fixtures",tags=tags,status="draft",created="2026-11-18",author=AUTHOR,
                    blender_version="5.1.2",creation_method=provenance["method"],generator="generate.py",
                    paths=paths,origin=ORIGIN,display={"previewRotationY":0,"units":"metres",
                    "up_axis":"Blender +Z / glTF +Y","front_axis":"Blender -Y / glTF +Z",
                    "previewCameraDirection":([-.63,.36,1] if slot=="S15" else
                                              [.42,-.38,1] if slot=="S02" else [.42,.28,1])},
                    root="ASSET_"+slug.replace("-","_"),palette=spec["palette"],node_groups=default["groups"],
                    measured={"glb_bytes":default["bytes"],"triangles":default["triangles"]},lods=lods,
                    rights=licence,licence=licence,attribution=credit,provenance=provenance,
                    accuracy_notes="Unbranded architectural entrance anchor. Catalog review and in-engine placement, lighting and physical-device performance remain pending.")
    emit(folder/"metadata"/(slug+".json"),dump(metadata),check)
    registry = {k:metadata[k] for k in ("id","name","category","tags","description","root")}
    registry.update(file=f"models/{slug}/{paths['glb']}",thumbnail=f"models/{slug}/{paths['preview']}",
                    metadata=f"models/{slug}/metadata/{slug}.json",downloadable=True,license=licence)
    readme = [f"# {name}",f"![{title}](previews/hero.webp)",f"{slot} · {spec['brand']} · {spec['style']}. {title}.",
              ORIGIN," | ".join(f"{tier} {lods[tier]['triangles']:,} triangles" for tier in tiers)+".",
              f"[Editable source]({paths['source']}) · [Generator](generate.py) · [Measurements and provenance](metadata/{slug}.json) · [Rights](LICENSE.md)",
              "[Build instructions and placement contract](../../docs/gjh-v11-interiors-build.md)"]
    emit(folder/"README.md","\n\n".join(readme)+"\n",check)
    return entries,registry


def main(check):
    assets,registry = [],[]
    placements = ["# GJH v11 interior anchors",
                  "Use one GLB for the active tier at each entrance. Model units are metres. All files are self-contained.",
                  PROGRAM["coordinates"],
                  "Create a slot parent with the world translation and yaw below. Attach the GLB at its slot-local translation and yaw with unit scale. Rotations follow the right-hand rule about +Y. Envelopes are design limits before rotation.",
                  "| Store | Anchor | Slot-local XYZ (m) | Local yaw (°) | Parent world XYZ (m) | Parent yaw (°) | Envelope WHD (m) |",
                  "|---|---|---|---:|---|---:|---|"]
    estimates = []
    table = ["| Store | Model | Low tris / bytes | Balanced tris / bytes | Detailed tris / bytes |",
             "|---|---|---:|---:|---:|"]
    for spec in PROGRAM["stores"]:
        entries,item = package_model(spec,check)
        assets.extend(entries)
        registry.append(item)
        a = spec["anchor"]
        slot = spec["slot"]
        placements.append(f"| {slot} {spec['brand']} | {a['asset_id']} | {a['position_m']} | {a['yaw_deg']} | {spec['world_origin_m']} | {spec['yaw_world_deg']} | {a['envelope_whd_m']} |")
        values = [f"{e['triangles']:,} / {e['bytes']:,}" for e in entries]
        model_link = f"[{a['asset_id']}](../models/{spec['slug']}/README.md)"
        table.append("| "+" | ".join([slot,model_link,*values,*(["—"] if len(values)==2 else [])])+" |")
        remaining = spec["shop_low_cap"]-a["triangles_per_instance"]["Low"]*a["count"]
        estimate = remaining+entries[0]["triangles"]*a["count"]
        require(estimate<=PROGRAM["owner_caps"]["Low_store_triangles"],"Shop allocation exceeded")
        estimates.append(estimate)
    low = [a for a in assets if a["tier"]=="Low"]
    total = sum(e["triangles"] for e in low)
    full = sum(estimates)
    require(len(registry)==17 and len(assets)==42 and full<=PROGRAM["owner_caps"]["Low_global_added_triangles"],"Kit budget mismatch")
    expected = {a["file"] for a in assets}
    require(expected=={p.name for p in STAGE.glob("*.glb")},"Unexpected staged files")
    emit(STAGE/"manifest.json",dump(dict(plan_sha256=PROGRAM["plan_sha256"],assets=assets,
         totals={"low_anchor_triangles":total,"low_anchor_bytes":sum(e["bytes"] for e in low),
                 "projected_full_low_triangles":full,"projected_max_per_shop":max(estimates)})),check)
    placement_text = "\n\n".join(placements[:4])+"\n\n"+"\n".join(placements[4:])+"\n"
    emit(STAGE/"README.md",placement_text+"\nRights and transformations accompany each file in [manifest.json](manifest.json).\n",check)
    catalog_path = ROOT/"models/catalog.json"
    original = catalog_path.read_text()
    group = dict(id="gjh-v11-interiors",name="GJH Interior Fixtures",
                 description="Seventeen shop entrance anchors.",assets=registry)
    def locate(group_id):
        # Preserve byte formatting of the gallery's older hand-edited entries.
        match = re.search(r'^    (\{\n      "id": "'+re.escape(group_id)+'")',original,re.MULTILINE)
        if match:
            begin = match.start(1)
            _,end = json.JSONDecoder().raw_decode(original,begin)
            return begin-4,end
        return None
    encoded = indent(dump(group).rstrip(),"    ")
    existing = locate(group["id"])
    if existing:
        begin,end = existing
        updated = original[:begin]+encoded+original[end:]
    else:
        _,end = locate("new-moon-sign")
        updated = original[:end]+",\n"+encoded+original[end:]
    require(sum(g["id"]==group["id"] for g in json.loads(updated)["collections"])==1,"Duplicate catalog collection")
    emit(catalog_path,updated,check)
    doc = ROOT/"docs/gjh-v11-interiors-build.md"
    start,end = "<!-- metrics:start -->","<!-- metrics:end -->"
    before,rest = doc.read_text().split(start)
    _,after = rest.split(end)
    totals = f"Measured Low anchors total **{total:,} triangles**. Substituting them into the 17 complete Phase 1 allocations projects **{full:,} triangles** across all shops and **{max(estimates):,}** for the largest shop. The remaining room geometry is budgeted."
    emit(doc,before+start+"\n\n"+"\n".join(table)+"\n\n"+totals+"\n\n"+end+after,check)
    print(f"{len(registry)} catalog entries, {len(assets)} GLBs, {total} measured Low triangles, {full} projected for full rooms")


if __name__=="__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    main(parser.parse_args().check)
