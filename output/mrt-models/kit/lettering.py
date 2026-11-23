"""Low-cost geometric lettering for equipment with tight triangle budgets."""
from collections import Counter, defaultdict

from mathutils import Vector
from mathutils.geometry import delaunay_2d_cdt

from geometry import part_name

# Each glyph is outlined with convex patches; separated patches have shared borders.
GLYPHS = {
    'A': [[(0,0),(.33,1),(.57,1),(.2,0)],[(.43,1),(.67,1),(1,0),(.8,0)],[(.23,.28),(.78,.28),(.73,.43),(.27,.43)]],
    'B': [[(0,0),(.17,0),(.17,1),(0,1)],[(.17,.85),(.67,.85),(.84,1),(.17,1)],
          [(.67,.85),(.72,.61),(.90,.62),(.84,1)],[(.17,.42),(.79,.42),(.90,.62),(.17,.58)],
          [(.69,.43),(.79,.16),(1,0),(.87,.44)],[(.17,0),(1,0),(.79,.16),(.17,.16)]],
    'U': [[(0,1),(.18,1),(.18,.18),(0,.18)],[(.18,0),(.82,0),(1,.18),(0,.18)],
          [(.82,.18),(1,.18),(1,1),(.82,1)]],
    'S': [[(0,.86),(.16,1),(1,1),(.96,.85)],[(0,.86),(.18,.86),(.18,.57),(0,.45)],
          [(0,.45),(.87,.42),(1,.57),(.18,.57)],[(.82,.45),(1,.57),(1,.16),(.82,.16)],
          [(0,0),(.84,0),(1,.16),(0,.16)]],
    'R': [[(0,0),(.18,0),(.18,1),(0,1)],[(.18,.84),(.79,.84),(.94,1),(.18,1)],
          [(.76,.84),(.94,1),(.94,.50),(.76,.50)],[(.18,.45),(.88,.45),(.94,.61),(.18,.61)],
          [(.42,.48),(.62,.48),(1,0),(.77,0)]],
    'I': [[(.39,0),(.61,0),(.61,1),(.39,1)]],
    'L': [[(0,0),(1,0),(1,.17),(0,.17)],[(0,.17),(.18,.17),(.18,1),(0,1)]],
    'V': [[(0,1),(.21,1),(.59,0),(.39,0)],[(.41,0),(.79,1),(1,1),(.61,0)]],
    'M': [[(0,0),(.16,0),(.16,1),(0,1)],[(.84,0),(1,0),(1,1),(.84,1)],
          [(.12,1),(.31,1),(.59,.53),(.45,.43)],[(.42,.53),(.69,1),(.88,1),(.55,.43)]],
    'N': [[(0,0),(.17,0),(.17,1),(0,1)],[(.83,0),(1,0),(1,1),(.83,1)],
          [(.07,1),(.25,1),(.94,0),(.76,0)]],
    '0': [[(0,0),(.18,.15),(.18,.85),(0,1)],[(.82,.15),(1,0),(1,1),(.82,.85)],
          [(0,0),(1,0),(.82,.15),(.18,.15)],[(.18,.85),(.82,.85),(1,1),(0,1)]],
    '1': [[(.31,0),(.55,0),(.55,1),(.12,.75)]],
    '2': [[(0,.84),(.16,1),(1,1),(.80,.84)],[(.80,.60),(1,.48),(1,1),(.80,.84)],
          [(0,.48),(.18,.35),(1,.48),(.80,.60)],[(0,0),(.18,.15),(.18,.35),(0,.48)],
          [(0,0),(1,0),(1,.15),(.18,.15)]],
    '3': [[(0,0),(1,0),(.82,.16),(0,.16)],[(.82,.16),(1,0),(1,1),(.82,.84)],
          [(0,.84),(.82,.84),(1,1),(0,1)],[(.16,.42),(.82,.42),(.82,.58),(.16,.58)]],
    '4': [[(0,.31),(.18,.48),(.18,1),(0,1)],[(.72,0),(.9,0),(.9,1),(.72,1)],
          [(0,.31),(1,.31),(1,.48),(.18,.48)]],
    '5': [[(0,1),(.17,.84),(1,.84),(1,1)],[(0,.43),(.18,.59),(.18,.84),(0,1)],
          [(0,.43),(.82,.43),(1,.59),(.18,.59)],[(.82,.15),(1,0),(1,.59),(.82,.43)],
          [(0,0),(1,0),(.82,.15),(0,.15)]],
    '6': [[(0,0),(.18,.16),(.18,.84),(0,1)],[(.18,.84),(1,.84),(1,1),(0,1)],
          [(.18,.43),(.82,.43),(1,.60),(.18,.60)],[(.82,.16),(1,0),(1,.60),(.82,.43)],
          [(0,0),(1,0),(.82,.16),(.18,.16)]],
    '8': [[(0,0),(.18,.14),(.18,.86),(0,1)],[(.82,.14),(1,0),(1,1),(.82,.86)],
          [(0,0),(1,0),(.82,.14),(.18,.14)],[(.18,.43),(.82,.43),(.82,.57),(.18,.57)],
          [(.18,.86),(.82,.86),(1,1),(0,1)]],
}
# Collinear points, where present, do not add triangles.
WIDTHS = {'I':.44,'1':.74,'M':1.22,' ': .51}

