# THE BLACK BIRD — design

A third-person 3D detective game for phones (landscape), playable on desktop.
Sherlock Holmes and Dr. Watson in San Francisco, 1895, caught up in the hunt
for a jewelled falcon. It follows the plot of Dashiell Hammett's *The Maltese
Falcon*, with Holmes in Sam Spade's place.

Touchstones:
- **Frogwares' Sherlock Holmes games** (*Crimes & Punishments*, *The Devil's
  Daughter*, *Chapter One*): free investigation of 3D scenes, character
  portraits, imagination reconstructions, the Deduction Space, and a moral
  choice at the end of each case.
- **Rockstar / Team Bondi's *L.A. Noire***: interrogations where you judge each
  statement (truth, doubt or a lie you can prove with evidence), a notebook of
  people, places and clues, and a rating at the end of every case.
- **Blazing Griffin's Agatha Christie games** (*Hercule Poirot: The First Cases*,
  *The London Case*): a mind map that joins facts into conclusions, and clean,
  readable UI on a small screen.

Our hook is **hyper-observation**. Holmes sees what other people miss, so
looking closely is the main thing the player does, and we make it feel good.

## Rights
- *The Maltese Falcon* (1930) entered the US public domain on 1 Jan 2026.
  Holmes is fully public domain. Use the **novel** only: its plot, characters
  and names.
- Do **not** use anything from the 1941 Warner Bros. film: likenesses, its
  added lines, poster art or music.
- Outside the US, Hammett's work stays in copyright until 2032 in countries
  that use life + 70 years. Check this before any non-US store release.
- **Holmes's look** follows Jeremy Brett's Granada costume (black frock coat,
  top hat, cane, black hair slicked back) and that *type* of face: long, pale,
  hawk-nosed. It is not a portrait of the actor. Keep it that way: a real
  person's likeness in a published game is a legal risk.
- Third-party assets (MakeHuman CC0 and CC-BY, an OFL font, public-domain
  paintings) are listed in `CREDITS.md`. The CC-BY items need a visible credit
  in any release.

## Story

The novel's plot, moved back to 1895. Miles Archer is a former Pinkerton man
who once helped Holmes. Holmes and Watson are in the city as his guests.

| # | Chapter | Novel beat | New mechanic it introduces |
|---|---------|-----------|------------------------------|
| I | **Burritt Alley** *(built)* | Archer shot; Thursby blamed | Explore, Focus, close-up, interrogation, notebook, Mind Palace, accusation, case rating |
| II | **The Levantine** | Joel Cairo searches Holmes's rooms at gunpoint; gardenia | Character portrait; fight prediction |
| III | **The St. Mark** | "Miss Wonderly" is Brigid O'Shaughnessy; one lie after another | Focus tells during speech; presenting evidence mid-conversation |
| IV | **The Fat Man** | Kasper Gutman tells the falcon's history (Knights of Malta, 1539); the drugged whisky | Research at the **Mark Hopkins Institute of Art** *(location built as a preview)*; a drugged, broken-memory reconstruction |
| V | **The Gunsel** | Wilmer tails Holmes through the fog | Tailing and counter-tailing on foot through the city |
| VI | **La Paloma** | The ship burns at the docks; Captain Jacobi brings in the parcel and dies | Reconstruction of the fire; timed search |
| VII | **The Black Bird** | The bird is lead. Holmes hands Brigid to the police | Final Mind Palace; the moral choice |

The fake falcon pays off careful players. If they noticed small details in
Chapters IV–VI (the weight Jacobi carried, fresh enamel, the smell of hot
lead at a Kearny Street foundry), they can call it a fake before Gutman
scrapes it. That opens a different last scene.

**Chapter IV and the Hopkins Institute.** In 1895 the Hopkins mansion on Nob
Hill was the San Francisco Art Association's school and gallery, the Mark
Hopkins Institute of Art. Holmes goes there to learn what a jewelled falcon
from the Knights of Malta would be: a curator in the Director's Room, the
school's archive in the old library, the Association's pictures in the
gallery, and the city at his feet from the tower. Gutman, a collector, would
know the place well. The scene is modelled and walkable; its people, clues
and dialogue are not written yet.

## Core loop
Explore → observe (Focus) → gather clues and testimony → read people in
interrogation → combine facts in the Mind Palace → answer the chapter's
question → choose what to do with the truth → a case rating.

### 1. Exploration
Third-person camera over Holmes's shoulder. Watson follows at his left
shoulder and comments.
- Touch: a fixed stick in the bottom-left corner (faint until touched), drag
  anywhere else to look. A context button above the Focus button names the
  nearest thing to do ("Examine the broken fence", "Talk to Sgt. Polhaus").
- Desktop: WASD, drag to look, E to act, F for Focus, B notebook, M Mind Palace.
- Clue markers are **bare circles**: what is there is only revealed on a tap.
  Markers turn gold once their clue is found.
- Scenes can have slopes and stairs (the Hopkins drive and front steps). The
  world reports the ground height and Holmes and Watson follow it.

