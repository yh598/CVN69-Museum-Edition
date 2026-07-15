#!/usr/bin/env python3
"""Generate neutral M6 family, plate, layout and integrated review renders."""

from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle


SCRIPT=Path(__file__).resolve();ROOT=SCRIPT.parents[3];PROJECT=ROOT/"Project";M6=PROJECT/"DeckVehicles";RENDER=M6/"Render";RENDER.mkdir(parents=True,exist_ok=True)


def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


R=load_module("m6_render_utilities",PROJECT/"Island/Scripts/render_island.py")
sys.path.insert(0,str(M6/"CAD/Python"));from deck_vehicle_parameters import make_parameters  # noqa:E402
P=make_parameters()
MATERIAL_KEYS=("gold","black","charcoal","red","ash_gray","silver","ivory","marine_blue")
COLORS={"gold":np.array([0.84,0.66,0.21]),"black":np.array([0.08,0.09,0.10]),"charcoal":np.array([0.20,0.22,0.24]),"red":np.array([0.72,0.22,0.20]),"ash_gray":np.array([0.59,0.60,0.56]),"silver":np.array([0.68,0.71,0.73]),"ivory":np.array([0.92,0.90,0.84]),"marine_blue":np.array([0.19,0.36,0.45]),"blue_grey":np.array([0.45,0.51,0.55]),"ivory_white":np.array([0.92,0.90,0.84]),"silk_silver":np.array([0.68,0.71,0.73]),"basic_black":np.array([0.08,0.09,0.10]),"deck_charcoal":np.array([0.20,0.22,0.24])}
R.COLORS=COLORS;R.LABELS={key:key.replace("_"," ").title() for key in COLORS}


def combine_many(models):
    result=models[0]
    for model in models[1:]: result=R.combine(result,model)
    return result


def filter_model(model,prefixes):
    vertices,faces=model; return vertices,[face for face in faces if any(face[2].startswith(prefix) for prefix in prefixes)]


def assembled_family_model(model,tokens):
    names=sorted({face[2] for face in model[1] if any(token in face[2] for token in tokens)})
    if not names: return filter_model(model,tokens)
    instance=names[0].split("_",1)[0]
    return filter_model(model,(instance+"_",))