def letter_line(model, text, low, high, style):
    advances = [WIDTHS.get(c,1)+.23 for c in text]
    width = sum(advances)-.23
    x = 0
    for character,advance in zip(text,advances):
        for patch in GLYPHS.get(character,()):
            points = [(low.x + (x+(advance-.23)*u)*(high.x-low.x)/width,
                       low.y,low.z+v*(high.z-low.z)) for u,v in patch]
            # Outline patches can start on either side. Face the source's front.
            area = sum(a[0]*b[2]-b[0]*a[2] for a,b in zip(points,points[1:]+points[:1]))
            model.face(points if area>0 else points[::-1],style)
        x += advance

def route_map(model, objects, sourced, world_bounds):
    for obj in objects:
        key = part_name(obj)
        mat = {'PANEL_Frame':'metal','PANEL_Inlay':'plate','ROUTE_Line':'trim',
               'STOP_Marker':'trim','EDITABLE_Title':'trim','EDITABLE_Stop':'trim'}[key]
        style = sourced(mat,obj)
        lo,hi = world_bounds(obj)
        if key=='PANEL_Frame':
            lo.y = -.041
            model.box(lo,hi,style)
        elif key=='PANEL_Inlay':
            model.front_quad(lo.x,hi.x,-.04125,lo.z,hi.z,style)
        elif key=='EDITABLE_Title':
            for triangle in simplified_cap(obj,.00135):
                center_x = sum(v[0] for v in triangle)/3
                if not -.162<center_x<-.113:
                    model.face([(x,-.0416,z) for x,_,z in triangle],style)
                # The first R touches the following A at one coordinate in the source.
                # Reuse the matching, clean R outline from ROUTE at the first R's placement.
                if .153<center_x<.206:
                    model.face([(x-.31563,-.0416,z) for x,_,z in triangle],style)
        elif key=='EDITABLE_Stop':
            i = round((obj.matrix_world.translation.x+.65)/.26)+1
            lo.y = -.0416
            letter_line(model,str(i),lo,hi,style)
        elif key=='STOP_Marker':
            model.front_quad(lo.x,hi.x,-.0418,lo.z,hi.z,style)
        elif key=='ROUTE_Line':
            model.front_quad(lo.x,hi.x,-.04155,lo.z,hi.z,style)

def bus_display(model, objects, sourced, world_bounds):
    for obj in objects:
        key = part_name(obj)
        mat = {'DISPLAY_Housing':'rubber','DISPLAY_Glass':'screen',
               'MOUNT_Bracket':'metal','EDITABLE_Heading':'plate','EDITABLE_Row':'trim'}[key]
        style = sourced(mat,obj)
        lo,hi = world_bounds(obj)
        if key.startswith('EDITABLE'):
            phrase = 'BUS     ARRIVAL' if key=='EDITABLE_Heading' else (
                '101      3 MIN' if lo.z>.4 else '203      8 MIN')
            lo.y = -.0912
            letter_line(model,phrase,lo,hi,style)
        elif key=='DISPLAY_Glass':
            model.front_quad(lo.x,hi.x,-.0906,lo.z,hi.z,style)
        elif key=='DISPLAY_Housing':
            model.part(obj,style,chamfer=.018,axis=1,corner_pair='high_v')
        else:
            model.part(obj,style,axis=1,skip=(0,))


def simplified_cap(obj, tolerance):
    """Simplify the front cap's contours while retaining holes in original glyphs."""
    obj.data.calc_loop_triangles()
    coordinates = [obj.matrix_world @ v.co for v in obj.data.vertices]
    edge_counts = Counter()
    depth = min(p.y for p in coordinates)
    for tri in obj.data.loop_triangles:
        if tri.normal.z < .999:
            continue
        points = [(round(coordinates[i].x,7),round(coordinates[i].z,7)) for i in tri.vertices]
        edge_counts.update(tuple(sorted((a,b))) for a,b in zip(points,points[1:]+points[:1]))
    neighbors = defaultdict(list)
    for (a,b),count in edge_counts.items():
        if count == 1:
            neighbors[a].append(b)
            neighbors[b].append(a)

    contours,visited = [],set()
    for start in neighbors:
        if start in visited:
            continue
        current,previous = start,None
        contour = []
        while current not in visited:
            visited.add(current)
            contour.append(Vector(current))
            candidates = [p for p in neighbors[current] if p!=previous]
            if not candidates:
                break
            previous,current = current,candidates[0]
        if current != start or len(contour)<3:
            continue
        while len(contour)>3:
            distances = []
            for i,p in enumerate(contour):
                a,b = contour[i-1],contour[(i+1)%len(contour)]
                base = b-a
                projection = max(0,min(1,(p-a).dot(base)/base.length_squared)) if base.length_squared else 0
                distances.append(((p-a-base*projection).length,i))
            distance,index = min(distances)
            if distance>=tolerance:
                break
            contour.pop(index)
        contours.append(contour)

    vertices,edges = [],[]
    for contour in contours:
        offset = len(vertices)
        vertices.extend(contour)
        edges.extend((offset+i,offset+(i+1)%len(contour)) for i in range(len(contour)))
    output,_,faces,*_ = delaunay_2d_cdt(vertices,edges,[],0,1e-8,False)
    for tri in faces:
        q = sum((output[i] for i in tri),Vector((0,0)))/3
        crossings = 0
        for contour in contours:
            for a,b in zip(contour,contour[1:]+contour[:1]):
                if (a.y>q.y) != (b.y>q.y) and q.x < (b.x-a.x)*(q.y-a.y)/(b.y-a.y)+a.x:
                    crossings += 1
        if crossings%2:
            yield [(output[i].x,depth,output[i].y) for i in tri]
