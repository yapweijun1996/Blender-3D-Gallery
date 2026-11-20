// Route maths for the Marina Bay to Johor Bahru drive. Pure functions, no three.js, so they are unit tested.
const LAT0 = 1.2834, LON0 = 103.8607;
const M_PER_DEG_LAT = 110574;
const M_PER_DEG_LON = 111320 * Math.cos(LAT0 * Math.PI / 180);

/** WGS84 degrees to local metres: x east, z south (so north is -z, like a map seen from above). */
export const project = ([lon, lat]) => [(lon - LON0) * M_PER_DEG_LON, -(lat - LAT0) * M_PER_DEG_LAT];

/** Resample a polyline at an even spacing and add heading and cumulative distance. */
export function buildRoute(data, spacing = 6, metres = null) {
  const raw = metres ?? data.coordinates.map(project);
  const points = [];
  let carry = 0;
  let [x, z] = raw[0];
  points.push({ x, z, s: 0 });
  for (let i = 1; i < raw.length; i++) {
    const [nx, nz] = raw[i];
    const length = Math.hypot(nx - x, nz - z);
    let at = spacing - carry;
    while (at <= length) {
      const t = at / length;
      points.push({ x: x + (nx - x) * t, z: z + (nz - z) * t, s: 0 });
      at += spacing;
    }
    carry = length - (at - spacing);
    x = nx; z = nz;
  }
  points.push({ x, z, s: 0 });
  for (let i = 1; i < points.length; i++) points[i].s = points[i - 1].s + Math.hypot(points[i].x - points[i - 1].x, points[i].z - points[i - 1].z);
  for (let i = 0; i < points.length; i++) {
    const a = points[Math.max(0, i - 2)], b = points[Math.min(points.length - 1, i + 2)];
    const dx = b.x - a.x, dz = b.z - a.z, l = Math.hypot(dx, dz) || 1;
    points[i].tx = dx / l; points[i].tz = dz / l;
    points[i].heading = Math.atan2(dx, dz);
  }
  const length = points.at(-1).s;
  const roads = data.roads.map(road => ({ ...road, from_m: Math.min(road.from_m, length) }));
  return { points, length, roads, spacing: points.length > 1 ? points[1].s : spacing };
}

/** Resample a polyline given in local metres (x east, z south) into the same route structure as buildRoute. */
export function polylineRoute(raw, roads = [{ name: "Road", from_m: 0 }], spacing = 4) {
  return buildRoute({ coordinates: [], roads }, spacing, raw);
}

/** Pose at a distance along the route, with an optional sideways offset (positive = to the left of travel). */
export function sample(route, distance, offset = 0) {
  const d = Math.max(0, Math.min(route.length, distance));
  // Chords around bends are a little shorter than the arc spacing, so search by distance.
  let low = 0, high = route.points.length - 2;
  while (low < high) {
    const middle = (low + high + 1) >> 1;
    if (route.points[middle].s <= d) low = middle; else high = middle - 1;
  }
  const index = low;
  const a = route.points[index], b = route.points[index + 1];
  const t = (d - a.s) / ((b.s - a.s) || 1);
  const tx = a.tx + (b.tx - a.tx) * t, tz = a.tz + (b.tz - a.tz) * t;
  const l = Math.hypot(tx, tz) || 1;
  const nx = -tz / l, nz = tx / l; // left of travel when z points south
  const x = a.x + (b.x - a.x) * t, z = a.z + (b.z - a.z) * t;
  return { x: x + nx * offset, z: z + nz * offset, heading: Math.atan2(tx, tz), tx: tx / l, tz: tz / l, index };
}

/** Closest route distance to a world position, searching a window around a previous distance. */
export function locate(route, x, z, near = 0, window = 400) {
  const from = Math.max(0, Math.floor((near - window) / route.spacing));
  const to = Math.min(route.points.length - 1, Math.ceil((near + window) / route.spacing));
  let best = Infinity, distance = near, lateral = 0;
  for (let i = from; i <= to; i++) {
    const p = route.points[i];
    const dx = x - p.x, dz = z - p.z, d2 = dx * dx + dz * dz;
    if (d2 < best) { best = d2; distance = p.s; lateral = dx * -p.tz + dz * p.tx; }
  }
  return { distance, lateral, off: Math.sqrt(best) };
}

export function roadAt(route, distance) {
  let current = route.roads[0];
  for (const road of route.roads) if (road.from_m <= distance) current = road; else break;
  return current;
}

/** Distance of the first road whose name contains the text, or undefined. */
export function findRoad(route, text) {
  return route.roads.find(road => road.name.toLowerCase().includes(text.toLowerCase()))?.from_m;
}

/** Day clock for the trip: 17:30 at the start to 19:45 at the end, as hours. */
export const tripHour = (route, distance) => 17.5 + 2.25 * Math.max(0, Math.min(1, distance / route.length));
