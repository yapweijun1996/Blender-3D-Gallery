#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
test ! -e unit-fixture-latest
mkdir unit-fixture-latest
tar -C repo --exclude='./.git' --exclude='./node_modules' --exclude='./dist' --exclude='./docs/verification/sgmy-fifty-06/integration' --exclude='./docs/verification/sgmy-fifty-06/latest-main' -cf - . | tar -C unit-fixture-latest -xf -
ln -s /srv/agent-workstation/workspaces/blender-event-booth-20261112/repo/node_modules unit-fixture-latest/node_modules
cd unit-fixture-latest
npm test
