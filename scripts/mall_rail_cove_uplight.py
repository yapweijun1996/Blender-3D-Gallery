"""Metre-scale profile geometry for the mall track, cove and in-ground luminaires."""
import math
import bpy
from mathutils import Vector


def material(name, rgb, metal=0.0, rough=.4, glow=0.0, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    rgba = tuple(rgb) + (1,)
    mat.diffuse_color = tuple(rgb) + (alpha,)
    p = mat.node_tree.nodes.get("Principled BSDF")
    for key, value in {"Base Color": rgba, "Metallic": metal, "Roughness": rough,
                       "Emission Color": rgba, "Emission Strength": glow, "Alpha": alpha}.items():
        p.inputs[key].default_value = value
    return mat


def root(name):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_size = .01
    return obj


def mesh(name, parent, mat, points, faces):
    data = bpy.data.meshes.new(name)
    data.from_pydata(points, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    if mat:
        data.materials.append(mat)
    return obj


def along(name, parent, mat, x0, x1, yz):
    # The section walks counterclockwise as seen from +X. End faces are square for butt joints.
    winding = sum(a*d-b*c for (a,b),(c,d) in zip(yz,yz[1:]+yz[:1]))
    yz = yz if winding > 0 else list(reversed(yz))
    n = len(yz)
    pts = [(x,y,z) for x in (x0,x1) for y,z in yz]
    faces = [tuple(reversed(range(n))),tuple(range(n,n*2))]
    faces += [(i,(i+1)%n,n+(i+1)%n,n+i) for i in range(n)]
    return mesh(name,parent,mat,pts,faces)


def block(name,parent,mat,x0,x1,y0,y1,z0,z1,bevel=0):
    obj = along(name,parent,mat,x0,x1,[(y0,z0),(y1,z0),(y1,z1),(y0,z1)])
    if bevel:
        mod = obj.modifiers.new("Edge breaks", "BEVEL")
        mod.width = bevel
        mod.segments = 1
        obj.modifiers.new("Planar normals", "WEIGHTED_NORMAL")
    return obj


def turned(name,parent,mat,profile,steps,center=(0,0,0),angle=0,smooth=True,stagger=0):
    # Ordered perimeter in radius/height. A true pole has one vertex.
    pts, rings, faces = [], [], []
    for row,(r,z) in enumerate(profile):
        ring = []
        for i in range(steps if r else 1):
            a = math.tau*(i+(stagger if row%2 else 0))/steps+angle
            ring.append(len(pts))
            pts.append((r*math.cos(a),r*math.sin(a),z))
        rings.append(ring)
    for a,b in zip(rings,rings[1:]+rings[:1]):
        for i in range(steps):
            j=(i+1)%steps
            if len(a)==1 and len(b)>1:
                faces.append((a[0],b[j],b[i]))
            elif len(b)==1 and len(a)>1:
                faces.append((a[i],a[j],b[0]))
            elif len(a)>1 and len(b)>1:
                faces.append((a[i],a[j],b[j],b[i]))
    obj = mesh(name,parent,mat,pts,faces)
    obj.location = center
    if smooth:
        obj.data.polygons.foreach_set("use_smooth",[True]*len(faces))
        obj.data.set_sharp_from_angle(angle=math.radians(38))
    return obj


def pin(name,parent,mat,radius,z0,z1,n,center=(0,0,0)):
    return turned(name,parent,mat,[(0,z0),(radius,z0),(radius,z1),(0,z1)],n,center)


def rail(lod):
    base=root("ASSET_MallTrackLightRail")
    coat=material("Rail • basalt powdercoat",(.080,.100,.113),.51,.31)
    black=material("Continuous dielectric carrier",(.022,.030,.030),.07,.42)
    copper=material("Brushed copper contacts",(.60,.32,.115),.8,.3)
    bare=material("Satin countersink",(.43,.47,.48),.8,.32)
    # Primary casting matches the adapter dimensions of the existing spotlight's 360 mm rail.
    channel=along("Extrusion_1800",base,coat,-.8997,.8997,[
        (-.0185,0),(.0185,0),(.0201,-.0016),(.0201,-.0230),(.0191,-.024),
        (.0087,-.024),(.0087,-.021),(.0153,-.021),(.0153,-.005),
        (-.0153,-.005),(-.0153,-.021),(-.0087,-.021),(-.0087,-.024),
        (-.0191,-.024),(-.0201,-.023),(-.0201,-.0016)])
    # Four actual mounting bores through the ceiling crown. Recesses open toward the installer.
    for i,x in enumerate([-.76,-.26,.26,.76],1):
        cutter=turned(f"Cutter_{i}",base,None,[(0,-.01),(.0065,-.01),(.0065,-.0050),
            (.0036,-.0020),(.0036,.004),(0,.004)],18 if not lod else 12,(x,0,0),angle=.16,smooth=False)
        modifier=channel.modifiers.new("Countersunk mounting hole","BOOLEAN")
        modifier.operation='DIFFERENCE'
        modifier.solver='EXACT'
        modifier.object=cutter
        bpy.context.view_layer.objects.active=channel
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        bpy.data.objects.remove(cutter,do_unlink=True)
    for sign,side in [(-1,'Front'),(1,'Back')]:
        # The live-looking inserts are visual only. Clear central throat is 17.4 mm.
        def flip(coords):
            return [(sign*y,z) for y,z in coords]
        along("Insulator_"+side,base,black,-.8997,.8997,flip([(.0095,-.005),(.0155,-.005),(.0155,-.014),
            (.0095,-.014),(.0095,-.012),(.0125,-.012),(.0125,-.008),(.0095,-.008)]))
        along("Contact_"+side,base,copper,-.8997,.8997,flip([(.0088,-.0116),(.0126,-.0116),
            (.0126,-.0084),(.0094,-.0084),(.0088,-.0090)]))
        if not lod:
            # Rib and reference stations on the inside return, clear of the adapter throat.
            along("Guide_Rib_"+side,base,black,-.8997,.8997,flip([(.0161,-.02432),(.0177,-.02432),
                (.0174,-.02375),(.0165,-.02375)]))
            for i,x in enumerate([-.6,-.3,0,.3,.6]):
                along(f"Station_{side}_{i+1}",base,bare,x-.002,x+.002,
                    flip([(.018,-.02412),(.0189,-.02412),(.0189,-.02392),(.018,-.02392)]))
    key=material("Nickel splice key",(.42,.46,.45),.72,.30)
    block("Keeper_Inside_Crown",base,key,.861,.885,-.0075,.0075,-.0071,-.0048)
    block("Splice_Overhang",base,key,.875,.918,-.0067,.0067,-.0081,-.0055,.0003)
    return base


def cove(lod):
    base=root("ASSET_MallCoveLedStrip")
    pearl=material("Celadon enamel shielding",(.115,.201,.175),.36,.32)
    ceramic=material("Porcelain chip packages",(.73,.69,.58),.04,.39)
    aluminium=material("Extruded aluminium",(.35,.395,.41),.83,.29)
    gasket=material("Graphite gasket and terminals",(.041,.049,.050),.16,.43)
    board=material("Sage flex circuit",(.075,.178,.132),.30,.45)
    brass=material("Warm solder lands",(.50,.31,.096),.68,.31)
    diode=material("Warm segmented diode ribbon",(1,.66,.278),.03,.35,1.4)
    opal=material("Opal diffusion blade",(.85,.73,.46),.01,.28,.12,.49)
    base['mount']='Rear shelf rests on the cove ledge at Z=0; tall fascia faces -Y.'
    along("Cove_Fascia_And_Trough",base,pearl,-1,1,[(-.065,0),(.064,0),(.065,.001),
        (.065,.023),(.062,.023),(.060,.019),(.060,.005),(-.058,.005),
        (-.058,.059),(-.053,.064),(-.053,.070),(-.060,.071),(-.065,.066)])
    along("Shield_Upper_Edge",base,aluminium,-1,1,[(-.0651,.0635),(-.0651,.0668),
        (-.0603,.0714),(-.055,.0714),(-.055,.0708),(-.0597,.0708),(-.0646,.0663),(-.0646,.0635)])
    # A shallow wedge aims the tape toward the rear wall. Build in this local tape plane.
    along("Angled_Heat_Sink",base,aluminium,-.989,.989,[(-.044,.005),(.041,.005),
        (.041,.014),(.035,.016),(-.032,.042),(-.044,.042)])
    channel=root("Tilted_Diffuser_And_Tape")
    channel.parent=base
    channel.location=(0,-.001,.030)
    channel.rotation_euler.x=math.radians(-21.2)
    for sign,name in [(-1,"Forward"),(1,"Rear")]:
        y=sign*.019
        along("Diffuser_Clip_"+name,channel,aluminium,-.980,.980,[(y-.0014,-.002),(y+.0014,-.002),
            (y+.0014,.009),(y+.0007,.0108),(y-.0014,.009)])
    block("Circuit_Ribbon",channel,board,-.967,.967,-.010,.010,-.0001,.0014)
    if lod:
        block("Linear_Emitter",channel,diode,-.942,.942,-.0036,.0036,.0014,.0033)
    else:
        for i in range(40):
            x=-.9225+i*.0473
            block(f"Ceramic_Diode_{i:02}",channel,ceramic,x-.0075,x+.0075,-.005,.005,.0014,.0036,.00055)
            block(f"Phosphor_{i:02}",channel,diode,x-.0058,x+.0058,-.0032,.0032,.00355,.00405,.00018)
        for i in range(8):
            x=-.83+i*.237
            for s in (-1,1):
                block(f"Solder_Pad_{i}_{s}",channel,brass,x-.0042,x+.0042,s*.007-.001,s*.007+.001,.0014,.00175)
    # Two snap-on optical covers leave a screw-terminal service bay exposed at either end.
    section=[(-.018,.0078),(-.015,.0108),(0,.0131),(.015,.0108),(.018,.0078),
             (.018,.0092),(.015,.0122),(0,.0146),(-.015,.0122),(-.018,.0092)]
    for i,(x0,x1) in enumerate([(-.949,-.002),(.002,.949)]):
        along("Diffuser_Length_"+str(i+1),channel,opal,x0,x1,section)
    for sign in [-1,1]:
        x=sign*.966
        block("Feed_Clamp_"+str(sign),channel,gasket,x-.0105,x+.0105,-.011,.011,.0014,.010,.001)
        if not lod:
            for y in [-.005,.005]:
                pin(f"Terminal_{sign}_{y}",channel,brass,.0027,.0097,.0105,10,(x,y,0))
    return base


def floor(lod):
    base=root("ASSET_MallFloorUplight")
    steel=material("Radially machined stainless",(.48,.51,.51),.86,.27)
    body=material("Cast basalt housing",(.050,.061,.068),.53,.38)
    rubber=material("Compression gasket",(.018,.023,.024),.08,.46)
    silver=material("Hammered optical aluminium",(.65,.72,.72),.89,.23)
    gold=material("Amber phosphor",(.99,.63,.24),.04,.33,1.45)
    glass=material("Pale protective glazing",(.66,.82,.81),.08,.16,.0,.12)
    n=24 if lod else 64
    base['mount']='Ground datum z=0 is the underside of the top flange.'
    turned("Heat_Sink_Pot",base,body,[(.064,-.112),(.076,-.106),(.087,-.085),
        (.0885,-.028),(.0885,-.012),(.092,-.009),(.092,-.001),(.080,-.001),
        (.079,-.011),(.076,-.080),(.060,-.099),(0,-.099),(0,-.112)],n)
    # Below-grade ribs are solid and join the housing along their full depth.
    for i in range(8 if lod else 16):
        a=math.tau*i/(8 if lod else 16)
        rib=along(f"Cooling_Web_{i:02}",base,body,-.0019,.0019,[(.0758,-.105),(.080,-.103),
            (.0925,-.085),(.0925,-.033),(.0894,-.028),(.0874,-.028),(.0865,-.084)])
        rib.rotation_euler.z=a
    turned("Ground_Flange",base,steel,[(.076,-.0055),(.100,-.0055),(.100,0),
        (.1075,0),(.108,.0007),(.108,.0021),(.1067,.003),(.0816,.003),
        (.0794,.0019),(.0764,.0015)],n)
    turned("Window_Gasket",base,rubber,[(.0745,-.0052),(.0809,-.0052),(.0809,.0017),
        (.0798,.0021),(.0758,.0021),(.0745,.0001)],n)
    turned("Recessed_Glass",base,glass,[(0,-.0014),(.0765,-.0014),(.0773,-.0008),
        (.0773,.0002),(.0764,.00075),(0,.00075)],n)
    turned("Deep_Faceted_Reflector",base,silver,list(reversed([(.017,-.069),(.023,-.066),(.038,-.058),
        (.054,-.044),(.067,-.027),(.0752,-.010),(.077,-.0048),(.079,-.0055),
        (.077,-.013),(.068,-.031),(.056,-.048),(.040,-.062),(.022,-.071),(.017,-.071)])),
        12 if lod else 32,smooth=False,stagger=.35)
    turned("Optic_Bed",base,steel,[(0,-.074),(.021,-.074),(.021,-.0687),(.020,-.068),(0,-.068)],12 if lod else 24)
    for i in range(7):
        a=math.tau*(i-1)/6
        c=(0,0,0) if i==0 else (.0102*math.cos(a),.0102*math.sin(a),0)
        if lod:
            pin("Emitter_"+str(i+1),base,gold,.0044,-.0685,-.0659,8,c)
        else:
            turned("Emitter_"+str(i+1),base,gold,[(0,-.0685),(.0039,-.0685),(.0046,-.0673),
                (.0044,-.0664),(.002,-.0659),(0,-.0659)],16,c)
    for i in range(6):
        a=math.tau*i/6+math.pi/6
        x,y=.095*math.cos(a),.095*math.sin(a)
        if not lod:
            pin("Black_Fastener_Seat_"+str(i+1),base,rubber,.00565,.0024,.00315,24,(x,y,0))
        turned("Inset_Hex_Fastener_"+str(i+1),base,steel,[(0,.0029),(.0044,.0029),(.0045,.00345),
            (.0022,.00345),(.00195,.00305),(0,.00305)],6,(x,y,0),angle=a+.1,smooth=False)
    if not lod:
        for name,r in [("Outer_Turn_Line",.1042),("Inner_Turn_Line",.0843)]:
            turned(name,base,steel,[(r-.00018,.00298),(r+.00018,.00298),(r+.00017,.00314),
                (r-.00014,.00317)],n)
    gland=root("Side_Entry_Gland")
    gland.parent=base
    gland.location=(.078,0,-.071)
    gland.rotation_euler.y=math.pi/2
    turned("Conduit_Boss",gland,body,[(0,0),(.0135,0),(.012,.014),(.0106,.017),(0,.017)],18)
    turned("Gland_Hex_Nut",gland,steel,[(0,.015),(.0119,.015),(.0125,.016),
        (.0125,.022),(.0118,.023),(0,.023)],6,smooth=False)
    turned("Strain_Relief",gland,rubber,[(0,.021),(.0098,.021),(.0098,.026),
        (.0084,.027),(.0084,.030),(.009,.031),(.0085,.033),(.0065,.034),
        (.0065,.039),(.0058,.040),(0,.040)],12 if lod else 24)
    return base
