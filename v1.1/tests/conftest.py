"""Pytest configuration for v1.1 test suite."""

import sys
from pathlib import Path

V1_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = V1_ROOT.parent

if str(V1_ROOT) not in sys.path:
    sys.path.insert(0, str(V1_ROOT))

# Ensure root packages (paper_setting_core etc.) are in sys.path
for pkg in ["packages/core/src", "packages/runtime/src", "packages/contracts", "apps/api/src"]:
    p = str(WORKSPACE_ROOT / pkg)
    if p not in sys.path:
        sys.path.insert(1, p)
