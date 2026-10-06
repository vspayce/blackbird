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
- **Blazing Griffin's Agatha Christie games** (*Hercule Poirot: The First Cases*,
  *The London Case*): interrogations built around catching contradictions, a
  mind map that joins facts into conclusions, and clean, readable UI on a
  small screen.

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

## Story

The novel's plot, moved back to 1895. Miles Archer is a former Pinkerton man
who once helped Holmes. Holmes and Watson are in the city as his guests.

| # | Chapter | Novel beat | New mechanic it introduces |
|---|---------|-----------|------------------------------|
| I | **Burritt Alley** *(built)* | Archer shot; Thursby blamed | Explore, Focus, close-up, talk, Mind Palace, accusation |
| II | **The Levantine** | Joel Cairo searches Holmes's rooms at gunpoint; gardenia | Character portrait; fight prediction |
| III | **The St. Mark** | "Miss Wonderly" is Brigid O'Shaughnessy; one lie after another | Lie tells in conversation; present evidence |
| IV | **The Fat Man** | Kasper Gutman tells the falcon's history (Knights of Malta, 1539); the drugged whisky | Research in the archive; a drugged, broken-memory reconstruction |
| V | **The Gunsel** | Wilmer tails Holmes through the fog | Tailing and counter-tailing on foot through the city |
| VI | **La Paloma** | The ship burns at the docks; Captain Jacobi brings in the parcel and dies | Reconstruction of the fire; timed search |
| VII | **The Black Bird** | The bird is lead. Holmes hands Brigid to the police | Final Mind Palace; the moral choice |

The fake falcon pays off careful players. If they noticed small details in
Chapters IV–VI (the weight Jacobi carried, fresh enamel, the smell of hot
lead at a Kearny Street foundry), they can call it a fake before Gutman
scrapes it. That opens a different last scene.

## Core loop
Explore → observe (Focus) → gather clues and testimony → combine them in the
Mind Palace → answer the chapter's question → choose what to do with the truth.

### 1. Exploration
Third-person camera over Holmes's shoulder. Watson follows and comments.
- Touch: floating stick on the left 40% of the screen, drag anywhere else to
  look. A context button above the Focus button names the nearest thing to
  do ("Examine the broken fence", "Talk to Sgt. Polhaus").
- Desktop: WASD, drag to look, E to act, F for Focus.

### 2. Focus (hyper-observation)
Holmes's signature power, on its own button.
- Time slows to about 30%. The picture drains of colour, cools and narrows;
  only bright, revealed things keep their colour.
- **Hidden details** fade in (heel prints, a scent wisp, a glint past the
  fence) with pulsing blue markers. Most chapters hold some clues you can
  only find this way.
- **Reads**: short typewriter labels appear next to people and objects, in the
  style of BBC *Sherlock*'s on-screen text ("Hill clay on boots: lives on
  Telegraph Hill"). They are flavour that teaches the eye. In later chapters,
  some reads become clues you can use in conversation.
- A meter limits it: about 10 s of Focus, which refills while off. You choose
  where to look instead of leaving it on.

### 3. Close-up examination
Bodies and key objects open into a fixed close-up camera. A pocket lamp
lights the scene and there are tap targets on the details. Focus works here
too and reveals details like the powder burns. "Step back" returns to
exploring.

### 4. Conversations
A greeting, then topics. Some topics appear only once you hold a clue ("Archer
never drew his gun."). Answers can give testimony cards.
*Planned (Ch. III):* during a speech, Focus shows tells (a glove twisted, a
glance at the door). If a line contradicts a card you hold, you can
**present** the card. Getting it wrong costs credibility, and the witness says
less.

### 5. Mind Palace
Every clue, memory, testimony and deduction is a card. Pick two that belong
together and Holmes draws a deduction, which is a new card you can combine
further. Deductions chain (coat buttoned + gun holstered → *felt no danger*;
*felt no danger* + *face to face* → **knew his killer**). Some deductions are
**key** (gold). When all of them are made, "Name the killer" opens. Optional
deductions add flavour and, later, change the epilogue.
A wrong pair costs nothing. Holmes just dismisses it ("Data, Watson, but not
a deduction").

### 6. Conclusion
The chapter's question with several answers. Wrong answers get a reply
explaining why not and stay crossed out. The right one plays the epilogue.
*Planned:* from Ch. II on, a moral choice follows the right answer
(Frogwares-style): turn her in now or let her run, and the later chapters
remember.

### 7. Planned mechanics
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
- **Archive**: Holmes's index and the Mechanics' Institute library, where you
  look up the falcon's history.

## Mobile UX rules
- Landscape only; portrait shows a rotate prompt. Respect the safe areas.
- Every tap target is at least 44 px. The thumb zones are the bottom-left
  stick and the bottom-right Focus and act buttons. Text sits bottom centre.
- A chapter is 15–30 min, saved automatically after every clue and deduction
  (`localStorage`, which fails safely).
- Fonts: IM Fell English for narrative, Special Elite (typewriter) for Focus
  reads.

## Tech
- Vite + Three.js, vanilla ES modules, HTML/CSS UI (same stack as *Schofield*).
- One post pass (`src/core/renderer.js`): ACES, sRGB, night grade, vignette,
  grain, Focus look. HDR multisampled target.
- Lighting budget: hemisphere + one directional + at most 4 point lights. No
  shadow maps yet (blob shadows under people).
- Each chapter is data (`src/cases/<chapter>.js`): `CLUES`, `DEDUCTIONS`,
  `PEOPLE`, `SPOTS`, `CLOSEUP`, `TALK`, `READS`, `CONCLUSION`. Engine code
  never names a specific clue. Keep that true.

### Code layout
```
src/main.js            game loop, modes (title, intro, explore, closeup, talk, book, palace, accuse)
src/core/              renderer + grade, touch/keyboard input, synth audio, fullscreen
src/world/alley.js     Chapter I scene: buildings, fence, lamps, fog, Focus-only details
src/world/textures.js  procedural canvas textures (cobbles, brick, planks, poster, glows)
src/game/figure.js     placeholder people built from primitives, with walk/idle animation
src/game/state.js      investigation progress + save
src/cases/archer.js    Chapter I content
src/ui/                HUD + world labels, dialogue, casebook + Mind Palace, full-screen cards
```

### Assets (next)
Everything is procedural placeholder for now. Real assets follow *Schofield*'s
pipeline: Blender build scripts in `tools/blender/`, exported to
`public/assets/models/*.glb`, then `gltfpack`-compressed.
- Units are metres, Y-up. Characters are skinned, ≤ 12k tris, ≤ 40 bones, with
  clips `Idle`, `Walk`, `Talk`, `Gesture`, `Kneel` (close-ups), `LieBack`
  (bodies). Bone names match the pivots in `figure.js` (hips, legs, arms, torso,
  head) so the animation code carries over.
- Cast: Holmes (Inverness cape, travelling cap), Watson, Polhaus, Kelly,
  Archer, Brigid, Cairo, Gutman, Wilmer, Jacobi, Effie (Archer's secretary).
- Places: Burritt Alley, Bush St., Archer's office (Sutter St.), the Palace
  Hotel, the St. Mark, the Alexandria, the Embarcadero docks and *La Paloma*.

## Roadmap
1. ✅ Chapter I vertical slice: explore, Focus, close-up, talk, Mind Palace,
   accusation, save.
2. Real characters (skinned GLBs) and a modelled alley; audio pass.
3. Chapter II with the character portrait and fight prediction.
4. Lie tells and presenting evidence (Ch. III).
5. Reconstruction, tailing, archive.
6. PWA install, controller support, localisation.
