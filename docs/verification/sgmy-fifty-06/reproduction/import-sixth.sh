#!/bin/bash
set -e
python3 import-tranche.py /srv/agent-workstation/workspaces/blender-fifty06-mall-vehicle-20261113/repo d9d69a457bc4ab45c77aa9b8058873a9448a8745 mall 9f80a8f2d5ee69d8ac7b23f88191960ce195f110
python3 import-tranche.py /srv/agent-workstation/workspaces/blender-fifty06-health-architecture-20261113/repo c5599b17891fc97da57295782305bdae5d7a8511 health 349cd1f6e1faa0d045b2ae738f2869c6b0ac943a
python3 import-tranche.py /srv/agent-workstation/workspaces/blender-fifty06-civicvehicles-20261113/repo d9d69a457bc4ab45c77aa9b8058873a9448a8745 civic fb8c6a0a7e40f72e8353157632050d19712324b5
python3 verify-imports.py
