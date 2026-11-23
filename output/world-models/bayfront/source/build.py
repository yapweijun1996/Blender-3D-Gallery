"""Build and stage the Bayfront kit, using Blender Z-up until GLB export."""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT / ".qa"
PALETTE = {
    "paint": (0xc8ccd0, .58, 0),
    "glass": (0xa3cbd2, .17, 0),
    "window": (0x6b9aa3, .21, .05),
    "wall": (0xc8cbc5, .60, .08),
    "roof": (0xd1d8d7, .53, .15),
    "concrete": (0x777d7e, .82, 0),
    "metal": (0xadb4b6, .36, .62),
    "chrome": (0xc4c9c7, .26, .74),
    "trim": (0x303b40, .56, .28),
    "stone": (0xb5b9b5, .44, .05),
    "light": (0xf0faf5, .34, 0),
    "lamp_emissive": (0xd7ffed, .32, 0),
    "rubber": (0x25282a, .89, 0),
    "plate": (0xffffff, .59, 0),
}
GOLD, BLUE = 0xefa912, 0x1478c0
TEAL, DARK = 0x006c6a, 0x263035
GROUT, TACTILE = 0x8a908e, 0xdcb74b


def linear(hex_value):
    srgb = [(hex_value >> shift & 255) / 255 for shift in (16, 8, 0)]
    return tuple(c / 12.92 if c < .04045 else ((c + .055) / 1.055) ** 2.4 for c in srgb)


def make_materials(atlas):
    materials = {}
    for key, (hex_value, roughness, metallic) in PALETTE.items():
        mat = bpy.data.materials.new(key)
        mat.use_nodes = True
        mat.diffuse_color = (*linear(hex_value), 1)
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        shader = nodes.get("Principled BSDF")
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
        tint = nodes.new("ShaderNodeVertexColor")
        tint.layer_name = "SurfaceColor"
        links.new(tint.outputs["Color"], shader.inputs["Base Color"])
        if key in {"glass", "window"}:
            mat.surface_render_method = 'BLENDED'
            shader.inputs["Alpha"].default_value = .30 if key == "glass" else .44
        if key in {"light", "lamp_emissive"}:
            links.new(tint.outputs["Color"], shader.inputs["Emission Color"])
            shader.inputs["Emission Strength"].default_value = 1.4
        if key == "plate":
            texture = nodes.new("ShaderNodeTexImage")
            texture.image = bpy.data.images.load(str(atlas))
            links.new(texture.outputs["Color"], shader.inputs["Base Color"])
        materials[key] = mat
    return materials


class Part:
    def __init__(self, name):
        self.name = name
        self.vertices, self.faces, self.surfaces = [], [], []

    def polygon(self, points, material, color=None, uv=None):
        start = len(self.vertices)
        self.vertices.extend(points)
        self.faces.append(tuple(range(start, start + len(points))))
        self.surfaces.append((material, color, uv))

    def prism(self, loops, material, color=None):
        bottom, top = loops
        self.polygon(bottom[::-1], material, color)
        self.polygon(top, material, color)
        for i in range(len(bottom)):
            j = (i + 1) % len(bottom)
            self.polygon((bottom[i], bottom[j], top[j], top[i]), material, color)

    def box(self, x, y, z, dx, dy, dz, material, color=None, chamfer=0):
        a, b, c, d = x-dx/2, x+dx/2, y-dy/2, y+dy/2
        k = chamfer
        outline = [(a,c),(b,c),(b,d),(a,d)] if not k else [
            (a+k,c),(b-k,c),(b,c+k),(b,d-k),(b-k,d),(a+k,d),(a,d-k),(a,c+k)]
        self.prism([[(u,v,z+h) for u,v in outline] for h in (-dz/2,dz/2)], material, color)

    def sheet(self, x0, x1, y0, y1, z, material, color=None, down=False):
        points = [(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)]
        self.polygon(points[::-1] if down else points, material, color)

    def pane(self, a, b, z0, z1, material="glass", color=None):
        self.polygon(((a[0],a[1],z0),(b[0],b[1],z0),(b[0],b[1],z1),(a[0],a[1],z1)), material, color)

    def beam(self, a, b, width, thickness, material, color=None, across=(0,1,0)):
        a, b = Vector(a), Vector(b)
        along, side = (b-a).normalized(), Vector(across).normalized()
        up = along.cross(side).normalized()
        side = up.cross(along).normalized()
        end = []
        for base in (a,b):
            end.append([tuple(base + s*width/2*side + u*thickness/2*up)
                        for s,u in ((-1,-1),(1,-1),(1,1),(-1,1))])
        self.prism(end, material, color)

    def cylinder(self, x, y, z, radius, height, material, color=None, segments=12):
        self.prism([[(x+radius*math.cos(2*math.pi*i/segments),
                      y+radius*math.sin(2*math.pi*i/segments), z+offset)
                     for i in range(segments)] for offset in (-height/2,height/2)], material, color)

    def sign(self, x, y, z, width, height, row, side=-1):
        self.box(x,y,z,width+.07,.08,height+.07,"trim",0x223036)
        low, high = (row*128+3)/1024, ((row+1)*128-3)/1024
        left, right = x+side*width/2, x-side*width/2
        position = y+side*.041
        self.polygon(
            [(left,position,z-height/2),(right,position,z-height/2),
             (right,position,z+height/2),(left,position,z+height/2)],
            "plate", uv=((.003,low),(.997,low),(.997,high),(.003,high)))

    def finish(self, materials):
        if not self.faces:
            return
        mesh = bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        used = list(dict.fromkeys(surface[0] for surface in self.surfaces))
        for name in used:
            mesh.materials.append(materials[name])
        colors = mesh.color_attributes.new(name="SurfaceColor", type="FLOAT_COLOR", domain="CORNER")
        mesh.color_attributes.active_color = colors
        uv_data = mesh.uv_layers.new(name="UVMap").data if "plate" in used else None
        for face, (material, color, uv) in zip(mesh.polygons,self.surfaces):
            face.material_index = used.index(material)
            rgba = (*linear(PALETTE[material][0] if color is None else color), 1)
            for i, li in enumerate(face.loop_indices):
                colors.data[li].color = rgba
                if uv_data is not None:
                    uv_data[li].uv = uv[i] if uv else (0,0)


