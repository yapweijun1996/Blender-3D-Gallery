/** The interaction families advertised by the model library. */
export function interactionKind(asset) {
  switch (asset.id) {
    case "interactive-shopping-cart": return "cart";
    case "mall-ride-hail-pickup-bay": return "pickup-bay";
    case "loh-hei-yee-sang-platter": return "loh-hei";
    case "gjh-mall-visitor-v2": return "visitor-v2";
    case "gjh-visitor-v3": return "visitor-v3";
    default: return asset.collectionId === "singapore-fish" ? "fish" : null;
  }
}
