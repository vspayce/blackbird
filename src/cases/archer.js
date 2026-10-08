// Chapter I: Burritt Alley. Everything the chapter knows lives in this one data
// file: clues, the deductions they combine into, the people, what they say and
// the question the chapter ends on. Later chapters follow the same shape.

export const CHAPTER = {
  id: 'archer',
  title: 'Chapter I · Burritt Alley',
  intro: [
    'San Francisco. November, 1895.',
    'Sherlock Holmes and Dr. Watson have come west as guests of Miles Archer, a former Pinkerton man who once did Holmes a service in an affair of forged bonds.',
    'Yesterday afternoon a young woman calling herself Miss Wonderly came to Archer\'s office. She hired him to follow a man named Floyd Thursby. Holmes was in the room and said nothing.',
    'At half past two this morning a police messenger knocked at the Palace Hotel.',
    'Miles Archer was dead.',
  ],
  start: { x: 0, z: 14.5 },
};

// kind: 'clue' (seen), 'testimony' (heard), 'memory' (already known)
export const CLUES = {
  wonderly: { kind: 'memory', title: 'Miss Wonderly', text: 'Yesterday afternoon. Blue gloves she would not take off. Lavender water. She twisted the left glove at every mention of Thursby, and not at all when she spoke of her poor lost sister.' },
  coat: { kind: 'clue', title: 'Coat buttoned', text: 'Archer\'s overcoat is buttoned to the collar. A man who expects trouble keeps his coat open.' },
  gun: { kind: 'clue', title: 'Revolver never drawn', text: 'His revolver is still on his hip, under the buttoned coat. All six chambers loaded.' },
  wound: { kind: 'clue', title: 'One shot, from the front', text: 'A single wound, high in the chest. He was facing the man who shot him. Or the woman.' },
  burns: { kind: 'clue', title: 'Powder burns', text: 'The cloth around the wound is scorched. The muzzle was not two feet from him.' },
  card: { kind: 'clue', title: 'A card in his pocket', text: 'Miss Wonderly\'s card, St. Mark Hotel. On the back, in pencil: "Burritt St. 2 o\'clock". The hand is not Archer\'s.' },
  fence: { kind: 'clue', title: 'Broken fence', text: 'Three boards snapped outward at the dead end. Archer went back against them when he fell. His back was to the fence and the drop.' },
  heel: { kind: 'clue', title: 'Narrow heel prints', text: 'In the damp between the cobbles: a narrow, pointed heel. A lady\'s boot, small, and standing an arm\'s length from where Archer fell.' },
  scent: { kind: 'clue', title: 'Lavender water', text: 'Under the alley lamp the fog still holds it. Lavender water. Someone stood here and waited.' },
  webley: { kind: 'clue', title: 'An English revolver', text: 'In the weeds past the fence: a Webley-Fosbery, one chamber fired. Rare in San Francisco. Thrown, not dropped. It was meant to be found.' },
  job: { kind: 'testimony', who: 'watson', title: 'Watson: the job', text: 'Miss Wonderly hired Archer to follow Floyd Thursby, who she said had run off with her younger sister. Archer took the night watch himself.' },
  hack: { kind: 'testimony', who: 'polhaus', title: 'Polhaus: a hack', text: 'Patrolman Kelly saw a hired hack pull away from Bush Street just before he found the body. He did not get the number.' },
  thursby: { kind: 'testimony', who: 'kelly', title: 'Kelly: Thursby', text: 'Kelly knows Thursby by sight: an English gunman who drinks at the Belvedere and has boasted of his "Webley". Kelly saw him at the bar at one o\'clock, very drunk.' },
  alibi: { kind: 'testimony', who: 'kelly', title: 'Kelly: the shot', text: 'Kelly was taking a nip at the Belvedere\'s back door when he heard the shot, at ten to two. Thursby was at the bar beside him, too drunk to stand.' },
};

