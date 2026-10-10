#!/usr/bin/env python3
"""List V3 visual presets for user selection."""
from build_hybrid_hyperframes_project import STYLE_PRESETS
for key, value in STYLE_PRESETS.items():
    print(f"{key}\t{value['label']}")
