# Original food tin pilot contract (pre-generation)
Original unbranded DEMO / CONCEPT food tin, nominal diameter 0.075m and height0.11m. Not food-safe/fabrication/certified packaging and not a physically simulated pull-open can. Removable recessed lid and pull ring illustrate assembly and inspection, with explicit clearance rather than a sealing/tearing claim.

Fixed caps:12000triangles,12primitives,1000000GLBbytes,texture <=2048x1024. No budget increases after failure. Editable source body/upperrim/lowerrim/lid/rivet/ring/label. Blender Z-up metre,glTF Y-up metre; base at0.

Root ASSET_DemoFoodTin; BODY_HollowShell; RIM_Upper; RIM_Lower; LABEL_Wrap; MOVABLE_Lid containing LID_Plate and LID_Rivet; MOVABLE_PullRing child containing RING_Handle. Clips OpenClose and Exploded, mutually exclusive,0→1.5→3 seconds, complete rest restoration. OpenClose raises lid45mm and rotates ring; Exploded raises lid70mm and ring additionally25mm. No scale/fade or visibility tricks. Final rawGLB and sampled motion are acceptance evidence, not this design document.

Geometry checks: manifold solid hollow shell incl bottom, open rim cavity not a filled cylinder; consistent outward surface normals; lid radial clearance and all sampled parts stay above interior body/rim except deliberate assembly contact. Labels UV wrap with back seam, uniform seam background, originalgraphics and DEMO/CONCEPT visible. Source edit verification changes copied mesh vertex +materialroughness and exports after save/reopen without generator, canonical hashunchanged.

Preview acceptance: actualclosed front/side/rear/top, opened and exploded inspected; browser loadedSHA +closed/open/reset endpoints. Fixedcaps and Khronos validator; no actualmobile/Safari claims. Source licensing originalownerproject; publicredistribution terms notasserted.