// Each deduction comes from two facts (clues or other deductions).
export const DEDUCTIONS = {
  unready: { from: ['coat', 'gun'], title: 'Archer felt no danger', text: 'Coat buttoned, gun never touched. He did not think he needed it.' },
  close: { from: ['wound', 'burns'], title: 'Face to face, at arm\'s length', text: 'He was shot from the front, close enough to scorch the cloth. He let the killer come right up to him.' },
  knew: { from: ['unready', 'close'], title: 'Archer knew his killer', text: 'No man lets a stranger walk up to him in a dark alley at two in the morning without his hand going to his gun. Archer knew the killer, and trusted them.', key: true },
  lady: { from: ['heel', 'scent'], title: 'A woman was here tonight', text: 'A lady\'s heel and a lady\'s scent, both in an alley where no lady has business at this hour.' },
  wasWonderly: { from: ['lady', 'wonderly'], title: 'Miss Wonderly stood here', text: 'Lavender water and a small, narrow boot. It was Miss Wonderly who waited under the lamp.', key: true },
  lured: { from: ['card', 'job'], title: 'Archer came to meet someone', text: 'He was not following Thursby here. The card says he had an appointment, made in someone else\'s hand.' },
  frame: { from: ['webley', 'thursby'], title: 'The gun points at Thursby', text: 'Thursby\'s own English revolver, thrown where the police would find it, while Thursby was drunk at the Belvedere. Somebody wants him hanged for this.', key: true },
  innocent: { from: ['alibi', 'frame'], title: 'Thursby did not fire', text: 'Thursby was at the Belvedere when the shot was fired. His gun was here; he was not. Someone borrowed it.' },
  backed: { from: ['fence', 'heel'], title: 'The killer came from the street', text: 'Archer stood with the dead end behind him. Whoever met him came from Bush Street and stood between him and the way out.' },
};

const WRONG = [
  'No. Those two facts have nothing to say to one another.',
  'Data, Watson, but not a deduction.',
  'I am theorising without enough to go on. A capital mistake.',
  'Tempting, but it does not hold.',
];
export function wrongLine() { return WRONG[(Math.random() * WRONG.length) | 0]; }

export function combine(a, b) {
  for (const [id, d] of Object.entries(DEDUCTIONS)) {
    const [x, y] = d.from;
    if ((x === a && y === b) || (x === b && y === a)) return id;
  }
  return null;
}

// Things Holmes reads off people and places while in Focus. Pure colour: they
// teach the eye where to look but are not clues in the casebook.
export const READS = {
  polhaus: ['Cigar ash on lapel, gravy on cuff: called from his supper', 'Hill clay on boots: lives on Telegraph Hill', 'Doesn\'t believe it was a robbery'],
  watson: ['Hasn\'t slept', 'Service revolver, right coat pocket', 'Grieving: liked Archer'],
  kelly: ['Lantern wick fresh-trimmed', 'Wet to the knees: ran here', 'Nervous of his sergeant'],
  hat: ['Hat two yards off: fell backwards'],
};

// People in the scene. pos is where they stand; Watson follows Holmes.
export const PEOPLE = {
  watson: { name: 'Dr. Watson', role: 'Friend and chronicler', note: 'Liked Archer more than he will say. Takes people at their word, which is why I keep him by me.', look: { model: 'watson', coat: '#5a4632', trousers: '#3b3128', hat: 'bowler', hatColor: '#2a211a', moustache: '#6b4b2e', hair: '#6b4b2e', longCoat: true, height: 1.76 } },
  polhaus: { name: 'Sgt. Polhaus', role: 'San Francisco Police', note: 'Slow-spoken, not slow-witted. Answers to Lieutenant Dundy, who likes his cases simple.', pos: [-1.5, -16.4], face: [0.5, -19.5], look: { model: 'polhaus', coat: '#2f3238', trousers: '#25262a', hat: 'bowler', hatColor: '#1b1c20', moustache: '#3a2a1e', longCoat: true, height: 1.84 } },
  kelly: { name: 'Patrolman Kelly', role: 'Beat constable, Bush Street', note: 'Young, keen and frightened of his sergeant. Found the body.', pos: [1.6, 6.2], face: [0, 12], look: { model: 'kelly', coat: '#1d2740', trousers: '#1d2740', hat: 'helmet', hatColor: '#1a2238', buttons: true, height: 1.8 } },
};

