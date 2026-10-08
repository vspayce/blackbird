// Chapter V: The Gunsel. Kearny Street in the fog, Wednesday, the day before La Paloma is due.
// Wilmer has been following Holmes since dawn. Holmes notices (a reflection in the jeweller's window, the
// constable on the corner), doubles back into a doorway, and then follows the boy instead, through the fog
// to the Alexandria Hotel, where Wilmer leaves his report for Gutman. The question: why is Gutman having Holmes
// followed? Same shape as archer.js; positions in the Kearny world (Kearny runs along -z from Market Street).
// place: a spot borrows its position from kearny.json's named places (shop doors).
import { PEOPLE as CH1 } from './archer.js';
import { PEOPLE as CH4, READS as R4 } from './gutman.js';

export const CHAPTER = {
  id: 'gunsel',
  number: 'V',
  title: 'Chapter V · The Gunsel',
  next: 'Chapter VI · La Paloma',
  world: 'kearny',
  start: 'spawn',
  startClues: ['paloma'],
  opening: 'Slowly, Watson. Look in the shop windows, not behind us.',
  intro: [
    'San Francisco. Wednesday, the day before La Paloma is due.',
    'The fog came in at dawn and has not lifted.',
    'Holmes has a telegram to send, and a fancy to walk to the telegraph office himself.',
    ['Holmes', 'Up Kearny Street, Watson, and slowly. Let us see who else is taking the air this morning.'],
  ],
  summary: 'Gutman drugged Holmes at the Hopkins Institute to keep him away until La Paloma docks tomorrow. This morning Holmes walks up Kearny Street to send a telegram to Hong Kong.',
};

export const CLUES = {
  paloma: { kind: 'memory', title: 'La Paloma', text: 'From Hong Kong, due at the Embarcadero tomorrow. Gutman drugged me to keep me away until then.' },
  reflection: { kind: 'clue', title: 'In the jeweller\'s glass', text: 'Among the rings and watches, a reflection: a cap, an overcoat too good for its wearer, twenty paces back on the far side. When I stop, he stops.' },
  sentinel: { kind: 'testimony', who: 'kelly', title: 'Kelly: since dawn', text: 'The boy stood across from the Palace from six this morning, and asked the bell boy whether a lady had called on Mr. Holmes.' },
  dollar: { kind: 'testimony', who: 'kelly', title: 'Kelly: a dollar', text: 'The boy paid Kelly a dollar to say which way Holmes went.' },
  wire: { kind: 'memory', title: 'The telegram', text: 'To the harbour master, Hong Kong: "La Paloma. Who shipped cargo aboard her in November? A lady?" Sent from the Western Union on Kearny Street.' },
  chances: { kind: 'memory', title: 'Within reach', text: 'He passed within a yard of my doorway with two guns in his pockets and never looked in. He was not sent to kill me.' },
  register: { kind: 'clue', title: 'The note for 12C', text: 'Left in the Alexandria\'s key box for Suite 12C, and read upside down across the desk: "H. walked to the telegraph office. No lady. Still looking. W."' },
};

export const DEDUCTIONS = {
  followed: { from: ['reflection', 'sentinel'], title: 'Followed since dawn', text: 'The boy took up his post outside the Palace at six and has walked behind me ever since. Gutman put him there.', key: true },
  watching: { from: ['followed', 'chances'], title: 'Watched, not hunted', text: 'Two guns, a yard away, and he never touched them. His orders are to watch me, not to kill me.', key: true },
  lady: { from: ['sentinel', 'register'], title: 'Gutman is looking for Brigid', text: 'He asked whether a lady had called on me, and his report says "no lady. Still looking." Gutman thinks I will lead him to Miss O\'Shaughnessy.', key: true },
  bought: { from: ['dollar', 'followed'], title: 'Gutman buys what he needs', text: 'A dollar for a constable, a whisky for a detective. Everyone has a price, to Gutman; it is the one thing he believes.' },
  wired: { from: ['wire', 'paloma'], title: 'Who shipped it', text: 'When the harbour master answers, we shall know who put a parcel aboard La Paloma. I think I know already.' },
};