def tile_floor(part, width, depth, spacing, holes=()):
    """Run continuous tile joints up to the edges of actual floor openings."""
    x_lines = {-width/2,width/2}
    y_lines = {-depth/2,depth/2}
    x_lines.update(-width/2 + i*spacing for i in range(1,math.ceil(width/spacing)))
    y_lines.update(-depth/2 + i*spacing for i in range(1,math.ceil(depth/spacing)))
    for a,b,c,d in holes:
        x_lines.update((a,b))
        y_lines.update((c,d))
    xs, ys = sorted(x_lines), sorted(y_lines)
    for i, (a,b) in enumerate(zip(xs,xs[1:])):
        for j, (c,d) in enumerate(zip(ys,ys[1:])):
            if any(h0 <= (a+b)/2 <= h1 and k0 <= (c+d)/2 <= k1 for h0,h1,k0,k1 in holes):
                continue
            shade = [0xb5b8b5,0xbbbfba,0xb2b6b3,0xb8bbb7][(i*11+j*13)%4]
            g = min(.009,(b-a)/4,(d-c)/4)
            part.sheet(a+g,b-g,c+g,d-g,0,"stone",shade)
    x_cuts = sorted({-width/2, width/2, *(v for a,b,_,_ in holes for v in (a,b))})
    y_cuts = sorted({-depth/2, depth/2, *(v for _,_,c,d in holes for v in (c,d))})
    for a,b in zip(x_cuts,x_cuts[1:]):
        for c,d in zip(y_cuts,y_cuts[1:]):
            if not any(h0 <= (a+b)/2 <= h1 and k0 <= (c+d)/2 <= k1 for h0,h1,k0,k1 in holes):
                part.sheet(a,b,c,d,-.007,"concrete",GROUT)
                part.sheet(a,b,c,d,-.22,"concrete",down=True)
    well_lining(part,-width/2,width/2,-depth/2,depth/2,-.22,-.007,"concrete")
    for a,b,c,d in holes:
        well_lining(part, a,b,c,d,-.22,-.007,"concrete")


def well_lining(part, a,b,c,d, bottom, top, material):
    part.pane((a,c),(a,d),bottom,top,material)
    part.pane((b,d),(b,c),bottom,top,material)
    part.pane((a,d),(b,d),bottom,top,material)
    part.pane((b,c),(a,c),bottom,top,material)


def annulus(part, x, y, z, outer, inner, material, color=None, count=40, down=False):
    for i in range(count):
        a,b = (2*math.pi*j/count for j in (i,i+1))
        corners = [(x+r*math.cos(t),y+r*math.sin(t),z)
                   for r,t in ((inner,a),(outer,a),(outer,b),(inner,b))]
        if inner == 0:
            corners.pop()
        part.polygon(corners[::-1] if down else corners, material, color)


