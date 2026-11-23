"""Paint front-space designs into the original UV islands, including filter gutters."""
import numpy as np
from face import *
from regions import smooth
from atlas import layout

def srgb(code):
    rgb=np.array([int(code[k:k+2],16) for k in (0,2,4)])/255.
    return rgb

def mix(a,b,t):
    return a+(b-a)*np.clip(t,0,1)[...,None]

def orbital_contour(base,u,y):
    # Trace the source eye pigment against peach skin along rays. The surprise
    # ink follows the modeled rim, including the flatter lower/inner corner.
    theta=np.linspace(-np.pi,np.pi,360,endpoint=False)
    radius=np.arange(36,122,.4)[None,:]
    samples=sample(base,248+np.cos(theta[:,None])*radius,535+np.sin(theta[:,None])*radius)
    red,green,blue=samples.transpose(2,0,1)
    pigment=(red<.80)|((red-green<.12)&(green>.6))
    radii=np.max(np.where(pigment,radius,0),axis=1)
    weights=np.exp(-(np.arange(-6,7)/3.1)**2)
    radii=sum(w*np.roll(radii,k) for k,w in zip(range(-6,7),weights))/weights.sum()
    dx=(u-248)/1.025
    dy=(y-535)/1.035
    polar=np.arctan2(dy,dx)
    return np.hypot(dx,dy)-np.interp(polar,theta,radii,period=2*np.pi)

def paint(front,state):
    # Screen coordinates are measured directly on the neutral albedo projection.
    base=front[::-1].copy()
    y,x=np.mgrid[:H,:W]
    center=430.94
    u=center-np.abs(x-center)
    x_signed=x-center
    edited=base.copy()
    alpha=np.zeros((H,W))
    def coat(color,mask):
        nonlocal edited,alpha
        edited=mix(edited,color,mask)
        alpha=1-(1-alpha)*(1-np.clip(mask,0,1))
    def ellipse(cx,cy,rx,ry):
        return (np.hypot((u-cx)/rx,(y-cy)/ry)-1)*min(rx,ry)
    def ink(distance,softness=1.4):
        return 1-smooth(.5+distance/softness)
    def line(u0,u1,end0,end1,bend,width,col):
        t=(u-u0)/(u1-u0)
        b=np.clip(t,0,1)
        center_y=end0*(1-b)+end1*b-4*b*(1-b)*bend
        thickness=width*np.maximum(0,np.sin(b*np.pi))**.62
        d=np.abs(y-center_y)-thickness
        coat(srgb(col),ink(d)*smooth(t*90)*smooth((1-t)*90))
    # Sample clean skin along the same meridians, above and below the eye.
    # The varying sample positions retain the original warm cheek shading.
    top=sample(base,x,399+4*np.cos(u/47))
    bottom=sample(base,x,645+4*np.sin(u/44))
    skin=mix(top,bottom,smooth((y-405)/242))
    clean=smooth((u-142)/13)*smooth((351-u)/11)*smooth((y-388)/24)*smooth((645-y)/17)
    coat(skin,clean)
    if state=="happy":
        # A softly shaded lid fold and one tapered, convex-up lash per side.
        tint=np.exp(-((u-250)/80)**4-((y-542)/24)**2)*.20
        coat(srgb("e8a381"),tint)
        line(163,335,558,550,37,7.6,"773c26")
        line(164,334,557,549,38,4.4,"542d23")
        line(179,319,447,443,17,3.5,"a56544")
        # A broad warm apple under the outer lid follows the lifted cheek plane.
        cheek=np.exp(-((u-212)/53)**2-((y-637)/21)**2)
        coat(srgb("ee9d8e"),cheek*.58)
        highlight=np.exp(-((u-223)/38)**2-((y-622)/9.5)**2)
        coat(srgb("ffcfaf"),highlight*.36)
    else:
        # Rounded whites, dark upper lash, amber iris, pupil and two catchlights.
        cx,cy,rx,ry=(249,533,91,96) if state=="surprised" else (249,537,87,79)
        uu=(u-cx)/rx
        vv=(y-cy)/ry
        rim=((np.abs(uu)**2.22+np.abs(vv)**2.22)**(1/2.22)-1)*min(rx,ry)
        if state=="surprised":
            rim=orbital_contour(base,u,y)
            lid=rim
            icx,icy,irx,iry=264,533,38,47
        else:
            # The outer corner of the lowered lid hangs below its inner corner.
            roof=527-24*np.clip(uu,-1,1)-19*(1-np.clip(uu,-1,1)**2)
            lid=np.maximum(rim,roof-y)
            icx,icy,irx,iry=272,548,50,60
        coat(srgb("9b6655"),ink(lid-1.4))
        white=mix(srgb("dfd1d3"),srgb("fffaf6"),.85-.35*np.clip(-vv,0,1)-.28*np.abs(uu)**3)
        coat(white,ink(lid+.7))
        inner=ink(lid+1)
        ir=ellipse(icx,icy,irx,iry)
        coat(srgb("684331"),ink(ir)*inner)
        if state=="sad":
            # Resample the source iris, including its original painted glint.
            ix=278+(u-icx)*(56/irx)
            iy=544+(y-icy)*(71/iry)
            ix=np.where(x<=center,ix,2*center-ix)
            iris=sample(base,ix,iy)
            coat(iris,ink(ir+2)*inner)
        else:
            iris=mix(srgb("70412a"),srgb("bf7d47"),smooth((y-icy+iry)/(1.8*iry)))
            coat(iris,ink(ir+2)*inner)
            coat(srgb("482c22"),ink(ellipse(icx,icy-3,15,23))*inner)
            coat(srgb("fffaf4"),ink(ellipse(icx+11,icy-18,7.4,8.3))*inner)
            coat(srgb("e8be90"),ink(ellipse(icx-11,icy+22,2.6,3.0))*inner)
        if state=="surprised":
            upper=smooth((cy+14-y)/43)
            coat(srgb("67371f"),ink(np.abs(rim+4.7)-7.1*upper)*upper)
            line(179,318,424,418,23,4.8,"955c3e")
        else:
            t=np.clip((u-(cx-rx))/(2*rx),0,1)
            roof=527-24*np.clip(uu,-1,1)-19*(1-np.clip(uu,-1,1)**2)
            upper=ink(np.abs(y-roof)-6*np.maximum(0,np.sin(np.pi*t))**.55)*ink(rim-1)
            coat(srgb("673a29"),upper)
            line(168,330,486,444,12,5.4,"965b3b")
    # Remove the straight source mouth before painting the changed lip contour.
    mx=x_signed
    t=(y-668)/58
    clean_lip=mix(sample(base,x,np.full_like(x,668)),sample(base,x,np.full_like(x,726)),smooth(t))
    clear=smooth((58-np.abs(mx))/11)*smooth((y-671)/10)*smooth((720-y)/11)
    coat(clean_lip,clear)
    if state=="surprised":
        r=(np.hypot(mx/17,(y-698)/23)-1)*17
        coat(srgb("b77862"),ink(r-1.2))
        mouth=mix(srgb("713d36"),srgb("ac6560"),smooth((y-687)/33))
        coat(mouth,ink(r+.7))
        tongue=ink((np.hypot((mx+1)/12,(y-713)/7)-1)*7)*ink(r+3)
        coat(srgb("c67a73"),tongue*.72)
    else:
        width=55 if state=="happy" else 43
        a=np.clip(mx/width,-1,1)
        if state=="happy":
            top=685+10*(1-a*a)
            lower=685+24*(1-a*a)
            d=np.maximum(top-y,y-lower)
            mask=ink(d)*smooth((width-np.abs(mx))/2.5)
            mouth=mix(srgb("804737"),srgb("ac6655"),smooth((y-691)/16))
            coat(mouth,mask)
            coat(srgb("d9917f"),ink(np.abs(y-lower+2)-1.3)*mask*.26)
        else:
            lip=702-14*(1-a*a)
            thick=2.6*(1-a*a)**.55
            coat(srgb("995c42"),ink(np.abs(y-lip)-thick)*smooth((width-np.abs(mx))/4))
    return edited[::-1],alpha[::-1]

