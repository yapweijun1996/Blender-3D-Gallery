export const shopfrontAssets = [
  { id: 'glazing', path: 'models/mall-glass-partition/exports/mall-glass-partition.glb' },
  { id: 'door', path: 'models/mall-shopfront-door/exports/mall-shopfront-door.glb' },
  { id: 'fasciaWide', path: 'models/mall-fit-finishes/exports/mall-shopfront-fascia-210.glb' },
  { id: 'fasciaNarrow', path: 'models/mall-fit-finishes/exports/mall-shopfront-fascia-120.glb' },
];

export const shopfrontZ = -1.2;
export const fasciaBaseY = 2.4;

// A partition and a door meet when their centres are 0.60 + 1.05 m apart.
export const shopfrontBays = [
  { x: -3.30, opening: 'glazing', fascia: 'fasciaNarrow' },
  { x: -1.65, opening: 'door', fascia: 'fasciaWide' },
  { x: 0, opening: 'glazing', fascia: 'fasciaNarrow' },
  { x: 1.65, opening: 'door', fascia: 'fasciaWide' },
  { x: 3.30, opening: 'glazing', fascia: 'fasciaNarrow' },
];
