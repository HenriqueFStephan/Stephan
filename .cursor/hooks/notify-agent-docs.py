#!/usr/bin/env python3
"""
Inject navigation hint when agents edit core backend/frontend paths.

Hook: afterFileEdit
"""

import json
import sys
from pathlib import Path

WATCH_PREFIXES = (
    "backend/app/api/",
    "backend/app/services/",
    "agents/",
    "frontend/src/app/features/",
)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    file_path = data.get("file_path", "") or data.get("path", "") or ""
    normalized = file_path.replace("\\", "/")

    for prefix in WATCH_PREFIXES:
        if prefix in normalized:
            studio = ""
            if "frontend/src/app/features/" in normalized and "/studio/" not in normalized:
                studio = (
                    " If this edit changes a public page, its copy, or its layout, "
                    "update /studio in the same change. Follow "
                    ".cursor/skills/studio-mode/SKILL.md."
                )
            print(
                json.dumps(
                    {
                        "additional_context": (
                            "Stephan: After editing this path, consider updating "
                            "docs/AGENT_NAVIGATION.md if you added a new module. "
                            "See docs/ARCHITECTURE.md for patterns."
                            + studio
                        )
                    }
                )
            )
            return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
