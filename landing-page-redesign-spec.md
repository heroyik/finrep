# Landing Page Redesign Spec

## Overview

Replace `public/index.html` (the FinRep landing page) with a redesigned version based on the existing `~/proj/heroyik.github.io/index.html` design, adapted for FinRep-specific content and redirecting to `https://heroyik.gitlab.io/finrep/`.

## Source Reference

- **Source**: `~/proj/heroyik.github.io/index.html` — the current GitHub Pages landing page announcing the move to GitLab
- **Target**: `public/index.html` — the FinRep project's landing page on GitHub Pages

## Design

### Visual Style

- **Theme**: Dark mode
- **Background**: Dark gradient with green radial glow at top-left
- **Panel**: Semi-transparent dark card with subtle border
- **Colors**:
  - `--bg`: `#101114`
  - `--panel`: `#181a20`
  - `--text`: `#f5f2ea`
  - `--muted`: `#b8b1a3`
  - `--accent`: `#48f0a4` (green)
  - `--accent-strong`: `#1fd67f`
  - `--line`: `rgba(245, 242, 234, 0.18)`
- **Font**: Inter, ui-sans-serif, system-ui stack
- **Layout**: Centered card layout, max-width 680px

### Brand Icons

- **GitHub icon**: SVG path (currentColor fill)
- **GitLab icon**: SVG with official GitLab colors (red `#e24329`, orange `#fc6d26`, `#fca326`)
- **Arrow**: Green (`currentColor` with `#48f0a4` accent), connecting GitHub → GitLab with drop-shadow glow
- **Icon sizes**: 44px × 44px for brand icons, responsive arrow width

### Interactivity

- **Button hover**: Background changes to `--accent-strong`, slight upward translate
- **Auto-redirect**: 10-second delay via meta refresh and JavaScript fallback
- **Button**: Direct link to `https://heroyik.gitlab.io/finrep/`

## Content

### Page Title
```
FinRep - GitLab era
```

### Eyebrow (label above headline)
```
New spot just dropped
```

### Headline (h1)
```
GitLab era.
```

### Body (lede)
FinRep-specific version of the casual-toned announcement. Example tone:
> "Big love, GitHub. You held it down. As of June 10, 2026,
> FinRep is pulling up at **heroyik.gitlab.io/finrep** now. Chill
> for 10 seconds and I will slide you over."

Key changes from source:
- "heroyik" → "FinRep" (message is FinRep-specific)
- URL reference includes `/finrep` path

### Button Text
```
Pull up on GitLab now
```

### Note (below button)
```
Ten seconds is optional. The new spot is already live.
```

## Technical Specifications

### Redirect Configuration

- **Redirect URL**: `https://heroyik.gitlab.io/finrep/` (with trailing slash)
- **Mechanism**:
  1. `<meta http-equiv="refresh">` with 10-second delay
  2. JavaScript `setTimeout` → `window.location.assign()` fallback after 10 seconds
- **Manual redirect**: Button link with `href="https://heroyik.gitlab.io/finrep/"`

### Content Security Policy (CSP)

Keep CSP and add `https://heroyik.gitlab.io` to allowed sources:

```
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'
```

Note: `form-action 'self'` should be added since the redirect URL (`heroyik.gitlab.io`) is an external origin. However, for a simple redirect page, the CSP primarily needs `default-src 'self'` with `style-src 'unsafe-inline'`. The meta refresh and JavaScript redirect do not require `connect-src` or `form-action` allowances since they navigate via `location.assign()` and `<a href>`.

### SEO / Meta

- `<meta charset="utf-8">`
- `<meta name="viewport" content="width=device-width, initial-scale=1.0">`
- No `meta description` needed (redirect page, not indexed)

### Performance

- No external font loading (use system font stack)
- No external dependencies
- Inline SVG icons (no external image loads)
- Minimal CSS (no animation beyond hover transitions)
- Inline JavaScript for redirect fallback

### Accessibility

- `aria-label` on icon row
- `role="img"` on SVGs
- `aria-hidden="true"` on decorative arrow
- Button is a proper `<a>` element with `href`
- Sufficient color contrast on all text

### Responsive Design

- Uses `clamp()` for font sizes and spacing
- `min(100%, 680px)` for card width
- `place-items: center` for vertical + horizontal centering
- Padding uses `clamp(28px, 6vw, 56px)` for responsive inner spacing

## Key Differences from Source

| Aspect | Source (heroyik.github.io) | Target (finrep) |
|--------|---------------------------|-----------------|
| Page title | `heroyik moved` | `FinRep - GitLab era` |
| Redirect URL | `heroyik.gitlab.io/` | `heroyik.gitlab.io/finrep/` |
| Message scope | heroyik (account-wide) | FinRep-specific |
| Body text | "heroyik is pulling up at..." | "FinRep is pulling up at..." |
| URL in body | heroyik.gitlab.io | heroyik.gitlab.io/finrep |

## Implementation Scope

- **File to modify**: `public/index.html` (replace entire content)
- **File to create**: None (single-file page)
- **No other files affected**: The redirect page is standalone

## Open Questions / Future Considerations

- Consider adding `data-redirect-now` attribute (as in source) for the redirect.js script if needed later
- External `redirect.js` script (`/assets/js/redirect.js`) is referenced in the source but may not be needed for a simple implementation; can inline the logic
