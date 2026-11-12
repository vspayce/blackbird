# Working on The Black Bird

The owner works on a MacBook with Unity, Blender and Xcode. Work happens **on that laptop, in the Unity project**,
not in a cloud session: a cloud session has no Unity editor, no Xcode and no App Store Connect key, and cannot see
the result of anything it writes.

## At the start of every session

1. Say plainly where this session is running (the laptop or a cloud container). If it is a cloud container, say so
   before doing any work, list what cannot be done from there (run Unity, build, TestFlight), and give the owner
   the setup checklist below so they can move to the laptop.
2. On the laptop, check the checklist below and tell the owner which steps are still missing, as a short list.
   They have asked to be reminded of these steps each time rather than be expected to remember them.

## Setup checklist (laptop)

1. **Claude in Terminal.** Open Terminal, then `cd ~/blackbird-unity` and run `claude`. (Or the Claude desktop
   app ▸ Claude Code ▸ a Local session on that folder.) The art sources are in the web repo, `~/BlackBird`.
2. **Unity MCP.** Open the project in Unity 6. `ProjectSetup.cs` installs MCP for Unity
   (`com.coplaydev.unity-mcp`) on first open. In Unity, open the MCP for Unity window and start its server; Claude
   reaches it at `http://127.0.0.1:8080/mcp` (the `UnityMCP` entry in `~/.claude.json`). Unity must stay open.
3. **Blender MCP.** Open Blender 5.2 with the Blender Lab **MCP** add-on enabled (Preferences ▸ Get Extensions,
   Blender Lab repository). Claude Code starts the server half itself (the `blender` entry in `~/.claude.json`,
   run through `uv`). Model builds do not need it: they run headless, e.g.
   `/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/build_set.py`.
4. **Check both are connected.** In Claude, run `/mcp`: `blender` and `UnityMCP` should both show as connected.
5. **Character rebuilds only:** MPFB and the MakeHuman asset packs, with the separate Blender config
   (`art/.blender-config`). See the web repo's `docs/SETUP.md`, section 5.
6. **TestFlight:** Xcode signed in to the Apple ID, `Tools/apple/team.txt` present. Build the Xcode project from
   Unity (Black Bird ▸ Apple ▸ Build Xcode Project), then `Tools/apple/testflight.sh iOS` (or `tvOS`).

The full account of the tools, add-ons and traps is the web repo's `docs/SETUP.md`.

## The two repositories

- `blackbird-unity` (this is the game being worked on): C# in `Assets/BlackBird`, scenes built by the menu
  **Black Bird ▸ Build ...**, so rerun the builder after changing art or builder code.
- `blackbird` (the three.js prototype): holds the `.blend` files, the Blender build scripts in `art/` and the case
  data in `src/cases/`, which Unity imports (`Tools/blender/export_unity.py`, `Tools/cases/export_cases.mjs`).
  Change those there; do not spend effort on the web game itself unless asked.
