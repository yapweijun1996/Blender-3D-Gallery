# Civic/vehicle 06 C: geometry and test corrections

All assets are original illustrative geometry, not operational equipment, certified transport/accessibility systems, religious-function specifications or copies of real landmarks. Independent semantic types follow the assigned exact backlog IDs.

## Fixed limits

Small props: 18,000 triangles and 800,000 bytes. Architectural shells: 30,000 triangles and 1,500,000 bytes. MRT carriage: 80,000 triangles/5,000,000 bytes/320 primitives; public bus: 60,000/4,000,000/240; cargo truck: 50,000/3,000,000/180. Limits were selected before generation and were not raised after failures.

## Preserved failures and bounded corrections

- Pallet intersecting coplanar deck ribs were replaced with non-overlapping rib segments, retaining actual open deck cells and fork channels.
- Blackboard rails now meet stiles without overlapping coplanar faces. Panels remain depth-separated and slide 900mm.
- Fish-counter side/back/well intersections were trimmed to inside wall faces; original and intermediate seam evidence is retained.
- Drill-press depth initially measured .74m against its fixed .70m design. Table depth and motor placement were corrected, not the expected dimensions. Spindle moves 100mm with clearance.
- Five-foot arcade thresholds initially spanned 6.2m against 6m design. Edge threshold placement was corrected; rear piers end below their header.
- Kampung veranda posts now reach the pitched roof and have independent rail balusters. Mosque/church wall joints were trimmed to inner faces; generic layouts remain illustrative.
- Vehicle interiors gained independent seat supports. Truck cab floor was raised clear of tires and shortened to its original length envelope; mirrors are attached to moving doors. Doors have actual apertures, not a hidden solid side/rear wall.
- Vehicle end/side headers fill unintended body gaps. Window bands end between posts instead of overlapping their end faces. Vehicle renders use projected bounds for useful front views, with an additional side view.

## Test corrections without relaxed contracts

The initial pallet vertical probe hit a hollow support-block wall at x=.058, not a deck opening. The corrected independent probe at x=.03 passes through an actual deck cell to the bottom runner. Fork-channel and exact component-count assertions remain.

The first vehicle ground-contact test transformed local bounding boxes and therefore overestimated rotated tire depth. It now uses precise transformed mesh vertices via Box3.setFromObject(..., true). Radius-derived contact tolerance is unchanged: r*(1-cos(pi/32))+.00002m, based on the original 32-sided tire geometry. Raw half-turn midpoint, return endpoints, total angular travel, all axle coordinates, 61 sampled tyre/door-vs-fixed clearances and open-aperture raycasts are independently checked. These clips demonstrate a half-turn then reverse, not continuous wheel spin or driving simulation.

Physical Android/iOS and Safari/WebKit remain untested. The Gallery does not provide generic component animation controls. No production deployment is claimed. Final hashes and pass/fail results are recorded in each asset's reports, not inferred from these design notes.