// People who are not in the alley but belong in the notebook. needs: a clue
// or deduction that brings them into the case.
export const ABSENT = {
  archer: { name: 'Miles Archer', role: 'The victim', note: 'Former Pinkerton man, partner in Spade & Archer. Brave, vain, and fond of a pretty client.' },
  wonderly: { name: 'Miss Wonderly', role: 'The client', note: 'Hired Archer yesterday. Blue gloves, lavender water, a sister who may not exist.', needs: 'wonderly' },
  thursby: { name: 'Floyd Thursby', role: 'The man Archer was following', note: 'English. Drinks at the Belvedere. Owns a Webley-Fosbery, and tells everyone so.', needs: 'job' },
};

// Places to examine. focus: only visible while Focus is on (until found).
// closeup: opens the close-up examination instead of giving a clue.
export const SPOTS = [
  { id: 'body', label: 'Examine Miles Archer', pos: [0.5, 0, -19.9], r: 2.3, closeup: true },
  { id: 'fence', label: 'Examine the broken fence', pos: [0.8, 1, -21.6], r: 1.8, clue: 'fence' },
  { id: 'heel', label: 'Marks in the damp', pos: [0.3, 0.05, -16.3], r: 2.6, clue: 'heel', focus: true },
  { id: 'scent', label: 'Something in the air', pos: [-1.9, 1.5, -8], r: 2.8, clue: 'scent', focus: true },
  { id: 'webley', label: 'A glint past the fence', pos: [0.95, -0.12, -23.3], r: 2.6, clue: 'webley', focus: true },
  { id: 'hat', label: 'Archer\'s hat', pos: [-0.5, 0.1, -18.2], r: 1.5, say: 'His hat, two yards from the body. Knocked off as he went over backwards. No struggle.' },
  { id: 'billboard', label: 'The billboard', pos: [2.2, 1.6, -19.5], r: 1.6, say: '"Cures every ailment known to science." Except, it would seem, a bullet.' },
];

// Close-up on Archer. pos are world points the markers sit on.
export const CLOSEUP = {
  cam: [1.35, 1.2, -19.45],
  look: [0.45, 0.25, -20.2],
  spots: [
    { pos: [0.52, 0.37, -20.18], clue: 'coat', label: 'Coat' },
    { pos: [0.8, 0.26, -19.85], clue: 'gun', label: 'Hip' },
    { pos: [0.4, 0.38, -20.45], clue: 'wound', label: 'Chest' },
    { pos: [0.62, 0.41, -20.38], clue: 'burns', label: 'Scorching', focus: true },
    { pos: [0.27, 0.3, -19.8], clue: 'card', label: 'Pocket' },
  ],
};

