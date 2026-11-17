"""Generate both detail levels, save native source and render the exported fixture."""
from pathlib import Path
import sys

ASSET_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ASSET_DIR.parents[1] / "scripts"))
from mall_lighting_delivery import deliver
from mall_rail_cove_uplight import cove

if __name__ == "__main__":
    deliver(ASSET_DIR, "ASSET_MallCoveLedStrip", cove, (3.4, 1.45, -1.05))
