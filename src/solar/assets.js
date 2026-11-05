// Scene identities and physical facts stay with the solar collection; gallery
// assets own the geometry, source notes and attribution for each replacement.
const replacements = {
  sun: 'nasa-sun', mercury: 'nasa-mercury', venus: 'nasa-venus',
  earth: 'nasa-earth', mars: 'nasa-mars', jupiter: 'nasa-jupiter',
  saturn: 'nasa-saturn', uranus: 'nasa-uranus', neptune: 'nasa-neptune',
  moon: 'nasa-moon', pluto: 'nasa-pluto', 'asteroid-01': 'nasa-vesta',
  'asteroid-02': 'nasa-eros', comet: 'nasa-tempel-1',
};

export function solarSceneAssets(catalogAssets) {
  const byId = new Map(catalogAssets.map(a => [a.id, a]));
  return catalogAssets.filter(a => a.family === 'solar-system').map(base => {
    const replacementId = replacements[base.solarId];
    if (!replacementId) return base;
    const source = byId.get(replacementId);
    if (!source?.details) throw new Error(`Missing solar model: ${replacementId}`);
    return {
      ...base,
      id: source.id,
      file: source.file,
      name: base.solarId === 'asteroid-01' ? 'Vesta' : base.solarId === 'asteroid-02' ? 'Eros' : base.solarId === 'comet' ? 'Comet 9P/Tempel 1' : base.name,
      details: { ...source.details, scientific_properties: base.details.scientific_properties },
      // NASA Saturn's model is normalized to the ring diameter, not the planet.
      modelScale: base.solarId === 'saturn' ? 2.330901 : 1,
    };
  });
}