// Dialogue. Each person has a greeting and a list of topics; a topic can need
// clues first and can hand over a testimony.
export const TALK = {
  polhaus: {
    hello: [['Polhaus', 'Mr. Holmes. Didn\'t figure you for an early riser.'], ['Holmes', 'Nor I you, Sergeant. Tell me what you have.'], ['Polhaus', 'Kelly found him at ten past two. One shot. Nobody heard it over the foghorns.']],
    topics: [
      { q: 'Was anyone seen leaving?', a: [['Polhaus', 'Kelly says a hack pulled away from Bush Street just before he turned the corner. Didn\'t get the number.']], gives: 'hack' },
      { q: 'Has anything been moved?', a: [['Polhaus', 'Not a thing. Dundy\'ll have my hide if it is. Look all you like, just don\'t pocket anything.']] },
      { q: 'Archer never drew his gun.', needs: ['gun'], a: [['Polhaus', 'No. Miles was careless, but he weren\'t that careless. Not with a stranger.'], ['Holmes', 'Precisely, Sergeant. Not with a stranger.']] },
      { q: 'What of Floyd Thursby?', needs: ['job'], a: [['Polhaus', 'The fella Miles was tailing? Ask Kelly. Kelly knows every barfly on the Coast.']] },
      {
        q: 'What does the Lieutenant make of it?', needs: ['gun'],
        a: [['Polhaus', 'Dundy? Robbery, plain as day. Some footpad caught Miles in the dark and ran for it.']],
        challenge: {
          tell: 'Polhaus watches you over his cigar, waiting.',
          answer: 'lie', evidence: ['gun', 'webley'],
          right: [['Holmes', 'A footpad who leaves a loaded revolver on his victim\'s hip? You do not believe that, Sergeant.'], ['Polhaus', 'Had to see if you\'re as sharp as they say. No. It weren\'t robbery. But Dundy wants it to be, so mind how you go.']],
          wrong: [['Polhaus', 'Well, that\'s the official line, Mr. Holmes. You can take it or leave it.']],
        },
      },
    ],
  },
  watson: {
    hello: [['Watson', 'Poor Archer. Only this afternoon he was boasting of what an easy job Miss Wonderly had handed him.']],
    topics: [
      { q: 'Remind me of the job, Watson.', a: [['Watson', 'She wanted a man named Floyd Thursby followed. Claimed he\'d run off with her younger sister. Archer took the evening watch himself.']], gives: 'job' },
      { q: 'What did you make of Miss Wonderly?', a: [['Watson', 'A charming young woman. Rather nervous.'], ['Holmes', 'Charming, yes. Nervous, no. She was rehearsed, Watson. Every tremble came in on its cue.']] },
      { q: 'Your medical opinion?', needs: ['wound'], a: [['Watson', 'Straight through the heart. He was dead before he struck the fence, poor fellow.']] },
    ],
  },
  kelly: {
    hello: [['Kelly', 'Terrible thing, sir. Terrible. I was only round the corner.']],
    topics: [
      { q: 'Do you know Floyd Thursby?', needs: ['job'], a: [['Kelly', 'Thursby? Englishman, drinks at the Belvedere. Always going on about his "Webley", like no one else ever owned a gun.'], ['Kelly', 'He was in there at one, sir. Drunk as a lord. I saw him through the window on my round.']], gives: 'thursby' },
      {
        q: 'You came running.',
        a: [['Kelly', 'I heard nothing, sir, honest. Just saw the hack go and thought I\'d look down the alley. Wish to God I hadn\'t.']],
        challenge: {
          tell: 'Kelly glances at his sergeant and wipes his mouth with the back of his glove.',
          answer: 'doubt', gives: 'alibi',
          right: [['Holmes', 'There is whisky on your breath, Constable, and you are not telling me everything.'], ['Kelly', '…I was at the Belvedere\'s back door, sir. One nip, against the cold. I heard the shot at ten to two, plain as anything.'], ['Kelly', 'And Thursby was at the bar the whole time, sir. Couldn\'t stand, let alone shoot anybody. Please don\'t tell the sergeant.']],
          wrong: [['Kelly', 'I\'ve told you all I know, sir.'], ['Holmes', '(He has closed up like an oyster. I pushed too hard, or not hard enough.)']],
        },
      },
    ],
  },
};

export const CONCLUSION = {
  needs: ['knew', 'wasWonderly', 'frame'],
  question: 'Who shot Miles Archer?',
  answers: [
    { a: 'Floyd Thursby', right: false, reply: 'The gun points at Thursby, which is exactly why we must not follow it. A drunk at the Belvedere does not leave a gun so neatly placed.' },
    { a: 'A footpad', right: false, reply: 'A footpad who takes nothing and leaves his revolver behind? No.' },
    { a: 'Sergeant Polhaus', right: false, reply: 'Polhaus came from his supper, Watson. There is ash on his lapel and gravy on his cuff.' },
    { a: 'Miss Wonderly', right: true, reply: 'She lured him here with her card, walked up to him under the lamp he trusted, and shot him at arm\'s length. Then she threw Thursby\'s gun over the fence for Polhaus to find.' },
  ],
  epilogue: [
    ['Watson', 'Then we must tell Polhaus at once!'],
    ['Holmes', 'And tell him what? A scent and a heel print. She would be on the morning boat to Hong Kong before the ink was dry.'],
    ['Holmes', 'No, Watson. She thinks she has made fools of us. Let her keep thinking it. Whatever she killed for is still in this city, and she will lead us to it.'],
    ['Holmes', 'Come. I believe there is a gentleman from the Levant waiting at the Palace Hotel, and he smells of gardenias.'],
  ],
};

// Clues and deductions share one namespace in the casebook and Mind Palace.
for (const id of Object.keys(DEDUCTIONS)) console.assert(!CLUES[id], `id "${id}" is both a clue and a deduction`);
