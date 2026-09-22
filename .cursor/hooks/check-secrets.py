#!/usr/bin/env python3
"""
Warn when prompts may contain secret patterns before submission.

Hook: beforeSubmitPrompt
Returns allow by default; asks permission if suspicious patterns found.
"""

import json
import re
import sys

PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",
    r"password\s*=\s*['\"][^'\"]+['\"]",
    r"api[_-]?key\s*=\s*['\"][^'\"]+['\"]",
]


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        print(json.dumps({"permission": "allow"}))
        return 0

    prompt = data.get("prompt", "") or data.get("user_message", "") or ""
    for pattern in PATTERNS:
        if re.search(pattern, prompt, re.IGNORECASE):
            print(
                json.dumps(
                    {
                        "permission": "ask",
                        "user_message": "Possible secret detected in prompt. Confirm before sending.",
                        "agent_message": "Hook flagged a pattern that looks like an API key or password.",
                    }
                )
            )
            return 0

    print(json.dumps({"permission": "allow"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
