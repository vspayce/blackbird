# How The Black Bird is built: the setup

Everything it took to build and publish this game, as it stands in October
2026: the tools, the Blender add-ons and asset packs, the MCP servers Claude
Code talks to, how each kind of asset is made, and the traps we fell into.
Written for whoever sets this up next (including a future Claude session).

---

## 1. The stack at a glance

| Layer | What | Why |
|---|---|---|
| Game | [three.js](https://threejs.org) 0.186, plain JavaScript modules | Runs in any phone browser from a link; no install, no app store |
| Build | [Vite](https://vitejs.dev) 8 | Dev server with hot reload; bundles to `dist/` |
| Hosting | GitHub Pages via GitHub Actions | Every push to `main` deploys to https://vspayce.github.io/blackbird/ |
| 3D content | Blender 5.2, driven by Python scripts in `art/` | Models are *generated*, so they can be rebuilt and changed in code |
| Characters | MPFB (MakeHuman for Blender) + MakeHuman asset packs | Realistic, rigged human bodies with free-to-use assets |
| Testing | Playwright with headless Chromium | Screenshots of the real game for checking changes |
| Assistant | Claude Code (Opus 5.5), with Blender MCP connected | Wrote the code, ran Blender, checked the renders |

It is **not** a Unity project. Unity MCP is configured on this machine but
nothing here uses it.

## 2. Machine and tools

Versions this was built with (macOS 27, Apple silicon):

| Tool | Version | Install |
|---|---|---|
| Node.js | 26.8 | `brew install node` |
| npm | 11.19 | comes with Node |
| git | 2.54 | Xcode command line tools |
| GitHub CLI `gh` | 2.100 | `brew install gh`, then `gh auth login` |
| Blender | 5.2.1 LTS | blender.org, installed in `/Applications/Blender.app` |
| uv | any recent | `brew install uv` (runs the Blender MCP server) |
| Python | the one inside Blender | nothing to install; the scripts run in Blender's Python, which has numpy |

Blender's command line lives inside the app bundle. It is not on the PATH, so
the scripts are always run as:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b ...
```

## 3. The game: run, build, publish

```bash
npm install
npm run dev        # http://localhost:5173 (also on your LAN, for testing on a phone)
npm run build      # production build in dist/
```

**Publishing.** `.github/workflows/deploy.yml` builds and deploys on every push
to `main`. GitHub Pages must be switched on with *GitHub Actions* as the
source. That was missing at first, so the first deploys failed with
`Failed to create deployment (status: 404)`. It was fixed with:

```bash
gh api -X POST repos/vspayce/blackbird/pages -f build_type=workflow
```

`vite.config.js` sets `base: './'` so the build works under `/blackbird/`.

**Draco.** The models are Draco-compressed. The decoder is copied from three.js
into `public/draco/` (`draco_decoder.js`, `.wasm`, `draco_wasm_wrapper.js`).
`src/core/gltf.js` is the one shared loader that uses it.

**Testing scenes.** The title screen has a **Scenes** button. The same scenes
are reachable by URL:

- `?skip=1`: Chapter I in Burritt Alley, without the intro
- `?scene=hopkins`: the Mark Hopkins Institute preview

## 4. Claude Code and MCP

Claude Code did the work from a terminal in this folder. Two MCP servers are
configured globally in `~/.claude.json`:

```jsonc
"mcpServers": {
  "blender": {
    "type": "stdio",
    "command": "uv",
    "args": ["run", "--project",
      "/Users/spayce/Library/Application Support/Claude/Claude Extensions/ant.dir.gh.blender.blender-mcp",
      "blender-mcp"]
  },
  "UnityMCP": { "type": "http", "url": "http://127.0.0.1:8080/mcp" }   // not used by this project
}
```

### Blender MCP

There are two halves:

1. **The MCP server** (the `blender` entry above). It came with the Claude
   Desktop extension *blender-mcp* and runs through `uv`. Claude Code launches
   it at startup.
2. **The add-on inside Blender.** Blender Lab's **MCP** add-on (id `mcp`,
   v1.0.3, GPL-3.0, from the `lab.blender.org` extensions repository, needs
   Blender 5.1+). Install it from *Edit → Preferences → Get Extensions*, with
   the Blender Lab repository enabled. Once enabled, a running Blender accepts
   connections from the server.

With both running, Claude can inspect the open Blender file (objects,
collections, save state), run Python in it, take viewport screenshots and
search the bundled API docs.

**How it was used here, and why mostly not.** When this work started, Blender
had a different project open (`Asset_Sugi_Hero.blend`) with **unsaved
changes**. Driving that live session risked those changes. So the MCP was used
only to look (file and object summaries), and every model was built by
running Blender **headless** in separate processes:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/build_set.py
```

That is the recommended way to run these scripts: repeatable, with no
dependence on what is open in the GUI, and runnable in the background. Use
the live MCP connection for poking around a file you have open and are
happy for Claude to touch.

## 5. Blender add-ons and assets

### MPFB (MakeHuman for Blender), for the characters

Installed from the official blender.org extensions repository on the command
line:

```bash
/Applications/Blender.app/Contents/MacOS/Blender -c extension install -s -e mpfb
```

MPFB ships the base human mesh, the rigs (`game_engine` is used here) and the
shaping targets. Skins, eyes, hair and clothes come separately, as
**MakeHuman asset packs**. They are listed at
http://static.makehumancommunity.org/assets/assetpacks.html and downloaded as
zips from `files2.makehumancommunity.org/asset_packs/...`:

| Pack | Licence | Used for |
|---|---|---|
| `makehuman_system_assets` | CC0 | eyes, eyebrows, eyelashes, short hair, shoes, proxies |
| `suits01` | CC0 | `toigo_male_suit_3`, the base suit for everyone; `toigo_female_suit` (Brigid) |
| `hair01` | CC0 | `elvs_reverse_french_braid_bun` (Brigid) |
| `skins02` | CC0 | male skin textures |
| `eyebrows01` | CC0 | extra eyebrows |
| `bodyparts05` | CC0 | beards and moustaches |
| `bodyparts06` | **CC-BY** | `grinsegold_moustache` |
| `hats03` | **CC-BY** | `culturalibre_cl_bowler_hat`, `elvs_male_flat_cap1` |
| `hair02` | **CC-BY** | `elvs_grump_hair` (Holmes, Cairo), `elvs_50s_updo` (Brigid) |
| `gloves01` | CC0 | `toigo_gloves_short` (Brigid's blue gloves) |
| `skins01` | CC0 | `toigo_light_skin_with_natural_makeup` (Brigid) |

Unzip them into MPFB's user data folder:

```
~/Library/Application Support/Blender/5.2/extensions/.user/blender_org/mpfb/data/
```

The CC-BY items must be credited (see `CREDITS.md`).

**A separate Blender config for builds.** Your everyday Blender saves its
preferences when it quits. If MPFB isn't enabled there, that save turns it off
again, and the build then fails with `'NoneType' object is not subscriptable`
inside MPFB's log service. The character builds therefore use their own
config folder, `art/.blender-config/` (git-ignored). Create it once:

```bash
BLENDER_USER_CONFIG=art/.blender-config /Applications/Blender.app/Contents/MacOS/Blender -b \
  --python-expr "import bpy; bpy.ops.preferences.addon_enable(module='bl_ext.blender_org.mpfb'); bpy.ops.wm.save_userpref()"
```

### Fonts

Shop signs use **IM FELL English SC** (SIL Open Font License), downloaded from
the google/fonts repository into `art/fonts/` with its `OFL.txt`. The game's
interface loads the IM Fell family from Google Fonts.

### Paintings

The Hopkins Institute's pictures are real public-domain works by William
Keith, Thomas Hill and Albert Bierstadt, fetched with the Wikimedia Commons
API (category listings, licence checked, 640 px thumbnails) into
`art/paintings/`, along with `credits.json` (title, artist, date, licence,
source page).

## 6. The build scripts

All in `art/`. Each writes a `.blend` you can open and a `.glb` in
`public/models/` that the game loads.

| Script | Builds | Command |
|---|---|---|
| `build_humans.py` | the cast: Holmes, Watson, Polhaus, Kelly, Archer, Gutman, Wilmer, Cairo, Wren, Brigid | `BLENDER_USER_CONFIG=art/.blender-config Blender -b --python art/build_humans.py -- [--only holmes] [--render dir]` |
| `build_set.py` | Burritt Alley and Bush Street | `Blender -b --factory-startup --python art/build_set.py -- [--render prefix]` |
| `build_hopkins.py` | the Mark Hopkins Institute, grounds, street | `Blender -b --factory-startup --python art/build_hopkins.py -- [--render prefix]` |
| `setkit.py` | shared kit for the two set builders | (imported) |

(`Blender` = `/Applications/Blender.app/Contents/MacOS/Blender`.)

**Characters** (`build_humans.py`). For each person in its `CAST` table:

- a MakeHuman body shaped by macros (age, weight, height) and face targets;
- the `game_engine` rig and a `GAMEENGINE` skin material;
- the MakeHuman suit, recoloured by rewriting its texture pixels;
- coats, capes and hats built in the script and fitted to the body by
  ray-casting its silhouette;
- a re-rest with the arms hanging at the sides;
- the suit atlas re-woven (plain wool or tweed, no pinstripe; shirt, tie colour) and every material rebuilt
  for glTF: no clearcoat or stray bump maps, hair and brows alpha-tested, a little sheen on skin and wool;
- the phone budget: the skin hidden under clothes deleted, everything but the face collapse-decimated
  (UV seams kept), about 10-15k triangles a character (the `TRIS` line in the log);
- hand-keyed `Idle`, `Talk`, `LieBack`, `Aim` and `HandsUp` clips, and a `Walk` whose legs are placed by IK
  so the planted foot stays put; its ground speed is stored as `walk_speed` in the glTF extras and
  `figure.js` matches the clip's speed to it (no foot sliding). Gaits: `gent`, `lady` (Brigid), `heavy` (Gutman).

Exported with Draco and JPEG textures, about 1.0 to 1.4 MB each. `--render dir` also writes walk and talk frames.

**Sets** (`build_set.py`, `build_hopkins.py`). Everything is modelled in the
game's own coordinates (Y up, metres) and turned Z-up only at export, so a
position in the script is a position in the game. Geometry is gathered into
one mesh per material, which keeps draw calls low. Textures (brick, ashlar,
clapboard, parquet, Persian rugs, frescoes, book spines) are generated with
numpy. The Hopkins script also writes `hopkins.json`: colliders, rooms, lamp
positions, interaction points and ground levels for the game.

## 7. Testing: screenshots of the real game

Changes were checked by driving the game in headless Chromium with Playwright
and looking at the screenshots. Install it outside the repo (it is not a
project dependency), for example in a scratch folder:

```bash
npm i playwright && npx playwright install chromium
```

Headless Chromium needs software WebGL:

```js
const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
```

The game exposes `window.game`, so a test can place Holmes and the camera
directly (`game.holmes.object.position.set(...)`, `game.yaw`, `game.pitch`)
before taking a screenshot. Software rendering is slow: give each view about
2 seconds to settle, and expect walking to cover less ground than on a real
device. For touch, emulate a phone (`hasTouch: true, isMobile: true`) and
send touch events through a CDP session.

## 8. Traps we fell into (and the fixes)

| Symptom | Cause | Fix |
|---|---|---|
| Pages deploys fail with a 404 | Pages not enabled | `gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow` |
| MPFB missing in a build | everyday Blender saved preferences without it | the separate `BLENDER_USER_CONFIG` (section 5) |
| Characters' second pivot named `body.001` | object names are unique per `.blend` | prefix names per character (`Watson_hips`) |
| Re-rested arms didn't stick | `modifier_apply` does nothing in background mode | bake the evaluated mesh coordinates directly |
| Preview showed the wrong pose | all NLA tracks muted leaves the last evaluated pose | reset pose bones before rendering a rest pose |
| Recolours vanished in the game | glTF only exports a texture wired straight into the shader | rewrite the texture pixels instead of using shader nodes |
| 1.4 million triangles of shop signs | the font's rough letter edges, at full curve resolution | `resolution_u = 2`, then a Decimate at 0.08 |
| Glass hid the shopfronts | glass sat on or behind the wall face | put the glass just proud of the wall |
| Exterior detail built inside the house | the wall normal flipped with the wall's direction | compute "outward" from the building's centre |
| City view invisible | camera far plane at 200 m; the lawn blocked the view | far plane 6,000 m for that scene; the hill drops at a terrace |
| Halos looked like bubbles | additive sprite discs on every lamp | removed them; a bloom pass with threshold above 1 |
| Image viewer showed an old render | same file name, cached | write each render to a new name |

## 9. Licences and credits

- **Code:** this repository.
- **The Maltese Falcon (1930):** public domain in the US since 2026. Use the
  novel only, nothing from the 1941 film (see `DESIGN.md`).
- **Assets:** MakeHuman CC0 assets, two CC-BY assets, the OFL font and
  public-domain paintings. All are listed in `CREDITS.md`; the CC-BY ones need
  visible credit if the game is published.
- **Likeness:** Holmes follows Jeremy Brett's costume and the type of face,
  not a portrait of the actor.
