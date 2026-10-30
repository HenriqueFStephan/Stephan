---
name: studio-mode
description: >-
  Keep /studio in step with the public site. Use on every GitHub issue labeled
  solve, on every [CORRECTION], and whenever a change alters a public page,
  its copy, or its layout.
---

# Studio mode

`/studio` is the hidden creative overlay. It frames the live site (`iframe src="/"`) and files a GitHub issue labeled `solve`. There is no second copy of page content inside the studio feature.

On every `solve` and every `[CORRECTION]` that changes what a visitor sees, update studio mode in the same change. Do this even when the issue never mentions studio.

- The framed pages are the real routes. A change to a public page, its copy, or its layout is the studio update for that page.
- If that change would leave the overlay, its copy, or its layout behind the pages it frames, update `frontend/src/app/features/studio/` in the same change. Check the panel, the snip layer, and the gate against the new page.
- Confirm `/studio` still shows the changed page inside the frame, with the header and footer the visitor sees on that route.
- Do not add `/studio` to the public header or footer.
- Do not put studio tokens in the frontend. Secrets stay in `debt.txt` and Render.

A backend-only change, a research briefing, or a `[POST]` does not need a studio edit.
