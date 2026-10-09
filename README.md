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

With a controller (Xbox, PlayStation or MFi, through the browser's Gamepad
API): left stick walk, right stick look, Ⓐ act / confirm, Ⓑ back, Ⓧ Focus,
Ⓨ Mind Palace, ☰ Notebook, LB/RB flip notebook tabs; in menus the d-pad or
left stick moves the highlight. The first press only switches to controller
mode. To play on a TV, run it in Safari on a Mac with the controller paired to
the Mac and AirPlay the screen to the Apple TV.

See `DESIGN.md` for the design, story plan and code layout.
See `docs/SETUP.md` for the full setup: tools, Blender add-ons and asset packs, MCP, build scripts and testing.

## Characters

The cast is realistic MakeHuman characters built in Blender by
`art/build_humans.py` (looks are in its `CAST` table): body and face shaping,
period clothes fitted to each body, the game rig and Idle / Walk / Talk /
LieBack clips. It saves `art/humans/<name>.blend` and exports
`public/models/<name>.glb`. It needs the MPFB extension and MakeHuman asset
packs; setup is described at the top of the script. See `CREDITS.md`.

```bash
BLENDER_USER_CONFIG=art/.blender-config /Applications/Blender.app/Contents/MacOS/Blender -b \
  --python art/build_humans.py -- --only holmes
```

## The set

Burritt Alley and Bush Street are built by `art/build_set.py` (no add-ons
needed), which saves `art/set/burritt.blend` and exports
`public/models/burritt.glb`. `src/world/alley.js` keeps the layout and
colliders and falls back to plain boxes if the model is missing.

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/build_set.py
```

## The Mark Hopkins Institute (preview)

`art/build_hopkins.py` builds the Hopkins mansion on Nob Hill as it was in 1895,
the San Francisco Art Association's Institute: exterior, grounds and the whole
ground floor plus the tower observatory. It writes `public/models/hopkins.glb`
and `hopkins.json` (colliders, rooms, lamps, interactions). The night city
below is generated in `src/world/hopkins.js`. The script's header separates
what is historical from what is invented (notably the floor plan).

Chapter IV, *The Fat Man*, is set there: `?chapter=4`, or the title screen's
**Scenes** button. `?scene=hopkins` walks the house freely with no case;
`?skip=1` starts Chapter I without the intro.

## Kearny Street (Chapter V)

`art/build_city.py` builds Kearny Street from Market to Bush with Sutter Street
running off either side and a cable car that runs along it
(`public/models/kearny.glb` + `kearny.json`: colliders, lamps, cover points and
named places). Chapter V: `?chapter=5`.

## Saving

The game autosaves as you play; the pause menu (Menu, Esc or the controller's
View button) has three save slots, loading, and a save code to move a save
between devices. Continue on the title resumes the latest save.

## The Palace Hotel (Chapter II)

`art/build_palace.py` builds Holmes's suite at the Palace Hotel (it borrows the
Hopkins builder's furniture). Chapter II: `?chapter=2`.

## The St. Mark Hotel (Chapter III)

`art/build_stmark.py` builds Brigid O'Shaughnessy's suite (it borrows the Hopkins
and Palace builders' pieces). Chapter III: `?chapter=3`.