def escalate(part, origin, direction, length, drop, width=1.02, steps=24, rail_height=.98):
    x,y,z = origin
    dx,dy = direction
    sx,sy = -dy,dx

    def p(t,u,h):
        return (x+t*dx+u*sx,y+t*dy+u*sy,z+h)

    for i in range(steps):
        a,b = length*i/steps,length*(i+1)/steps
        h, below = -drop*i/steps, -drop*(i+1)/steps
        half = width/2
        part.polygon([p(a,-half,h),p(b,-half,h),p(b,half,h),p(a,half,h)],"metal",0x959d9d)
        part.polygon([p(b,-half,h),p(b,-half,below),p(b,half,below),p(b,half,h)],"trim",0x4d5557)
        part.polygon([p(a,-half,h+.004),p(a+.018,-half,h+.004),
                      p(a+.018,half,h+.004),p(a,half,h+.004)],"paint",0xb69848)
    for u in (-width/2-.055,width/2+.055):
        profile = [(-.55,0),(0,0),(length,-drop),(length+.36,-drop)]
        for (a,za),(b,zb) in zip(profile,profile[1:]):
            part.beam(p(a,u,za-.095),p(b,u,zb-.095),.175,.20,"metal",across=(sx,sy,0))
            part.polygon([p(a,u,za+.04),p(b,u,zb+.04),
                          p(b,u,zb+rail_height),p(a,u,za+rail_height)],"glass",0x9fbec3)
            part.beam(p(a,u,za+rail_height),p(b,u,zb+rail_height),.09,.068,"rubber",across=(sx,sy,0))
        end = length+.36
        for a,h in ((-.55,0),(end,-drop)):
            part.beam(p(a,u,h+.14),p(a,u,h+rail_height),.11,.085,"chrome",across=(sx,sy,0))
    part.polygon([p(-.50,-width/2,0.008),p(0,-width/2,.008),
                  p(0,width/2,.008),p(-.50,width/2,.008)],"metal",0x7b8486)


def guard(part, a, b, z=0, height=1.05):
    dx,dy = b[0]-a[0], b[1]-a[1]
    length = math.hypot(dx,dy)
    across = (-dy/length,dx/length,0)
    part.pane(a,b,z+.12,z+height-.04)
    part.beam((*a,z+height),(*b,z+height),.055,.075,"chrome",across=across)
    for u in (0,.5,1):
        part.box(a[0]+u*dx,a[1]+u*dy,z+height/2,.062,.062,height,"metal")


def arrow(part, x, y, direction, color):
    coords = [(-.05,-.23),(.05,-.23),(.05,.03),(.15,.03),(0,.23),(-.15,.03),(-.05,.03)]
    part.polygon([(x+u*direction,y+v*direction,.017) for u,v in coords],"paint",color)


def lift(shell, x, y, code):
    shell.box(x,y+.66,1.54,2.56,1.62,3.08,"wall",0x89999b,chamfer=.11)
    shell.box(x,y-.18,1.16,1.60,.12,2.32,"trim")
    for dx in (-.374,.374):
        shell.box(x+dx,y-.249,1.10,.738,.037,2.20,"chrome",0xb3bdbe)
    shell.box(x+1.05,y-.193,1.13,.115,.044,.34,"metal",0x64767a)
    shell.box(x+1.05,y-.22,1.18,.048,.014,.046,"lamp_emissive")
    shell.sign(x,y-.195,2.62,1.93,.24,code)


