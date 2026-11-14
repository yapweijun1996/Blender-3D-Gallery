# Passenger Lift (005)

Original illustrative two-stop cutaway asset. Source `sources/passenger-lift.blend`, generator `generate.py`, export `exports/passenger-lift.glb`. Metres, Blender +Z up/-Y front to glTF +Y up/+Z front.

## Animation contract
Play the four DOOR_Cycle clips together at bottom OR TRAVEL_Cab alone. Never play both modes simultaneously. Top landing doors remain static. Cab travels 3m with doors closed. Not operational or safety-certified equipment, no control simulation or Gallery animation UI.

Run `node models/passenger-lift/validate.mjs` for fixed budgets, raw tracks and actual 121-pose clearances per mode; `MALL_QA_DIR=... node models/passenger-lift/browser-motion.mjs` for isolated Chromium motion and consumed-SHA proof. Physical mobile and WebKit untested.
