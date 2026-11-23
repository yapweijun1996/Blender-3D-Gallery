/** The interaction families advertised by the model library. */
export function interactionKind(asset) {
  switch (asset.id) {
    case "interactive-shopping-cart": return "cart";
    case "mall-ride-hail-pickup-bay": return "pickup-bay";
    case "loh-hei-yee-sang-platter": return "loh-hei";
    case "malaysia-rail-reload-counter": return "rail-reload";
    case "mall-carpark-help-point": return "carpark-help";
    case "ramadan-bazaar-air-balang-stall": return "air-balang";
    case "wet-market-coconut-scraper": return "coconut-scraper";
    case "gjh-mall-visitor-v2": return "visitor-v2";
    case "gjh-visitor-v3": return "visitor-v3";
    default: return asset.collectionId === "singapore-fish" ? "fish" : null;
  }
}