def uv_surface(body,size):
    xyz,idx,uv=triangles(body)
    world=np.zeros((size,size,3),np.float32)
    best=np.full((size,size),-np.inf,np.float32)
    for coords,vs in zip(uv,xyz[idx]):
        tri=coords*size-.5
        result=raster(tri,size,size,pad=4)
        if result is None: continue
        j,i,b=result
        lens=np.linalg.norm(tri[[2,0,1]]-tri[[1,2,0]],axis=1)
        v1,v2=tri[1]-tri[0],tri[2]-tri[0]
        heights=abs(v1[0]*v2[1]-v1[1]*v2[0])/np.maximum(lens,1e-8)
        score=(b*heights).min(axis=1)
        keep=score>best[j,i]
        j,i,b,score=j[keep],i[keep],b[keep],score[keep]
        world[j,i]=b@vs
        best[j,i]=score
    return world

def make_maps(body):
    front,_,_=project(body)
    size=1024
    neutral=layout(body)
    coords=uv_surface(body,size)
    save_rgb(ROOT/"textures/neutral.png",neutral)
    x,y,z=coords.transpose(2,0,1)
    region=(z>.615)&(z<.844)&(abs(x)<.15)&(y<-.070)
    j,i=np.where(region)
    px=(x[region]-LEFT)*SCALE-.5
    py=(z[region]-BOTTOM)*SCALE-.5
    for state in NAMES[1:]:
        painted,alpha=paint(front,state)
        # Transport the change in colour across every surface at that position.
        # In fully painted areas use the authored colour. At the outer edge
        # preserve the original UV texture through the front-projection blend.
        target=sample(painted,px,py)
        amount=sample(alpha[:,:,None],px,py)[:,0]
        src=sample(front,px,py)
        result=neutral.copy()
        changed=amount>0
        result[j[changed],i[changed]]=target[changed]+(neutral[j[changed],i[changed]]-src[changed])*(1-amount[changed,None])
        save_rgb(ROOT/"textures"/(state+".png"),result)
    node=next(n for n in body.data.materials[0].node_tree.nodes if n.type=="TEX_IMAGE")
    node.image=bpy.data.images.load(str(ROOT/"textures/neutral.png"))
