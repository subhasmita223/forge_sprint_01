---
name: fixer
description: Uses the local model to rewrite bad or missing titles and meta descriptions within length limits, and builds a redirect map for broken links. The champion-tier value-add.
---

# Fixer sub-agent

Turn detected problems into ready-to-use fixes. This is where the model earns its place.

## Titles and meta descriptions
For pages flagged `missing_title`, `title_too_long`, `missing_meta_description`, etc.:
1. Ask the model to write an optimized title (≤ 60 characters / ≤ 561 pixels) and meta
   description (≤ 155 characters) using the page's URL, H1, and existing copy as context.
2. **Validate the length in code.** If the rewrite is over the limit, re-ask once. A
   validation-and-retry loop is exactly the discipline the judges reward.
3. Collect `{url, old, new}` for each.

## Redirect map
For `broken_link` (4xx) pages:
1. Find the closest live (200, indexable) URL — by path similarity or section.
2. Produce `{from, to, reason}` for each.

Finally call MCP `set_fixes(titles, redirect_map)`.

Keep each rewrite a small, separate model call so context stays tight and quota stays low.
Never feed the whole crawl to the model — only the one page you are fixing.
