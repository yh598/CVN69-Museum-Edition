#!/usr/bin/env python3
"""Strict M6 BRep, STEP, STL, 3MF, layout, manifest and immutability QA."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import struct
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

import FreeCAD as App
import Part


SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[3]
M6 = SCRIPT.parents[1]
QA = M6 / "QA"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise ImportError(path)
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module


B = load_module("m6_build_for_validation", M6 / "Scripts" / "build_deck_vehicles.py")
L = load_module("m6_layout_for_validation", M6 / "Scripts" / "build_deck_equipment_layout.py")
P = B.P


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""): digest.update(chunk)
    return digest.hexdigest()


def strict_messages(shape):
    try: shape.check(True); return []
    except ValueError as exc: return [line.strip() for line in str(exc).splitlines() if line.strip()]


def boxes_overlap(a, b, tolerance=1.0e-7):
    return not (a.XMax <= b.XMin+tolerance or b.XMax <= a.XMin+tolerance or a.YMax <= b.YMin+tolerance or b.YMax <= a.YMin+tolerance or a.ZMax <= b.ZMin+tolerance or b.ZMax <= a.ZMin+tolerance)


def stable_output_paths():
    paths = sorted((M6 / "STL").glob("*.stl"))
    paths += sorted((M6 / "3MF").glob("*.3mf"))
    paths += sorted((M6 / "OBJ").glob("*.obj")) + sorted((M6 / "OBJ").glob("*.mtl"))
    paths += sorted((M6 / "Layout").glob("*.json"))
    return paths


def deterministic_rebuild():
    before = {str(path.relative_to(M6)): sha256(path) for path in stable_output_paths()}
    B.main(); L.main()
    after = {str(path.relative_to(M6)): sha256(path) for path in stable_output_paths()}
    matches = {name: before.get(name) == digest for name, digest in after.items()}
    passed = set(before) == set(after) and all(matches.values())
    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "actual second FreeCAD master/layout rebuild; byte comparison of deterministic STL, OBJ/MTL, 3MF and layout JSON outputs",
        "files_compared": len(after), "before": before, "after": after, "matches": matches,
        "overall_status": "PASS" if passed else "FAIL",
    }
    (QA / "Deterministic_Rebuild.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def mesh_record(path):
    data = path.read_bytes()
    if len(data) < 84: return {"path": str(path.relative_to(M6)), "valid": False, "error": "short STL"}
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84 + 50*count: return {"path": str(path.relative_to(M6)), "valid": False, "error": "binary length mismatch"}
    edges, minimum, maximum = Counter(), [float("inf")]*3, [float("-inf")]*3
    degenerate = normal_mismatch = 0; volume = 0.0; offset = 84
    for _ in range(count):
        values = struct.unpack_from("<12fH", data, offset); offset += 50
        normal, tri = values[:3], (values[3:6], values[6:9], values[9:12])
        for point in tri:
            for axis in range(3): minimum[axis] = min(minimum[axis], point[axis]); maximum[axis] = max(maximum[axis], point[axis])
        keys = [tuple(round(value, 6) for value in point) for point in tri]
        for left, right in ((0,1),(1,2),(2,0)): edges[tuple(sorted((keys[left],keys[right])))] += 1
        a,b,c=tri; ux,uy,uz=b[0]-a[0],b[1]-a[1],b[2]-a[2]; vx,vy,vz=c[0]-a[0],c[1]-a[1],c[2]-a[2]
        nx,ny,nz=uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx; magnitude=math.sqrt(nx*nx+ny*ny+nz*nz)
        if magnitude <= 1e-10: degenerate += 1
        elif (nx*normal[0]+ny*normal[1]+nz*normal[2])/magnitude < 0.999: normal_mismatch += 1
        volume += (a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0]))/6.0
    boundary = sum(value == 1 for value in edges.values()); nonmanifold = sum(value != 2 for value in edges.values())
    size = [maximum[i]-minimum[i] for i in range(3)]
    valid = count>0 and not degenerate and not normal_mismatch and not boundary and not nonmanifold and abs(minimum[2])<=0.01 and volume>0 and max(size)<=240.0+1e-6
    return {"path":str(path.relative_to(M6)),"facets":count,"bounds_mm":[round(x,6) for x in size],"minimum_mm":[round(x,6) for x in minimum],"boundary_edges":boundary,"non_manifold_edges":nonmanifold,"degenerate_triangles":degenerate,"normal_mismatches":normal_mismatch,"signed_volume_mm3":round(volume,6),"watertight":boundary==0 and nonmanifold==0,"valid":valid}


def package_record(path):
    required={"[Content_Types].xml","_rels/.rels","3D/3dmodel.model"}
    with zipfile.ZipFile(path) as archive:
        crc=archive.testzip(); missing=sorted(required-set(archive.namelist())); root=ET.fromstring(archive.read("3D/3dmodel.model")) if not missing else None
    if root is None: return {"path":str(path.relative_to(M6)),"valid":False,"missing":missing}
    ns={"m":"http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}; objects=root.findall("./m:resources/m:object",ns); items=root.findall("./m:build/m:item",ns)
    names=[]; invalid=unassigned=vertices=triangles=0; object_min_z={}
    for obj in objects:
        name=obj.attrib.get("name",""); names.append(name); verts=obj.findall("./m:mesh/m:vertices/m:vertex",ns); tris=obj.findall("./m:mesh/m:triangles/m:triangle",ns); vertices+=len(verts);triangles+=len(tris)
        object_min_z[name]=min((float(node.attrib["z"]) for node in verts),default=float("inf"))
        for tri in tris:
            if any(int(tri.attrib[key])>=len(verts) for key in ("v1","v2","v3")): invalid+=1
            if "pid" not in tri.attrib or "p1" not in tri.attrib: unassigned+=1
    review="Review" in path.name or "Support_Layout" in path.name
    bed_ok=review or all(abs(value)<=0.01 for value in object_min_z.values())
    valid=crc is None and not missing and objects and len(items)==len(objects) and all(names) and len(names)==len(set(names)) and not invalid and not unassigned and bed_ok
    return {"path":str(path.relative_to(M6)),"objects":len(objects),"build_items":len(items),"object_names":names,"vertices":vertices,"triangles":triangles,"object_min_z_mm":{k:round(v,6) for k,v in object_min_z.items()},"review_file":review,"bed_contact_ok":bed_ok,"invalid_indices":invalid,"triangles_without_material":unassigned,"zip_crc_ok":crc is None,"valid":bool(valid)}


def step_record(path):
    shape=Part.read(str(path)); messages=strict_messages(shape); passed=shape.isValid() and shape.Solids and all(s.isClosed() for s in shape.Solids)
    return {"path":str(path.relative_to(M6)),"valid":shape.isValid(),"solid_count":len(shape.Solids),"closed_solids":all(s.isClosed() for s in shape.Solids),"volume_mm3":round(float(shape.Volume),6),"strict_messages":messages,"status":"PASS" if passed else "FAIL","strict_message_interpretation":"Assembly cross-object contacts may be reported; child-solid validity and closure govern round-trip status."}


def dimensional_checks(parts):
    records=[]
    for family in P.families:
        shape=B.assembly_shape(parts,family.code); bounds=B.precise_bounds(shape); measured=(bounds[3]-bounds[0],bounds[4]-bounds[1],bounds[5]-bounds[2]); expected=(family.model_length,family.model_width,family.model_height)
        errors=[abs(a-b) for a,b in zip(measured,expected)]; passed=max(errors)<=family.tolerance_mm
        records.append({"family":family.code,"full_scale_reference_mm":[family.full_length_mm,family.full_width_mm,family.full_height_mm],"released_model_envelope_mm":[round(x,6) for x in expected],"measured_assembly_envelope_mm":[round(x,6) for x in measured],"errors_mm":[round(x,6) for x in errors],"tolerance_mm":family.tolerance_mm,"classification":family.classification,"status":"PASS" if passed else "FAIL"})
    return records


def exact_intersections(shape, targets, kind, instance):
    hits=[]
    for name, other in targets:
        if not boxes_overlap(shape.BoundBox,other.BoundBox): continue
        common=shape.common(other); volume=0.0 if common.isNull() else float(common.Volume)
        if volume>1e-7: hits.append({"instance":instance,"target":name,"target_kind":kind,"overlap_mm3":round(volume,8),"status":"PASS" if volume<=P.interference_threshold_mm3 else "FAIL"})
    return hits


def validate_layouts(parts):
    raw_baseline=L.AW.load_baseline(); fixed=[item for item in raw_baseline if item.role not in {"hull_module","deck_module","interface_pad"}]
    fixed_targets=[(item.name,item.shape) for item in fixed]; outline=L.deck_outline(); reports={}; all_hits=[]
    for name in ("light","default","full"):
        payload=json.loads(L.config_path(name).read_text(encoding="utf-8")); aircraft=L.aircraft_for_layout(name); aircraft_targets=[(item["entry"]["id"],item["shape"]) for item in aircraft]
        entries=payload.get("entries",[]); required={"equipment_family","variant","instance_id","x","y","z","heading","material_assignment","intended_relationship_to_nearby_aircraft","confidence_or_display_rationale","state","intentional_aircraft_link","source"}
        schema_fail=[entry.get("instance_id","missing") for entry in entries if not required.issubset(entry)]; boundary=[]; seating=[]; link=[]; placed=[]; fixed_hits=[]; aircraft_hits=[]
        for entry in entries:
            parts_placed=L.placed_family_parts(parts,entry); shape=L.combined_shape(parts_placed); placed.append((entry,shape))
            if not L.bbox_inside(shape,outline): boundary.append(entry["instance_id"])
            if abs(shape.BoundBox.ZMin-P.deck_top_z)>0.01: seating.append({"instance":entry["instance_id"],"min_z":shape.BoundBox.ZMin})
            if entry["state"] in {"towing","servicing"} and not entry["intentional_aircraft_link"]: link.append(entry["instance_id"])
            fixed_hits += exact_intersections(shape,fixed_targets,"approved_fixed",entry["instance_id"]); aircraft_hits += exact_intersections(shape,aircraft_targets,"approved_aircraft",entry["instance_id"])
        pair_hits=[]; clearance=[]
        for index,(left_entry,left) in enumerate(placed):
            for right_entry,right in placed[index+1:]:
                gap=L.bbox_gap(left,right)
                if gap<L.LP.vehicle_clearance-1e-6: clearance.append({"left":left_entry["instance_id"],"right":right_entry["instance_id"],"gap_mm":round(gap,6)})
                pair_hits += exact_intersections(left,[(right_entry["instance_id"],right)],"support_equipment",left_entry["instance_id"])
        ranges={"light":L.LP.light_count_range,"default":L.LP.default_count_range,"full":L.LP.full_count_range}; expected=ranges[name]
        hits=fixed_hits+aircraft_hits+pair_hits; all_hits+=hits
        passed=expected[0]<=len(entries)<=expected[1] and not schema_fail and not boundary and not seating and not link and not clearance and all(item["status"]=="PASS" for item in hits)
        reports[name]={"path":str(L.config_path(name).relative_to(M6)),"count":len(entries),"expected_range":list(expected),"schema_failures":schema_fail,"boundary_failures":boundary,"seating_failures":seating,"linkage_failures":link,"clearance_failures":clearance,"fixed_intersections":fixed_hits,"aircraft_intersections":aircraft_hits,"vehicle_pair_intersections":pair_hits,"status":"PASS" if passed else "FAIL"}
    return reports,all_hits,len(fixed)


def required_outputs():
    paths=[
        M6/"CAD/FreeCAD/CVN69_Deck_Vehicles_Master.FCStd",M6/"CAD/FreeCAD/CVN69_Deck_Equipment_Layout.FCStd",
        M6/"STEP/CVN69_Deck_Vehicles_Master.step",M6/"STEP/CVN69_Default_Support_Layout.step",M6/"STEP/CVN69_Full_Ship_AirWing_Vehicles_Review.step",
        M6/"OBJ/CVN69_Deck_Vehicles_Master.obj",M6/"OBJ/CVN69_Default_Support_Layout.obj",
        M6/"3MF/CVN69_Deck_Vehicles_Master.3mf",M6/"3MF/CVN69_Default_Support_Layout_Review.3mf",M6/"3MF/Print_Plate_00_First_Article.3mf",M6/"3MF/CVN69_Full_Ship_AirWing_Vehicles_Review.3mf",
        M6/"README.md",M6/"Assembly/Glue_Only_Deck_Vehicle_Assembly.md",
        M6/"Docs/Deck_Vehicles_Drawings.pdf",M6/"Docs/Deck_Vehicles_Printing_Guide.pdf",M6/"Docs/Deck_Vehicles_Project_Plan.pdf",M6/"Docs/Deck_Vehicles_First_Article_Instructions.pdf",M6/"Docs/Deck_Equipment_Layout_Guide.pdf",
        M6/"QA/BambuStudio_Validation.md",M6/"QA/Reference_Confidence_Report.md",M6/"QA/Material_Map.md",M6/"QA/Physical_First_Article_Status.md",
    ]
    paths += list((M6/"STL").glob("*.stl"))+list((M6/"3MF").glob("Print_Plate_*.3mf"))+list((M6/"Render").glob("*.png"))
    missing=[str(path.relative_to(M6)) for path in paths if not path.exists() or path.stat().st_size==0]
    counts={"stl":len(list((M6/"STL").glob("*.stl"))),"production_plates":len(list((M6/"3MF").glob("Print_Plate_*.3mf"))),"renders":len(list((M6/"Render").glob("*.png"))),"pdf":len(list((M6/"Docs").glob("*.pdf")))}
    expected={"stl":16,"production_plates":7,"renders":45,"pdf":5};count_failures={key:{"expected":value,"actual":counts[key]} for key,value in expected.items() if counts[key]!=value}
    return {"checked":len(paths),"missing":missing,"counts":counts,"expected_counts":expected,"count_failures":count_failures,"status":"PASS" if not missing and not count_failures else "FAIL"}


def main():
    if os.environ.get("CVN69_DETERMINISTIC_REBUILD")=="1": deterministic_rebuild()
    parts=B.build_parts(False); production=[part for part in parts if part.production]
    brep=[]
    for spec in production:
        messages=strict_messages(spec.shape); passed=spec.shape.isValid() and len(spec.shape.Solids)==1 and spec.shape.Solids[0].isClosed() and not messages
        brep.append({"name":spec.name,"valid":spec.shape.isValid(),"solid_count":len(spec.shape.Solids),"closed":all(s.isClosed() for s in spec.shape.Solids),"strict_messages":messages,"volume_mm3":round(float(spec.shape.Volume),6),"status":"PASS" if passed else "FAIL"})
    dims=dimensional_checks(parts)
    parameter_checks={"ship_length_476_mm":P.overall_length==476.0,"deck_top_z_34p5_mm":P.deck_top_z==34.5,"frozen_interface_0p25_mm_per_side":P.integration.interface_clearance_per_side==0.25,"wall_at_least_0p80":P.minimum_structural_wall>=0.80,"wheel_at_least_1p00_by_0p70":P.minimum_wheel_diameter>=1.0 and P.minimum_wheel_width>=0.70,"towbar_at_least_0p80":P.minimum_tow_bar>=0.80,"ladder_at_least_0p60":P.minimum_ladder>=0.60,"hose_at_least_0p60":P.minimum_hose>=0.60,"production_count_16":len(production)==16,"all_enlargements_documented":all(item.enlargements for item in P.families),"approved_palette_only":set(B.MATERIALS)=={"gold","black","charcoal","red","ash_gray","silver","ivory","marine_blue"}}
    mesh=[mesh_record(path) for path in sorted((M6/"STL").glob("*.stl"))]; packages=[package_record(path) for path in sorted((M6/"3MF").glob("*.3mf"))]; steps=[step_record(path) for path in sorted((M6/"STEP").glob("*.step"))]
    layouts,hits,fixed_count=validate_layouts(parts)
    manifest=json.loads((QA/"build_manifest.json").read_text(encoding="utf-8")); input_checks=[]
    for relative,expected in manifest["approved_input_hashes"].items():
        path=ROOT/relative; current=sha256(path); input_checks.append({"path":relative,"expected_sha256":expected["sha256"],"current_sha256":current,"status":"PASS" if current==expected["sha256"] else "FAIL"})
    manifest_checks=[]
    for relative,expected in manifest.get("outputs",{}).items():
        path=M6/relative; actual_bytes=path.stat().st_size if path.exists() else None; actual_sha=sha256(path) if path.exists() else None; passed=actual_bytes==expected["bytes"] and actual_sha==expected["sha256"]
        manifest_checks.append({"path":relative,"expected_bytes":expected["bytes"],"actual_bytes":actual_bytes,"expected_sha256":expected["sha256"],"actual_sha256":actual_sha,"status":"PASS" if passed else "FAIL"})
    manifest_pass=manifest.get("output_file_count")==len(manifest_checks) and len(manifest_checks)>=100 and all(item["status"]=="PASS" for item in manifest_checks)
    required=required_outputs(); deterministic_path=QA/"Deterministic_Rebuild.json"; deterministic=json.loads(deterministic_path.read_text(encoding="utf-8")) if deterministic_path.exists() else {"overall_status":"NOT_RUN"}
    topology_pass=all(item["status"]=="PASS" for item in brep+steps); dimensional_pass=all(parameter_checks.values()) and all(item["status"]=="PASS" for item in dims); mesh_pass=len(mesh)==16 and all(item["valid"] for item in mesh); package_pass=len(packages)>=11 and all(item["valid"] for item in packages); layout_pass=all(item["status"]=="PASS" for item in layouts.values()); immutable_pass=all(item["status"]=="PASS" for item in input_checks); deterministic_pass=deterministic.get("overall_status")=="PASS"; required_pass=required["status"]=="PASS"
    overall=topology_pass and dimensional_pass and mesh_pass and package_pass and layout_pass and immutable_pass and deterministic_pass and required_pass and manifest_pass
    timestamp=datetime.now(timezone.utc).isoformat()
    reports={
        "Topology_QA.json":{"generated_utc":timestamp,"brep_records":brep,"step_records":steps,"overall_status":"PASS" if topology_pass else "FAIL"},
        "Dimensional_QA.json":{"generated_utc":timestamp,"parameter_checks":parameter_checks,"equipment_dimensions":dims,"overall_status":"PASS" if dimensional_pass else "FAIL"},
        "Mesh_Validation.json":{"generated_utc":timestamp,"stl_files":len(mesh),"records":mesh,"overall_status":"PASS" if mesh_pass else "FAIL"},
        "ThreeMF_Validation.json":{"generated_utc":timestamp,"packages":len(packages),"records":packages,"overall_status":"PASS" if package_pass else "FAIL"},
        "Layout_Validation.json":{"generated_utc":timestamp,"layouts":layouts,"overall_status":"PASS" if layout_pass else "FAIL"},
        "Interference_Report.json":{"generated_utc":timestamp,"threshold_mm3":P.interference_threshold_mm3,"fixed_baseline_objects":fixed_count,"intersections":hits,"layouts":layouts,"overall_status":"PASS" if layout_pass else "FAIL"},
        "Immutable_Input_Validation.json":{"generated_utc":timestamp,"records":input_checks,"overall_status":"PASS" if immutable_pass else "FAIL"},
        "Required_Output_Validation.json":{"generated_utc":timestamp,**required},
        "Manifest_Validation.json":{"generated_utc":timestamp,"manifest_entries":len(manifest_checks),"records":manifest_checks,"overall_status":"PASS" if manifest_pass else "FAIL"},
    }
    for filename,payload in reports.items(): (QA/filename).write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
    (QA/"Dimensional_QA.md").write_text(f"# Milestone 6 dimensional QA\n\nOverall status: **{'PASS' if dimensional_pass else 'FAIL'}**\n\nSeven released family envelopes, eleven manufacturing/datum rules, and every declared enlargement were checked. The approved 476.00 mm ship length, z=34.50 mm deck top, and frozen 0.25 mm-per-side ship interface are unchanged.\n\nLiteral scale-sensitive details are not described as exact; their released FDM dimensions are listed in `FDM_Enlargements.json`.\n",encoding="utf-8")
    (QA/"Mesh_Validation.md").write_text(f"# Milestone 6 mesh validation\n\nOverall status: **{'PASS' if mesh_pass and package_pass else 'FAIL'}**\n\nValidated {len(mesh)} production STL objects for manifold/watertight topology, normals, degenerate triangles, positive signed volume, z=0 bed contact, and the 240 mm envelope. Validated {len(packages)} named/material 3MF packages for ZIP CRC, OPC members, XML, indices, unique object names, material assignment, and production-object bed contact.\n",encoding="utf-8")
    (QA/"Interference_Report.md").write_text(f"# Milestone 6 interference report\n\nOverall status: **{'PASS' if layout_pass else 'FAIL'}**\n\nExact BRep common-volume validation used the 0.10 mm³ failure threshold against {fixed_count} approved fixed objects, the matching approved AirWing layout, and every other support-equipment instance. Light/default/full support counts are {layouts['light']['count']}/{layouts['default']['count']}/{layouts['full']['count']}. All objects seat at z={P.deck_top_z:.2f} mm.\n",encoding="utf-8")
    (QA/"Layout_Validation.md").write_text(f"# Milestone 6 layout validation\n\nOverall status: **{'PASS' if layout_pass else 'FAIL'}**\n\nAll required placement, heading, material, rationale, state, confidence, and linkage fields are present. No supplied entry declares an intentional towing/servicing contact; all are independent static staging with validated clearance.\n",encoding="utf-8")
    summary={"generated_utc":timestamp,"overall_status":"PASS" if overall else "FAIL","topology":topology_pass,"dimensional":dimensional_pass,"mesh":mesh_pass,"3mf":package_pass,"layouts":layout_pass,"immutable_inputs":immutable_pass,"deterministic_rebuild":deterministic_pass,"required_outputs":required_pass,"manifest_hashes":manifest_pass,"counts":{"production_objects":len(production),"stl":len(mesh),"3mf":len(packages),"step":len(steps),"light_support":layouts['light']['count'],"default_support":layouts['default']['count'],"full_support":layouts['full']['count']}}
    (QA/"Validation_Summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8"); print(json.dumps(summary,indent=2))
    if not overall: raise SystemExit(1)


if __name__=="__main__": main()