def concourse(add):
    holes = [(2.0,11.15,-6.25,-1.55),(4.25,13.85,4.15,8.75)]
    floor = add("Concourse_Terrazzo_Deck")
    tile_floor(floor,50,25,1.57,holes)
    pattern = add("Concourse_Circular_Floor_Inlays")
    for radius,width in ((2.6,.23),(3.55,.17),(4.2,.10)):
        annulus(pattern,-13,-5,.014,radius,radius-width,"stone",0x818d88)
    for a,b,c,d in ((-24,-9,-3.15,-2.88),(-9,-3,-3.15,-2.88),(-3.27,-3, -3.15,1.65)):
        pattern.sheet(a,b,c,d,.018,"stone",TACTILE)

    walls = add("Concourse_Stone_Walls_And_Open_Portals")
    for a,b in ((-25,-16.5),(-11.9,2),(7.2,25)):
        walls.box((a+b)/2,12.28,2.29,b-a,.44,4.58,"wall",0xaab0aa)
        walls.box((a+b)/2,12.042,.21,b-a,.038,.42,"stone",0x727a78)
        for x in range(math.ceil(a+.3),math.floor(b-.3),2):
            walls.box(x,12.039,2.40,.019,.025,3.84,"trim",0x7a817e)
    for a,b in ((-12.5,-8.8),(-4.8,4.8),(8.8,12.5)):
        walls.box(24.75,(a+b)/2,2.29,.5,b-a,4.58,"wall")
    for a,b in ((-12.5,-9), (5.7,12.5)):
        walls.box(-24.75,(a+b)/2,2.29,.5,b-a,4.58,"wall")
    columns = add("Concourse_Brushed_Steel_Columns")
    for x,y in ((-19,-7.8),(-6,-7.8),(3,-8.8),(17,-7.8),(-19,7.8),(-8.2,8.8),(1.2,9.9),(17.5,8.9)):
        columns.cylinder(x,y,2.35,.46,4.70,"metal",0xb2bcb9,segments=10)
        columns.cylinder(x,y,.19,.49,.38,"trim",0x596467,segments=8)
        columns.cylinder(x,y,4.57,.49,.22,"chrome",segments=8)

    canopy = add("Ceiling_Suspended_Panels")
    lighting = add("Ceiling_Light_Strips_And_Green_Oculus")
    canopy.box(0,0,4.89,50,25,.09,"roof",0xaeb9b3)
    for i in range(10):
        for j in range(8):
            x,y = -22.5+5*i,-10.9375+3.125*j
            shade = (0xc5d0c8,0xc0c9c2,0xc9d2c9)[(i+2*j)%3]
            canopy.sheet(x-2.49,x+2.49,y-1.551,y+1.551,4.832,"roof",shade,down=True)
    for y in (-10.75,-6.45,-2.15,2.15,6.45,10.75):
        for i,x in enumerate((-19.3,-7.7,3.9,15.5,22.15)):
            dx = 4.8 if i == 4 else 11.12
            for offset in (-.46,.46):
                canopy.box(x,y+offset,4.66,dx,.85,.14,"roof",0xccd2cd)
            lighting.sheet(x-dx/2+.06,x+dx/2-.06,y-.065,y+.065,4.574,"lamp_emissive",down=True)
    for radii,mat,hex_value,z in (((3.6,2.95),"roof",0x9eada6,4.50),
                                  ((2.95,2.81),"light",0xe0ffe9,4.48),
                                  ((2.81,2.55),"lamp_emissive",0xbcf8bd,4.47),
                                  ((2.55,0),"roof",0xd0e9d2,4.51)):
        annulus(lighting,-13,-5,z,*radii,mat,hex_value,count=32,down=True)
    for x in (-20,-8,4,16,23):
        canopy.box(x,0,4.79,.34,24.8,.29,"roof",0x8c9997)

    gates = add("Faregate_Line_Stainless_Cabinets")
    wing = add("Faregate_Lane_Flaps_And_Readers")
    centers = [-15.5,-14.23,-12.96,-11.69,-10.42,-9.15,-7.88,-6.61,-4.84,-3.57]
    for i,x in enumerate(centers):
        y = .45 if i <= 5 else .65
        gates.box(x,y,.49,.38,1.50,.98,"metal",0xa8b6b9,chamfer=.10)
        gates.box(x,y,.92,.40,1.38,.10,"trim",0x394346,chamfer=.06)
        gates.box(x,y-.56,.994,.27,.23,.043,"rubber")
        wing.sheet(x-.083,x+.083,y-.652,y-.482,1.017,"light",0x8ccad0)
        for side in (-1,1):
            wing.box(x,y+side*.755,.75,.12,.023,.093,"light",
                     (0x8feaa6 if i%3 else 0xf77a67) if side == -1 else 0x8feaa6)
            if (side == -1 and i != 0) or (side == 1 and i != len(centers)-1):
                wing.pane((x+side*.18,y),(x+side*(.76 if i in (7,8) else .59),y),.42,.81,"glass",0x8cb6ad)
    bypass = add("Faregate_Flanking_Glass_Barriers")
    guard(bypass,(-24.96,.45),(-15.82,.45))
    for a,b in zip((-3.30,2.35,8.0,13.6,19.15),(2.35,8.0,13.6,19.15,24.48)):
        guard(bypass,(a,.65),(b,.65))

    office = add("Station_Control_Glazed_Service_Counter")
    ox,oy = -1.0,2.40
    office.box(ox,oy,.51,4.16,2.98,1.02,"wall",0x9badaa,chamfer=.40)
    office.box(ox,oy,2.81,4.28,3.02,.42,"trim",0x243d3e,chamfer=.40)
    office.box(ox,oy,1.025,4.30,3.12,.105,"stone",0x40514e,chamfer=.43)
    outline = [(-2.08,-.95),(-1.66,-1.49),(1.66,-1.49),(2.08,-.95),
               (2.08,.95),(1.66,1.49),(-1.66,1.49),(-2.08,.95)]
    for i, (a,b) in enumerate(zip(outline,outline[1:]+outline[:1])):
        start,end = (ox+a[0],oy+a[1]),(ox+b[0],oy+b[1])
        office.pane(start,end,1.07,2.62,"window" if i >= 4 else "glass")
        office.box(*start,1.85,.095,.095,1.55,"chrome")
    office.box(ox,oy,.98,2.30,.94,.12,"stone",0x758b88)
    for x in (ox-.72,ox+.67):
        office.box(x,oy,1.29,.52,.11,.38,"trim",0x293f45,chamfer=.04)
    office.sign(ox,oy-1.51,2.84,3.25,.40,5)

    kiosks = add("Ticketing_Kiosks")
    for x in (-22.8,-21.6,-20.4):
        kiosks.box(x,11.62,.82,.82,.64,1.64,"metal",0xacbdbe,chamfer=.07)
        kiosks.box(x,11.278,1.27,.55,.06,.42,"trim",0x344849,chamfer=.025)
        kiosks.box(x,11.243,1.32,.40,.019,.23,"light",0xaccdd5)
        kiosks.box(x,11.242,.81,.52,.027,.072,"trim")
        kiosks.box(x,11.26,.37,.52,.03,.30,"rubber")
    for i,(a,b,c,d) in enumerate(holes):
        bottom = -4.15 if i == 0 else -4.70
        well = add(f"Escalator_Well_{i+1}_Lining_And_Guards")
        well_lining(well,a,b,c,d,bottom-.20,.01,"wall")
        well.sheet(a,b,c,d,bottom-.03,"stone",0xaab3b2)
        guard(well,(a,c),(b,c))
        guard(well,(a,d),(b,d))
        guard(well,(b,c),(b,d))
        bank = add(f"Escalator_Bank_{i+1}_To_Platforms")
        for k in range(3):
            escalate(bank,(a+.10,c+.87+1.41*k,0),(1,0),b-a-1.05,-bottom,steps=25)
    lifts = add("Platform_Lifts_And_Call_Panels")
    lift(lifts,17,8.4,2)
    lift(lifts,20,8.4,2)
    signs = add("Concourse_Suspended_Wayfinding")
    for x,y,w,row in ((-10,.48,6.5,1), (5.6,-7.8,5.5,2), (8.0,3.8,5.1,1),(-12,10.8,5.6,7)):
        signs.sign(x,y,3.42,w,.64,row)
        for xx in (x-w*.38,x+w*.38):
            signs.box(xx,y,4.12,.08,.07,.87,"metal")


