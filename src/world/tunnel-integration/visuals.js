import { BoxGeometry, BufferAttribute, BufferGeometry, DoubleSide, Group, InstancedMesh, Matrix4,
  Mesh, MeshBasicMaterial, MeshLambertMaterial } from "three";
import { tunnelMarkings } from "../tunnel-prototype/geometry.js";
import { groundSurface, splitGroundBounds } from "./ground.js";

const ROAD_Y = .03;
const MARKINGS_Y = .031;
const SHARED_MARKINGS_Y = .014;
const WORLD_EXTENT = 60000;

const HARD_SURFACES = {
  road: 0x3b3e43,
  walls: 0x777c7b,
  ceiling: 0x484f57,
  portals: 0x999d91,
  footway: 0x9c9a90,
};

function surfaceBuffer(surfaces) {
  const position = new Float32Array(surfaces.reduce((size, surface) => size + surface.position.length, 0));
  const indices = new Uint32Array(surfaces.reduce((size, surface) => size + surface.indices.length, 0));
  let offset = 0, cursor = 0;
  for (const surface of surfaces) {
    position.set(surface.position, offset);
    for (const index of surface.indices) indices[cursor++] = index + offset / 3;
    offset += surface.position.length;
  }
  const buffer = new BufferGeometry();
  buffer.setAttribute("position", new BufferAttribute(position, 3));
  buffer.setIndex(new BufferAttribute(indices, 1));
  buffer.computeVertexNormals();
  return buffer;
}

function roofFixtures(geometry, material) {
  const rows = [];
  let next = geometry.coveredFrom + 3;
  for (const row of geometry.alignment.link) {
    if (row.s > geometry.coveredTo - 3) break;
    if (row.s < next) continue;
    rows.push(row);
    next = row.s + 11;
  }
  const fixtures = new InstancedMesh(new BoxGeometry(1.5, .075, .25), material, rows.length);
  const matrix = new Matrix4();
  for (const [index, row] of rows.entries()) {
    matrix.makeRotationY(Math.atan2(row.tx, row.tz));
    matrix.setPosition(row.x, row.y + geometry.clearance - .065, row.z);
    fixtures.setMatrixAt(index, matrix);
  }
  fixtures.instanceMatrix.needsUpdate = true;
  fixtures.computeBoundingSphere();
  return fixtures;
}

/** Prepare an unattached scene group. The page retains ownership of its daylight ground material. */
export function createFortCanningVisuals(geometry, groundMaterial) {
  const group = new Group();
  group.name = "Fort Canning Link";
  const materials = new Set();
  const own = material => { materials.add(material); return material; };
  function add(name, mesh, height = 0) {
    mesh.name = name;
    mesh.position.y = height;
    group.add(mesh);
  }

  for (const [id, color] of Object.entries(HARD_SURFACES)) {
    const surfaces = geometry.surfaces.filter(surface => surface.id === id);
    if (!surfaces.length) continue;
    const material = own(new MeshLambertMaterial({ color, side: DoubleSide }));
    add(id, new Mesh(surfaceBuffer(surfaces), material), id === "road" ? ROAD_Y : 0);
  }
  const cover = geometry.surfaces.filter(({ id }) => id === "terrain" || id === "cover");
  add("apron-and-cover", new Mesh(surfaceBuffer(cover), groundMaterial));

  // The old moving plane would pass through the open cut. Keep the surrounding grass at the apron datum.
  const outer = { minX: -WORLD_EXTENT, maxX: WORLD_EXTENT, minZ: -WORLD_EXTENT, maxZ: WORLD_EXTENT };
  const outside = groundSurface(splitGroundBounds(outer, geometry.bounds));
  add("exterior-ground", new Mesh(surfaceBuffer([outside]), groundMaterial));

  const { link, penang, downstream, widths, profile } = geometry.alignment;
  const markings = [
    tunnelMarkings({ width: widths.link, lanes: profile.lanes }, link),
    tunnelMarkings({ width: widths.penang, lanes: widths.penang / profile.laneWidth }, penang),
    tunnelMarkings({ width: widths.downstream, lanes: widths.downstream / profile.laneWidth }, downstream),
  ];
  const paint = own(new MeshBasicMaterial({ color: 0xece7cf, side: DoubleSide }));
  // Road paint sits above the asphalt and below the streamed tile's junction surface.
  add("lane-markings", new Mesh(surfaceBuffer(markings), paint), MARKINGS_Y - SHARED_MARKINGS_Y);

  const lamp = own(new MeshBasicMaterial({ color: 0xffe5b4 }));
  add("roof-lighting", roofFixtures(geometry, lamp));

  let disposed = false;
  return {
    group,
    dispose() {
      if (disposed) return;
      disposed = true;
      group.removeFromParent();
      for (const mesh of group.children) {
        mesh.geometry.dispose();
        if (mesh.isInstancedMesh) mesh.dispose();
      }
      for (const material of materials) material.dispose();
      group.clear();
    },
  };
}
