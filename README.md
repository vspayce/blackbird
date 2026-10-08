# The Black Bird

A Sherlock Holmes mystery for the browser, built for phones in landscape and
playable on desktop. San Francisco, 1895: Holmes and Watson's host, the
detective Miles Archer, is shot dead in a foggy alley. It's the story of
Hammett's *The Maltese Falcon*, with Holmes on the case.

Explore the scene in 3D. Use **Focus** to slow time and see what everyone else
missed. Examine the body, question the police, then piece the facts together
in the **Mind Palace** and name the killer.

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build in dist/
```

Pushing to `main` publishes to https://vspayce.github.io/blackbird/ via `.github/workflows/deploy.yml`
(Settings → Pages → Source must be "GitHub Actions").

Controls: touch stick on the left, drag to look, context button to examine or
talk, eye button for Focus. On desktop: WASD, mouse drag, E, F, B (casebook),
M (Mind Palace).

See `DESIGN.md` for the design, story plan and code layout.

## Characters

The cast is built in Blender by `art/build_characters.py` (edit the `CAST`
table for looks). It saves `art/characters.blend` and exports
`public/models/<name>.glb`, which the game loads:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup \
  --python art/build_characters.py -- --render preview.png
```