def screen_mullion(part,x,y,width,depth,color):
    a,b = x-width/2,x+width/2
    part.pane((a,y),(b,y),.14,2.47,"metal",color)
    part.pane((x,y-depth/2),(x,y+depth/2),.14,2.47,"metal",color)


def platform(add, line):
    deck = add("Island_Tiled_Platform_Deck")
    tile_floor(deck,140,11,1.65)
    for side in (-1,1):
        name = "Front" if side == -1 else "Rear"
        edge = add(f"{name}_Tactile_Edge_And_Boarding_Marks")
        edge.box(0,side*5.39,-.07,140,.22,.13,"concrete",0x7d8587)
        for i,(y,w,color) in enumerate(((4.54,.24,0xe4be4c),(4.71,.048,0xf2d66c),(5.07,.09,0x747e81))):
            edge.sheet(-70,70,side*y-w/2,side*y+w/2,.012+i*.001,"stone",color)
        frames = add(f"{name}_Platform_Screen_Door_Frames")
        glazing = add(f"{name}_Platform_Screen_Door_Glazing")
        frames.box(0,side*5.26,2.79,140,.27,.64,"metal",0xb2bdbe)
        frames.box(0,side*5.246,3.30,140,.20,.40,"wall",0xaab4b2)
        frames.box(0,side*5.108,2.77,140,.028,.22,"paint",line)
        frames.box(0,side*5.405,2.77,140,.029,.22,"paint",line)
        frames.box(0,side*5.26,.09,140,.19,.18,"trim",0x596568)
        # Twelve active pairs per edge, in three car groups.
        active = {j+shift for j in (1,3,5,7) for shift in (8,16,24)}
        pitch = 140/40
        for i in range(40):
            a,b = -70+i*pitch,-70+(i+1)*pitch
            x = (a+b)/2
            xx = a+.037
            screen_mullion(frames,xx,side*5.26,.074,.17,0xa4b0b3)
            subdivisions = (a+.040,x-.96,x,x+.96,b-.04) if i in active else (a+.040,x,b-.04)
            if i in active:
                for px in subdivisions[1:-1]:
                    screen_mullion(frames,px,side*5.26,.055,.10,0x59666a)
                frames.box(x,side*5.105,2.42,.21,.023,.115,"trim")
                frames.box(x,side*5.089,2.42,.12,.010,.046,"light",line)
                for dx in (-.72,0,.72):
                    arrow(edge,x+dx,side*4.08,side if dx else -side,0x468f68 if dx else 0xaf4f53)
                for dx in (-.81,.81):
                    edge.sheet(x+dx-.095,x+dx+.095,side*3.68-.021,side*3.68+.021,.018,"paint",0x839c8a)
            else:
                screen_mullion(frames,x,side*5.26,.053,.092,0xa8b2b4)
            for u,v in zip(subdivisions,subdivisions[1:]):
                glazing.pane((u+.021,side*5.28),(v-.021,side*5.28),.17,2.45,"window",0x8aabb1)
                glazing.pane((u+.043,side*5.277),(v-.043,side*5.277),.93,.989,"paint",0x9baeb1)
        frames.box(69.962,side*5.26,1.31,.074,.17,2.43,"metal")
        for x in (-52,-34,-17,11,31,54):
            frames.sign(x,side*5.079,2.78,3.0,.37,4,side=-side)
            if x in (-34,11,54):
                frames.sign(x,side*5.065,2.23,2.03,.245,3,side=-side)

    columns = add("Central_Stainless_Columns_And_Service_Cores")
    seats = add("Platform_Individual_Seats")
    maps = add("Platform_Route_Maps_And_Exit_Signs")
    for x in (-61,-46,-32,-18,18,32,46,61):
        columns.box(x,0,1.82,1.13,.77,3.64,"metal",0xaeb9ba,chamfer=.16)
        columns.box(x,0,.14,1.17,.82,.28,"trim",0x687474,chamfer=.10)
        columns.box(x,0,2.66,1.18,.82,.18,"paint",line)
        if x in (-46,-18,18,46):
            for side in (-1,1):
                y = side*.76
                seats.box(x,y,.39,2.76,.25,.10,"chrome")
                for dx in (-.91,.91):
                    seats.box(x+dx,y,.18,.125,.37,.36,"metal")
                for dx in (-1.02,-.34,.34,1.02):
                    profile = [(.25,.445),(.24,.503),(-.19,.51),(-.25,.81),(-.31,.798),(-.26,.443)]
                    seats.prism([[(x+dx+w,y+side*u,z) for u,z in profile[::side]]
                                 for w in (-.283,.283)],"metal",0xc2c8c4)
    for x in (-55,-26,23,53):
        for side in (-1,1):
            maps.sign(x,side*.18,1.78,2.55,.38,3,side)
            maps.sign(x,side*.21,2.12,2.55,.28,4,side)
        for dx in (-1.1,1.1):
            maps.box(x+dx,0,1.10,.075,.10,2.25,"metal")

    vertical = add("Platform_Central_Escalator_And_Stair")
    vertical.box(12.4,0,1.65,3.1,3.12,3.30,"wall",0x9faeae,chamfer=.10)
    lift(vertical,12.4,-1.49,2)
    for k in range(2):
        escalate(vertical,(8,-.65+1.29*k,3.46),(-1,0),6.85,3.46,steps=22)
    for i in range(23):
        # Fixed stair rises beside the escalators.
        x = 1+i*.30
        z = (i+1)*.15
        vertical.sheet(x,x+.30,1.35,2.55,z,"stone",0xb7bcb7)
        vertical.pane((x,2.55),(x,1.35),z-.15,z,"trim",0x4b5555)
    for y in (1.34,2.56):
        vertical.beam((1,y,.87),(7.9,y,4.29),.058,.065,"chrome")
        for x,z in ((1,.46),(3.2,1.54),(5.4,2.62),(7.9,3.89)):
            vertical.box(x,y,z,.048,.058,.85,"metal")
    for side in (-1,1):
        maps.sign(3,side*2.48,3.02,4.35,.46,2,side)
    ends = add("Platform_End_Walls_And_Service_Doors")
    for x in (-69.88,69.88):
        inset = -.125 if x > 0 else .125
        ends.box(x,0,1.91,.24,10.35,3.82,"wall",0x7b8c8e)
        ends.box(x+inset,0,1.08,.025,1.26,2.14,"trim",0x4a5459)
        ends.box(x+inset*1.18,0,2.39,.016,.76,.10,"lamp_emissive")
    ceiling = add("Ceiling_Platform_Suspended_Liners")
    lights = add("Ceiling_Platform_Linear_Luminaires")
    for a,b,c,d in ((-70,0,-5.4,5.4),(9.85,70,-5.4,5.4),
                    (0,9.85,-5.4,-1.48),(0,9.85,2.83,5.4)):
        ceiling.box((a+b)/2,(c+d)/2,3.88,b-a,d-c,.10,"roof",0x9caaa8)
    for side in (-1,1):
        ceiling.box(0,side*4.35,3.58,140,1.85,.20,"roof",0xb4c0bf)
        for i in range(20):
            x = -66.5+i*7
            if side < 0 or i not in (10,11):
                ceiling.box(x,side*2.56,3.7,6.91,1.54,.16,"roof",0xc0c8c5)
                lights.sheet(x-3.335,x+3.335,side*1.75-.042,side*1.75+.042,3.572,"light",down=True)
            lights.sheet(x-3.335,x+3.335,side*3.31-.05,side*3.31+.05,3.558,"lamp_emissive",down=True)
    for x,dx in ((-35,70),(39.9,60.2)):
        ceiling.box(x,0,3.79,dx,2.99,.14,"roof",0x939f9f)