### 2. Focus (hyper-observation)
Holmes's signature power, on its own button.
- Time slows to about 30%. The picture drains of colour, cools and narrows;
  only bright, revealed things keep their colour.
- **Hidden details** fade in (heel prints, a scent wisp, a glint past the
  fence) with blue markers. Most chapters hold some clues you can only find
  this way.
- **Reads**: short typewriter labels appear next to people and objects, in the
  style of BBC *Sherlock*'s on-screen text ("Hill clay on boots: lives on
  Telegraph Hill"). Reads Holmes has noticed are written into the People tab
  of the notebook.
- A meter limits it: about 10 s of Focus, which refills while off. You choose
  where to look instead of leaving it on.

### 3. Close-up examination
Bodies and key objects open into a fixed close-up camera with letterbox bars.
A pocket lamp lights the scene and there are tap targets on the details.
Focus works here too and reveals details like the powder burns. "Step back"
returns to exploring.

### 4. Conversations and interrogation
A greeting, then topics. Some topics appear only once you hold a clue ("Archer
never drew his gun."). Answers can give testimony.

Some statements can be **challenged**, L.A. Noire style. After the line,
Holmes sees a **tell** (a stage direction: "Kelly glances at his sergeant and
wipes his mouth with the back of his glove"), and you choose:
- **Believe**: take it as the truth;
- **Press**: something is being held back;
- **Prove a lie**: pick the fact from your notebook that breaks it.

Each challenge is called once. A right call can give new testimony (pressing
Kelly gets Thursby's alibi); a wrong one gets nothing and counts against the
case rating. Chapter I has two: Polhaus repeating Dundy's robbery theory
(a provable lie: Archer's revolver was never touched) and Kelly claiming he
heard nothing (press him).
*Planned (Ch. III):* presenting evidence in the middle of a speech, and tells
that only show under Focus.

### 5. The notebook
A leather notebook with ruled pages and tabs:
- **Case**: the chapter, the current line of inquiry, a summary, and clues,
  deductions and key deductions found so far;
- **Clues**: everything observed, heard or remembered, each stamped with its
  kind, and how many remain to be found;
- **People**: profiles of everyone in the case (including the absent: Archer,
  Miss Wonderly, Thursby), the reads Holmes has noticed on them, and what they
  said;
- **Deductions**: each conclusion, what it was drawn from, and which are key.

### 6. Mind Palace
A board, like Frogwares' Deduction Space. Facts sit in the first column as
cards; each deduction appears as a new card joined to its sources by glowing
threads, and key deductions thread on to the chapter's question at the right.
Pick two cards that belong together and Holmes draws the deduction, which can
itself be combined. Deductions chain (coat buttoned + gun holstered → *felt no
danger*; *felt no danger* + *face to face* → **knew his killer**). When every
key deduction is made, the question lights up and tapping it names the killer.
A wrong pair costs nothing but Holmes's patience ("Data, Watson, but not a
deduction"), though false starts are counted for the rating.

### 7. Conclusion and rating
The chapter's question with several answers. Wrong answers get a reply
explaining why not, stay crossed out and count against the rating. The right
one plays the epilogue, then the **case rating**: one to five stars from clues
found, deductions drawn, interrogations read correctly, false starts in the
Mind Palace and wrong accusations.
*Planned:* from Ch. II on, a moral choice follows the right answer
(Frogwares-style): turn her in now or let her run, and the later chapters
remember.

### 8. Planned mechanics
- **Character portrait** (Ch. II): meeting someone new freezes them in a
  portrait pose. Scan them in Focus, pick out details and deduce what they
  are ("a Levantine, a collector, has been to sea recently, carries a pistol
  he has no idea how to use").
- **Reconstruction**: at marked spots, ghostly figures replay a moment. You set
  the order of events and the scene plays back to check you.
- **Fight prediction**: rare set pieces. Holmes freezes the moment and plans
  three moves on a timeline ("knock the gun hand, elbow, sweep"). You watch a
  ghosted preview, then it plays for real. If you missed a detail (Wilmer's
  second gun), the plan breaks.
- **Tailing**: follow Wilmer through the fog without being seen, using shop
  windows and cable cars as cover.
- **Archive**: the Hopkins Institute's records and library, where you look up
  the falcon's history.

## Look and presentation
- Night, fog and gaslight. San Francisco in 1895: brick and timber Italianate
  fronts with bay windows and bracketed cornices, cast-iron shopfronts with
  gilt signs, cast-iron gas lamps, telegraph wires, cable cars on California
  Street.
- Realistic people (MakeHuman bodies), in period dress: Holmes in Brett's black
  frock coat, top hat and cane; Watson in light tweed and a bowler; Polhaus in
  a grey overcoat; Kelly in a navy tunic and helmet; Archer buttoned to the
  collar.
- One post pass: ACES, sRGB, a cold night grade, vignette, grain and the Focus
  look, with a **bloom** threshold above 1 so only light sources glow (gas
  flames, lit windows, the police lantern). No halo sprites.
- Letterbox bars in conversations and close-ups; paper slips for new clues;
  an objective panel (in the Hopkins preview it names the room you are in).

## Mobile UX rules
- Landscape only; portrait shows a rotate prompt. Respect the safe areas.
- Every tap target is at least 44 px. The thumb zones are the bottom-left
  stick and the bottom-right Focus and act buttons. Text sits bottom centre.
- During a conversation, a tap anywhere advances the line.
- A chapter is 15–30 min, saved automatically after every clue, deduction and
  interrogation call (`localStorage`, which fails safely).
- Fonts: IM Fell English for narrative, Special Elite (typewriter) for Focus
  reads, IM Fell English SC for the shop signs in the sets.
- The title screen's **Scenes** button jumps to any scene for testing
  (`?skip=1` Chapter I without the intro, `?scene=hopkins` the Institute).

## Tech
- Vite + three.js, vanilla ES modules, HTML/CSS UI. Hosted on GitHub Pages;
  every push to `main` deploys.
- Renderer (`src/core/renderer.js`): HDR multisampled target, UnrealBloom pass,
  then the grade pass.
- Lighting: hemisphere + one directional + point lights. The alley has fixed
  lamps; the Hopkins Institute has six gas lights that move to the lamps
  nearest Holmes, because phones can't afford one per lamp. No shadow maps
  (blob shadows under people).
- Each chapter is data (`src/cases/<chapter>.js`): `CLUES`, `DEDUCTIONS`,
  `PEOPLE`, `ABSENT`, `SPOTS`, `CLOSEUP`, `TALK` (with `challenge`s), `READS`,
  `CONCLUSION`. Engine code never names a specific clue. Keep that true.
- Scenes: `main.js` picks a world from the URL. A world provides colliders,
  `update()`, and optionally `groundAt()`, rooms and interactions.
  `main.js` still carries Chapter I specifics; it becomes a proper per-chapter
  structure when Chapter IV is written.

### Code layout
```
src/main.js             game loop, modes (title, intro, explore, closeup, talk, book, palace, accuse), scene choice
src/core/               renderer (bloom + grade), touch/keyboard input, synth audio, fullscreen, glTF/Draco loader
src/world/alley.js      Chapter I: loads the modelled set, keeps the colliders, lamps, fog, Focus-only details
src/world/hopkins.js    the Mark Hopkins Institute: the model, moving gas lights, ground levels, the night city
src/world/textures.js   procedural canvas textures still used in the alley (cobbles, poster, glows)
src/game/figure.js      people: skinned GLBs with an animation mixer; fallbacks to rigid models or primitives
src/game/state.js       investigation progress, interrogation calls, reads, rating, save
src/cases/archer.js     Chapter I content
src/ui/                 HUD + world labels, dialogue + interrogation, notebook + Mind Palace board, full-screen cards
art/                    Blender build scripts and their .blend files (see docs/SETUP.md)
public/models/          exported .glb models and hopkins.json
```

### Assets
All 3D content is generated by Python scripts run in Blender, headless:
`art/build_humans.py` (characters, with MPFB), `art/build_set.py` (Burritt
Alley and Bush Street) and `art/build_hopkins.py` (the Institute, its grounds
and California Street), with `art/setkit.py` shared by the two set builders.
Exports are glTF with Draco geometry and JPEG textures. Setup, commands and
the traps we hit are in `docs/SETUP.md`.

- Units are metres, Y-up; set scripts model directly in game coordinates.
- **Characters** use MPFB's `game_engine` rig (53 bones) with clips `Idle`,
  `Walk`, `Talk` and `LieBack`, re-rested with the arms down. Built so far:
  Holmes, Watson, Polhaus, Kelly, Archer (1.9–2.5 MB each).
  **Over budget**: 38–47k triangles each against the 12k target. Next step:
  MPFB proxy meshes or decimation, and dropping hidden body faces.
- **Sets**: Burritt Alley 53k triangles, 1.5 MB; the Hopkins Institute and its
  street 112k triangles, 3.5 MB, plus `hopkins.json` (colliders, rooms, lamps,
  interactions, ground levels).
- Still to model. Cast: Brigid, Cairo, Gutman, Wilmer, Jacobi, Effie
  (Archer's secretary). Places: Archer's office (Sutter St.), the Palace
  Hotel, the St. Mark, the Alexandria, the Embarcadero docks and *La Paloma*.

## Roadmap
1. ✅ Chapter I vertical slice: explore, Focus, close-up, talk, Mind Palace,
   accusation, save.
2. ✅ Detective-game interface: notebook, Mind Palace board, interrogation
   (Believe / Press / Prove a lie), case rating, letterbox and clue slips.
3. ✅ Realistic cast (MPFB) for Chapter I, and the modelled alley set.
4. ✅ The Mark Hopkins Institute as a walkable preview, with the night city.
5. Next:
   - characters under budget;
   - motion-captured walks (the CMU library);
   - softer coat cloth;
   - an audio pass.
6. Chapter IV at the Hopkins Institute (curator, archive, the falcon's history).
7. Chapter II with the character portrait and fight prediction.
8. Focus tells and presenting evidence mid-speech (Ch. III).
9. Reconstruction, tailing.
10. PWA install, controller support, localisation.
