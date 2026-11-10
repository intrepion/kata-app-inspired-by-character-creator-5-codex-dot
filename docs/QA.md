# Persona Forge release QA

Verified 2026-11-10 in Chrome using a running localhost HTTP server. No files were opened as `file://` pages.

## Results

- `npm run check`: syntax checks and all 9 Node tests passed.
- `npm run build`: static build passed.
- `/tests/browser.html`: all 16 browser assertions passed, including editable project import/export, malformed input preservation and autosave restoration after reload.
- Desktop screenshot visually reviewed. Responsive layout inspected in a real 390px-wide iframe, served from `/tests/layout.html`; narrow screenshot is the viewport capture cropped to that iframe, not a resized desktop mockup.
- Form labels and controls present in browser accessibility tree; controls remain in the stacked responsive layout.

## Test details

Browser harnesses exercise DOM events and compare real rendered canvas pixels. Export assertions intercept browser object URLs to inspect actual generated Blobs. Imports use programmatically constructed FileLists. Native OS file pickers, actual downloaded-file round trips, physical touch/pen devices, screen readers and Safari/Firefox were not exercised.

Short test settling delays initially produced false failures under background-tab throttling. They now allow 1500ms for canvas rendering/PNG encoding. Persona imports also recreate each FileList after the app clears the input, matching file reselection.

## Fixes in this pass

- Fixed missing word spacing in narrow-layout headings.
- Patina Lab now autosaves keyboard orbit, matching mouse orbit, with a passing regression assertion.

## Scope

See README for deliberately limited modeling/texturing scope. The previews use custom Canvas renderers, not production 3D engines. Downstream professional 3D application compatibility has not been tested. Screenshots are actual localhost app captures.