def load_3mf(path):
    vertices=[];faces=[];keys=list(MATERIAL_KEYS);ns={"m":"http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    with zipfile.ZipFile(path) as archive:root=ET.fromstring(archive.read("3D/3dmodel.model"))
    for obj in root.findall("./m:resources/m:object",ns):
        name=obj.attrib.get("name","unnamed");mesh=obj.find("./m:mesh",ns);local=[(float(node.attrib["x"]),float(node.attrib["y"]),float(node.attrib["z"])) for node in mesh.findall("./m:vertices/m:vertex",ns)];offset=len(vertices);vertices.extend(local)
        for tri in mesh.findall("./m:triangles/m:triangle",ns):faces.append((tuple(offset+int(tri.attrib[key]) for key in ("v1","v2","v3")),keys[int(tri.attrib.get("p1","0"))],name))
    return np.asarray(vertices),faces


def ship_top_annotations(axis):
    axis.set_xlabel("authoritative x [mm] — bow 0 to stern 476");axis.set_ylabel("port (−y) / starboard (+y) [mm]");axis.text(2,46,"BOW",fontsize=7.5,weight="bold");axis.text(474,46,"STERN",fontsize=7.5,weight="bold",ha="right")


def layout_map(name,output,title):
    support=json.loads((M6/"Layout"/{"light":"light_support_layout.json","default":"default_support_layout.json","full":"full_support_layout.json"}[name]).read_text(encoding="utf-8"));air=json.loads((PROJECT/"AirWing/Layout"/{"light":"light_deck_layout.json","default":"default_deployment_layout.json","full":"full_deck_layout.json"}[name]).read_text(encoding="utf-8"));outline=[(P.overall_length-x,y) for x,y in P.integration.deck.outline_points]
    fig,axis=plt.subplots(figsize=(15,5.2),dpi=220,facecolor="#F2F0EA");axis.set_facecolor("#E8E7E2");axis.add_patch(Polygon(outline,closed=True,facecolor="#34383C",edgecolor="#1F272B",linewidth=.8))
    for entry in air["entries"]:axis.scatter([entry["x"]],[entry["y"]],s=22,c=[COLORS["blue_grey"]],edgecolors="#ECE8D9",linewidths=.3,zorder=3)
    cmap={"STT49":"gold","P25A":"gold","MSU200":"ash_gray","TOWBAR":"gold","LADDER":"gold","CHOCK":"gold","EXT":"red"}
    for entry in support["entries"]:axis.scatter([entry["x"]],[entry["y"]],s=18,c=[COLORS[cmap[entry["equipment_family"]]]],edgecolors="#151719",linewidths=.3,zorder=4,marker="s")
    x0,y0,x1,y1=P.island_bounds;axis.add_patch(Rectangle((x0,y0),x1-x0,y1-y0,facecolor="#969890",edgecolor="#ECE8D9",linewidth=.5));axis.set_xlim(-5,481);axis.set_ylim(-48,48);axis.set_aspect("equal");axis.grid(True,color="#BEC2C1",linewidth=.25);axis.set_xlabel("x [mm] bow → stern");axis.set_ylabel("y [mm]");fig.suptitle(title,x=.055,y=.96,ha="left",fontsize=15,weight="bold",color="#20272A");fig.text(.057,.89,f"{len(air['entries'])} APPROVED AIRCRAFT · {len(support['entries'])} SUPPORT INSTANCES · SQUARES = EQUIPMENT",fontsize=8,color="#58646A");fig.subplots_adjust(left=.055,right=.98,top=.82,bottom=.18);fig.savefig(output,facecolor=fig.get_facecolor());plt.close(fig)


def main():
    for path in RENDER.glob("*.png"):path.unlink()
    master=R.load_obj(M6/"OBJ/CVN69_Deck_Vehicles_Master.obj");support=R.load_obj(M6/"OBJ/CVN69_Default_Support_Layout.obj")
    family_prefixes={"STT49":("Tow_Tractor",),"P25A":("P25A",),"MSU200":("MSU200",),"TOWBAR":("Aircraft_Tow_Bar",),"LADDER":("Maintenance_Ladder",),"CHOCK":("Wheel_Chock",),"EXT":("Firefighting_Extinguisher",)};outputs=[]
    for code,prefixes in family_prefixes.items():
        model=assembled_family_model(support,prefixes);exploded=filter_model(master,prefixes);label=P.family(code).name.upper()
        for suffix,fn in (("Front_Isometric",lambda p,m=model,t=label:R.projected_render(m[0],m[1],p,t,"ASSEMBLED PARAMETRIC FAMILY · FILAMENT-LIKE COLORS",-135,28)),("Top",lambda p,m=model,t=label:R.orthographic_render(m[0],m[1],p,t+" · TOP","1:700 RELEASED FDM GEOMETRY",(0,1),2,False,None,None,False)),("Side",lambda p,m=model,t=label:R.orthographic_render(m[0],m[1],p,t+" · SIDE","DIMENSIONAL / PRINTABILITY REVIEW",(0,2),1,False,None,None,False))):
            path=RENDER/f"Family_{code}_{suffix}.png";fn(path);outputs.append(path)
        if code in {"STT49","P25A","MSU200","EXT"}:
            path=RENDER/f"Exploded_{code}.png";R.projected_render(exploded[0],exploded[1],path,label+" · PART BREAKDOWN","GLUE-ONLY COLOR-SEPARATED OBJECTS",-125,32);outputs.append(path)
    for plate_path in sorted((M6/"3MF").glob("Print_Plate_*.3mf")):
        model=load_3mf(plate_path);path=RENDER/f"{plate_path.stem}.png";R.orthographic_render(model[0],model[1],path,plate_path.stem.replace("_"," ").upper(),"NAMED OBJECTS · SUPPORT-FREE · 0.12/0.16 MM REAL-SLICE PASS",(0,1),2,False,None,None,False);outputs.append(path)
    path=RENDER/"Default_Support_Layout_Top.png";R.orthographic_render(support[0],support[1],path,"DEFAULT SUPPORT LAYOUT · TOP","24 STATIC SUPPORT INSTANCES · APPROVED DECK DATUM",(0,1),2,False,((0,476),(-45,45)),ship_top_annotations,True);outputs.append(path)
    path=RENDER/"Default_Support_Layout_Bow_Isometric.png";R.projected_render(support[0],support[1],path,"DEFAULT SUPPORT LAYOUT · BOW ISOMETRIC","NO AIRCRAFT OR SHIP PARTS DUPLICATED IN PRODUCTION FOLDERS",-145,28,full_ship=True);outputs.append(path)
    integration=R.load_obj(PROJECT/"Integration/OBJ/CVN69_Hull_Deck_Assembly.obj");island=R.load_obj(PROJECT/"Island/OBJ/CVN69_Island_Assembly.obj");weapons=R.load_obj(PROJECT/"WeaponsDeckEdge/OBJ/CVN69_Weapons_DeckEdge_Assembly.obj");aircraft=R.load_obj(PROJECT/"AirWing/OBJ/CVN69_AirWing_Default_Layout.obj");full=combine_many((integration,island,weapons,aircraft,support));fv,ff=full
    views=(("Default_Combined_Aircraft_Vehicles_Top.png","DEFAULT AIRCRAFT + SUPPORT · TOP","NON-PRODUCTION INTEGRATED REVIEW",(0,1),2,False,((-5,481),(-49,49)),ship_top_annotations),("Default_Combined_Port.png","DEFAULT AIRCRAFT + SUPPORT · PORT","APPROVED M1–M5 + NEW M6 REVIEW",(0,2),1,True,((-5,481),(-7,84)),R.ship_side_annotations),("Default_Combined_Starboard.png","DEFAULT AIRCRAFT + SUPPORT · STARBOARD","NO OCEAN BASE · NO CREW · NO EFFECTS",(0,2),1,False,((-5,481),(-7,84)),R.ship_side_annotations),("Closeup_Bow_Catapult_Support.png","BOW CATAPULT SUPPORT CLOSE-UP","STATIC EQUIPMENT CLEAR OF APPROVED TRACKS",(0,1),2,False,((0,150),(-42,42)),ship_top_annotations),("Closeup_Island_Side_Support.png","ISLAND-SIDE SUPPORT CLOSE-UP","VALIDATED CLEARANCE TO ISLAND / WEAPONS",(0,1),2,False,((310,395),(-42,42)),ship_top_annotations),("Closeup_Aft_Landing_Area_Support.png","AFT LANDING-AREA SUPPORT CLOSE-UP","STATIC DISPLAY CHOICES · NO ACTIVE PATH BLOCKAGE",(0,1),2,False,((380,476),(-42,42)),ship_top_annotations),("Tow_Tractor_Aircraft_Vignette.png","TOW-TRACTOR / AIRCRAFT VIGNETTE","INDEPENDENT STAGING · NO PHYSICAL FUSION",(0,1),2,False,((15,175),(-35,35)),ship_top_annotations),("Firefighting_Equipment_Vignette.png","FIREFIGHTING EQUIPMENT VIGNETTE","P-25A + PORTABLE GROUPS · STATIC DISPLAY",(0,1),2,False,((15,175),(-35,35)),ship_top_annotations))
    for filename,title,subtitle,axes,sort_axis,reverse,limits,annotations in views:
        path=RENDER/filename;R.orthographic_render(fv,ff,path,title,subtitle,axes,sort_axis,reverse,limits,annotations,True);outputs.append(path)
    for name,title in (("light","LIGHT AIRCRAFT + SUPPORT REVIEW"),("default","DEFAULT AIRCRAFT + SUPPORT REVIEW"),("full","FULL AIRCRAFT + SUPPORT REVIEW")):
        path=RENDER/f"Layout_{name.title()}_Combined.png";layout_map(name,path,title);outputs.append(path)
    print(json.dumps({"status":"ok","renders":len(outputs),"outputs":[str(path.relative_to(M6)) for path in outputs]},indent=2))


if __name__=="__main__":main()