def entrance(add):
    hole = (-2.21,2.21,-1.49,3.78)
    a,b,c,d = hole
    plaza = add("Exit_B_Tiled_Street_Apron")
    tile_floor(plaza,14,8,.75,[hole])
    paving = add("Exit_B_Guidance_Paving")
    paving.sheet(-.19,.19,-4,-1.505,.01,"stone",TACTILE)
    paving.sheet(-2.19,2.19,-1.81,-1.59,.012,"stone",TACTILE)
    stairwell = add("Exit_B_Stone_Lined_Escalator_Mouth")
    well_lining(stairwell,a,b,c,d,-2.84,.04,"stone")
    stairwell.sheet(a,b,c,d,-2.85,"stone",0xa3aaa9)
    for x in (a-.11,b+.11):
        stairwell.box(x,(c+d)/2,.315,.26,d-c,.63,"stone",0x9da7a6,chamfer=.04)
        stairwell.box(x,(c+d)/2,.64,.32,d-c+.06,.055,"trim",0x6a797a,chamfer=.04)
        guard(stairwell,(x,c+.08),(x,d-.05),.67,.52)
    stairwell.box(0,d+.10,.43,4.67,.24,.86,"stone",0x919b9c,chamfer=.04)

    escalators = add("Exit_B_Paired_Descending_Escalators")
    for x in (-.75,.75):
        escalate(escalators,(x,c+.02,0),(0,1),4.71,2.71,steps=21)
    floor = add("Exit_B_Lower_Landing")
    floor.sheet(-1.42,1.42,3.22,3.78,-2.71,"metal")
    floor.box(0,d+.10,-1.60,2.96,.18,2.17,"wall",0x8b9595)
    for z in (-2.19,-1.68,-1.17):
        floor.box(0,d+.022,z,2.69,.045,.038,"trim",0x657475)

    roof = add("Exit_B_Low_Folded_Canopy_Roof")
    # Pale rainscreen folds along the long eaves with a raised central seam.
    for x0,x1 in ((-6.73,-3.42),(-3.42,0),(0,3.42),(3.42,6.73)):
        for y0,y1,z0,z1 in ((-3.17,-2.77,2.96,3.14),(-2.77,.47,3.14,3.26),
                              (.47,3.44,3.26,3.11),(3.44,3.83,3.11,2.97)):
            roof.prism([[(x0,y0,z0-h),(x1,y0,z0-h),(x1,y1,z1-h),(x0,y1,z1-h)]
                        for h in (.165,0)],"roof",0xe0e3de)
    frame = add("Exit_B_Glazing_Mullions_And_Steel_Bents")
    glazing = add("Exit_B_Laminated_Glass_Side_Screens")
    for x in (-6.34,6.34):
        for y in (-2.48,-.50,1.45,3.47):
            frame.box(x,y,1.48,.14,.16,2.96,"metal",0xa5b1b0,chamfer=.027)
        for y0,y1 in ((-2.48,-.50),(-.50,1.45),(1.45,3.47)):
            glazing.pane((x,y0+.07),(x,y1-.07),.53,2.89,"glass",0xb7d6d8)
        frame.box(x,.495,.49,.14,5.95,.08,"metal")
        frame.box(x,.495,2.92,.16,5.95,.13,"metal")
        frame.box(x,.495,.22,.35,6,.44,"stone",0x8d9696,chamfer=.055)
    for x0,x1 in ((-6.35,-4.22),(-4.22,-2.22),(-2.22,0),(0,2.22),(2.22,4.22),(4.22,6.35)):
        glazing.pane((x0+.08,3.49),(x1-.08,3.49),.62,2.79,"glass")
    for x in (-4.22,-2.22,0,2.22,4.22):
        frame.box(x,3.49,1.47,.08,.125,2.94,"metal")
    frame.box(0,3.49,.31,12.70,.31,.62,"stone",0x929c9b)
    frame.box(0,3.49,2.83,12.70,.18,.16,"metal")
    for x in (-5.45,-3.87,3.87,5.45):
        frame.box(x,-2.71,1.46,.175,.175,2.92,"metal",0xb7bfbb,chamfer=.034)
    soffit = add("Exit_B_Soffit_Light_Strips")
    for y in (-2.52,-.28,2.10):
        for x in (-4.93,0,4.93):
            soffit.box(x,y,2.92,2.85,.073,.057,"lamp_emissive")
    signs = add("Exit_B_Bayfront_Line_And_Destination_Signs")
    signs.sign(0,-3.18,2.61,7.04,.78,0)
    for x in (-3.02,3.02):
        signs.box(x,-3.04,2.84,.085,.28,.29,"metal")
    signs.sign(0,-.97,2.53,3.92,.43,7)
    signs.sign(4.91,-2.69,1.40,.94,.19,4)
    benches = add("Exit_B_Granite_Seating_Plinths")
    for x in (-4.53,4.53):
        benches.box(x,.74,.223,2.53,.62,.447,"stone",0xa2abaa,chamfer=.12)
        benches.box(x,.74,.473,2.62,.69,.077,"stone",0xb5bdb9,chamfer=.132)


