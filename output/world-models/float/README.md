# The Float @ Marina Bay

This historical venue model follows the brief's short-end performance layout. The 120 × 83 m deck sits 1.2 m above the water datum. Its 15 interlocking steel pontoon units form a 3 × 5 grid beneath a light grey deck with panel seams, low dark fascia, rubber fenders and six detachable dolphin moorings. The land-side grandstand and shore bridges sit outside the floating asset's scope.

The event fit-out includes a steel lattice proscenium 30 m above deck, two 25 m stage towers with line-array speakers, overhead lighting trusses, a 60 × 15 m main LED wall, two wing screens, and a red-and-white performance riser. The tower and pylon placement, bracing detail, wing screens and riser are approximations for the requested short-end layout. DSTA's 2022 documentation establishes the main steelwork and screen dimensions. The screens show their idle surfaces.

- [DSTA engineering paper on the floating stage](https://floatingsolutions.org/wp-content/uploads/2019/12/Floating-platform-stage.pdf)
- [NUS report on the detachable mooring system](https://bpb-us-w2.wpmucdn.com/blog.nus.edu.sg/dist/1/17022/files/2025/10/FSReport.pdf)
- [DSTA's 2022 National Day Parade staging notes](https://www.dsta.gov.sg/whats-on/spotlight/celebrating-a-stronger-singapore-together)
- [The 2022 event sound supplier's stage photograph](https://www.dbaudio.com/global/es/aplicaciones/educacion-conferencias-y-administraciones-publicas/el-sistema-ksl-de-db-audiotechnik-participa-con-orgullo-en-el-desfile-del-dia-nacional-de-singapur/)

## Use and verification

`float.glb` is self-contained, in metres, with +Y up and the stage facing +Z. The shared pivot is the centre of the deck plan at the waterline. The moorings extend below that datum. The 125 × 85 m footprint includes the moorings. Each named part is a top-level GLB node. Its flat PBR material names use the supplied palette, with no texture maps.

`contact-sheet.png` shows the reimported GLB rendered in Cycles CPU. From left to right, the top row shows the front oblique, front and left-side views. The bottom row shows the top, rear and right-side views. Water, camera and lighting are review-scene elements.

To regenerate in this folder, run the supplied Blender 5.1.2 executable and guard library with `-b -noaudio -t 2 --python-exit-code 1 --python build_float.py`. Then run `node verify_float.mjs` with the repository dependencies installed. It validates the GLB, checks scale and orientation in an independent loader, and writes `models.json`. The render tiles can be combined with:

```sh
ffmpeg -v error -y -i .review/iso.png -i .review/front.png -i .review/side_left.png \
  -i .review/top.png -i .review/rear.png -i .review/side_right.png \
  -filter_complex 'xstack=inputs=6:layout=0_0|727_0|1454_0|0_507|727_507|1454_507:fill=0xeeeeee' \
  -frames:v 1 -threads 2 -update 1 contact-sheet.png
```