const WRONG = [
  'No. Those two facts have nothing to say to one another.',
  'Data, Watson, but not a deduction.',
  'The fog is in my head as well as the street. Again.',
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

export const READS = {
  wilmer: R4.wilmer,
  kelly: ['Wet to the knees again: walked the beat all night', 'A new silver dollar in his tunic pocket'],
  watson: ['Hasn\'t looked behind him once: good man', 'Service revolver, right coat pocket'],
};

export const PEOPLE = {
  watson: CH1.watson,
  kelly: {
    name: 'Patrolman Kelly', role: 'Beat constable, now on Kearny',
    note: 'Moved off Bush Street onto Kearny: his sergeant\'s idea of a kindness. Honest, mostly.',
    pos: [-9.6, 0, -50], face: [0, -50], look: CH1.kelly.look,
  },
  wilmer: {
    name: 'Wilmer', role: 'Gutman\'s gunsel',
    note: 'He has followed Holmes since dawn. Now Holmes follows him.',
    pos: [8.6, 0, 16], face: [8.6, 0], leaves: 'arrived', notalk: true,
    look: CH4.wilmer.look,
  },
};

export const ABSENT = {
  gutman: { name: 'Kasper Gutman', role: 'The Fat Man', note: 'Drugged Holmes last night at the Hopkins Institute. Waiting for La Paloma.' },
  brigid: { name: 'Brigid O\'Shaughnessy', role: 'Once "Miss Wonderly"', note: 'Everyone is looking for her. She had the bird in Hong Kong.' },
  cairo: { name: 'Joel Cairo', role: 'The Levantine', note: 'Drinks at the Belvedere, smells of gardenia, and is afraid of Gutman.' },
};

export const SPOTS = [
  { id: 'jeweller', place: 'jeweller', label: 'The jeweller\'s window', clue: 'reflection', focus: true, r: 2.4 },
  { id: 'telegraph', place: 'WESTERN UNION TELEGRAPH', label: 'The Western Union office', clue: 'wire', r: 2.6 },
  { id: 'doorway', place: 'HATTER', label: 'Step into the hatter\'s doorway', event: 'doubled', needs: ['reflection'], r: 2.2,
    early: 'A hatter. I have hats enough, Watson.' },
  { id: 'cabs', pos: [5.4, 1.5, -87], r: 3, say: 'The cabmen are asleep on their boxes. Nobody is going anywhere fast in this fog.' },
  { id: 'palace', place: 'palace', r: 3, say: 'The Palace: eight hundred rooms, and the boy has watched the door of mine since six.' },
  { id: 'register', place: 'alexandria', label: 'The hotel desk', clue: 'register', after: 'arrived', r: 3 },
  { id: 'sutter', place: 'sutter', label: 'Look down Sutter Street', r: 2.4,
    say: 'Sutter Street, Watson: the cable runs under the road all the way out to Larkin. Listen for the bell.' },
  { id: 'oysters', place: 'OYSTER GROTTO', r: 2.4, say: 'Oysters at ten in the morning. San Francisco never sleeps, it only lies down for an hour or two.' },
];

export const CLOSEUP = null;

// Tailing: Wilmer shadows Holmes up the east sidewalk; after 'doubled' he walks this path to the Alexandria,
// looking back at the pauses, and waits at the corner of Sutter for the cable car to pass.
export const TAIL = {
  who: 'wilmer',
  follow: 20, shadowX: 8.6,
  after: 'doubled', until: 'arrived',
  path: [[8.6, -103], [8.6, -122], [-8.4, -143], [-8.6, -152], [-8.6, -160], [6.8, -167], [8.8, -172.5]],
  pauses: { 1: 3.5, 3: 3.0, 5: 3.0 },
  waitFor: { 1: 'cablecar' },
  speed: 1.45, sight: 24, close: 4.5, lose: 34, loseTime: 4,
  spotted: ['He saw me. He walks on, but he knows. Back, and try again.', 'Too close, Watson. He has us. Again.'],
  lost: ['Gone, into the fog. Back to where we last had him.', 'Lost him. Again, and closer this time.'],
};

export const EVENTS = {
  doubled: {
    type: 'cards',
    lines: [
      'Holmes steps into the hatter\'s doorway, among the hat boxes.',
      'Twenty seconds later the boy goes by. Close enough to touch his sleeve. He never looks in.',
      ['Holmes', 'Now, Watson, we follow him. Keep him in sight. When he looks back, be behind something.'],
    ],
    gives: 'chances',
    wake: [10.2, 0, -94.5],
  },
  arrived: {
    type: 'cards',
    lines: [
      'The boy goes up the steps of the Alexandria without a look behind him.',
      'At the desk he writes a note, folds it twice, and leaves it in the box for Suite 12C.',
      ['Holmes', 'Suite 12C. Let us see what he has to report.'],
    ],
    wake: [7.6, 0, -168],
  },
};

export const TALK = {
  watson: {
    hello: [['Watson', 'Are we being followed, Holmes?'], ['Holmes', 'Don\'t look round, Watson.']],
    topics: [
      { q: 'What does Gutman want with me, Watson?', a: [['Watson', 'The bird, presumably. He thinks you know where it is.'], ['Holmes', 'Or he thinks I know someone who does.']] },
      { q: 'Why a telegram to Hong Kong?', a: [['Holmes', 'Somebody put a parcel aboard La Paloma in November, Watson. Harbour masters keep books.']] },
    ],
  },
  kelly: {
    hello: [['Kelly', 'Mr. Holmes! They\'ve moved me off Bush Street onto Kearny. The sergeant\'s idea of a kindness.']],
    topics: [
      { q: 'Have you seen a young man in a cap?', gives: 'sentinel', a: [['Kelly', 'The little fellow in the good overcoat? Stood across from the Palace since six this morning, sir. Asked the bell boy if a lady had called on you.']] },
      {
        q: 'Did he speak to you?', needs: ['sentinel'],
        a: [['Kelly', 'Told me to mind my own business, sir. That was all.']],
        challenge: {
          tell: 'Kelly reddens, and his hand goes to his tunic pocket.',
          answer: 'doubt', gives: 'dollar',
          right: [['Holmes', 'And what else, Constable?'], ['Kelly', '...He gave me a dollar to tell him which way you went, sir. I told him up Kearny. I\'m sorry, sir.'], ['Holmes', '(He told him the truth, then. No matter: today I want to be followed.)']],
          wrong: [['Kelly', 'That was all, sir. Good day to you.']],
        },
      },
    ],
  },
};

export const CONCLUSION = {
  needs: ['followed', 'watching', 'lady'],
  question: 'Why is Gutman having Holmes followed?',
  answers: [
    { a: 'To kill him when the moment comes', right: false, reply: 'He had his moment in the doorway, and a dozen before it. No.' },
    { a: 'To find Joel Cairo', right: false, reply: 'Cairo is in the Belvedere\'s bar every night. Gutman need not follow me to find him.' },
    { a: 'To keep him away from the wharf', right: false, reply: 'Then the boy would be at the wharf, not on Kearny Street.' },
    { a: 'To find Miss O\'Shaughnessy, and through her the bird', right: true, reply: '"No lady. Still looking." He thinks she will come to me, and he wants to be there when she does.' },
  ],
  epilogue: [
    ['Watson', 'So the boy goes back to his master with nothing.'],
    ['Holmes', 'With a note that says so. Gutman will be impatient tonight, and impatient men make mistakes.'],
    ['Holmes', 'Tomorrow La Paloma comes in. Let us be on the wharf before any of them.'],
  ],
};

export function objective(s) {
  if (s.solved) return 'Chapter complete';
  const ev = e => s.events.includes(e);
  if (!ev('doubled')) {
    if (!s.has('reflection')) return 'Walk up Kearny Street. Are we followed? Use Focus at the jeweller\'s window';
    if (!s.has('sentinel')) return 'Someone is behind us. Ask the constable on the corner of Post Street';
    return 'Turn the tables: step into the hatter\'s doorway on the next block and let him pass';
  }
  if (!ev('arrived')) return 'Follow the boy. Keep him in sight; when he looks back, be in cover';
  if (!s.has('register')) return 'He went into the Alexandria. See what he left at the desk';
  if (s.canConclude) return 'Open the Mind Palace: why is Gutman having you followed?';
  const missing = CONCLUSION.needs.filter(d => !s.deductions.includes(d)).length;
  return `Mind Palace: ${missing} key deduction${missing > 1 ? 's' : ''} still to make`;
}

for (const id of Object.keys(DEDUCTIONS)) console.assert(!CLUES[id], `id "${id}" is both a clue and a deduction`);