def aim(obj, target):
    obj.rotation_euler = (Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def area(name, at, target, power, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size = power, 'DISK', size
    obj = bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(obj)
    obj.location = at
    aim(obj,target)


def views(kind, stem):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12
    scene.cycles.use_denoising = True
    scene.cycles.max_bounces = 5
    scene.cycles.transparent_max_bounces = 10
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = 576,450
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.world = bpy.data.worlds.new("Review World")
    scene.world.use_nodes = True
    w = scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (.49,.58,.66,1)
    w.inputs["Strength"].default_value = .46
    scene.render.film_transparent = True
    camera_data = bpy.data.cameras.new("Review Camera")
    camera = bpy.data.objects.new("Review Camera",camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    if kind == "entrance":
        area("Canopy key",(-7,-9,12),(0,0,0),3200,9)
        area("Canopy edge",(4,5,9),(0,0,0),1800,7)
        area("Escalator fill",(0,-2,2),(0,2,-1),155,3.2)
        shots = [
            ((11,-16,9),(0,0,.64),17.3,False),
            ((0,-18,2.72),(0,0,.80),16.8,False),
            ((-14,10,8),(0,0,.8),17.5,False),
            ((.001,-.001,22),(0,0,0),16.0,True),
            ((0,-3.75,1.64),(0,2.2,-.65),22,False),
            ((-8.4,-11.4,5.7),(0,-1.1,1.18),40,False),
        ]
    elif kind == "concourse":
        area("Review key",(0,-12,22),(0,0,0),16000,32)
        for x in (-18,-10,-2,6,14,22):
            for y in (-7,4,9):
                area(f"Interior {x} {y}",(x,y,4.34),(x,y,0),145,4.2)
        for x,y in ((6,-4),(8,6)):
            area(f"Well {x}",(x,y,2.6),(x,y,-4),90,2.6)
        shots = [
            ((31,-43,37),(0,0,.0),63,True),
            ((-27,38,26),(0,0,.0),62,True),
            ((.001,-.002,78),(0,0,0),56,True),
            ((-12.7,-8.65,1.64),(-8.1,2.7,1.75),23,False),
            ((-1.1,-2.05,1.67),(6.4,-4.08,.7),25,False),
            ((-20,-7.1,1.84),(-9,0,2.62),20,False),
        ]
    else:
        for x in range(-65,70,9):
            area(f"Platform {x}",(x,0,3.44),(x,0,0),169,3.8)
        area("Review overview",(0,-23,44),(0,0,0),26000,56)
        shots = [
            ((34,-94,83),(0,0,.55),154,True),
            ((-40,94,61),(0,0,.55),152,True),
            ((.002,-.002,170),(0,0,0),148,True),
            ((-14,-2.7,1.65),(7,-.86,1.84),21,False),
            ((-39,-2.75,1.68),(-33.6,-5.0,1.97),24,False),
            ((-31,3.46,1.64),(-22,.1,1.50),25,False),
        ]
    for i,(eye,target,scale,cut) in enumerate(shots):
        for obj in scene.objects:
            if obj.type == 'MESH':
                obj.hide_render = cut and (
                    obj.name.startswith("Ceiling_") or obj.name in
                    {"Exit_B_Low_Folded_Canopy_Roof", "Exit_B_Soffit_Light_Strips"})
        camera.location = eye
        aim(camera,target)
        if (i == 2 and kind != "entrance") or (i == 3 and kind == "entrance"):
            camera.rotation_euler = (0,0,0)
        camera_data.type = 'ORTHO' if (i < 3 or kind == "entrance" and i == 3) else 'PERSP'
        camera_data.ortho_scale, camera_data.lens = scale, scale
        camera_data.clip_end = 350
        scene.render.filepath = str(QA / f"{stem}_{i}.png")
        bpy.ops.render.render(write_still=True)


def build(kind, render):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1
    parts = []

    def add(name):
        part = Part(name)
        parts.append(part)
        return part

    if kind == "concourse":
        concourse(add)
    elif kind == "entrance":
        entrance(add)
    else:
        platform(add,GOLD if kind == "circle" else BLUE)
    materials = make_materials(QA / f"atlas_{kind}.jpg")
    for part in parts:
        part.finish(materials)
    stem = f"bayfront_platform_{kind}" if kind in {"circle","downtown"} else f"bayfront_{kind}"
    bpy.ops.export_scene.gltf(
        filepath=str(ROOT / f"{stem}.glb"), export_format='GLB', export_yup=True,
        export_cameras=False, export_lights=False, export_animations=False,
        export_skins=False, export_image_format='AUTO', export_vertex_color='MATERIAL',
    )
    if render:
        views(kind,stem)


if __name__ == '__main__':
    if bpy.app.version != (5,1,2):
        raise RuntimeError(f"Expected Blender 5.1.2, got {bpy.app.version_string}")
    arguments = sys.argv[sys.argv.index("--")+1:]
    render = "--export-only" not in arguments
    for name in [arg for arg in arguments if not arg.startswith("--")] or ["concourse","circle","downtown","entrance"]:
        build(name,render)
