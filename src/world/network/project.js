import { project as projectRoute } from '../../drive/route.js';

export const ORIGIN = Object.freeze({ lat: 1.2834, lon: 103.8607 });

/** Project [longitude, latitude] in WGS84 to [x east, z south] in local metres. */
export const project = projectRoute;

export function projectOsm({ lon, lat }) {
  return project([lon, lat]);
}
