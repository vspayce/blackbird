// Chapter II: The Levantine. Holmes's suite at the Palace Hotel, the morning after Archer's death.
// Joel Cairo has searched the rooms and waits there. The character portrait reads him; he offers $5,000 for the
// black bird and draws a pistol; fight prediction disarms him; his pockets and his lies give the rest. The
// question: why did Cairo search the rooms? Positions in the palace world (art/build_palace.py).
import { PEOPLE as CH1, CLUES as C1 } from './archer.js';

export const CHAPTER = {
  id: 'cairo',
  number: 'II',
  title: 'Chapter II · The Levantine',
  next: 'Chapter III · The St. Mark',
  world: 'palace',
  start: 'spawn',
  startClues: ['wonderly'],
  ride: { to: 'Market Street', place: 'The Palace Hotel', time: 'The morning after' },
  opening: 'The door is open, Watson, and someone has been through everything we own.',
  intro: [
    'San Francisco. The morning after Miles Archer died.',
    'Holmes has been with the police half the night, and Watson is grey with tiredness.',
    'At the Palace Hotel the bell captain stops them. A gentleman has been shown up to their rooms. He would not wait in the lobby, and he sent up his card.',
    ['Holmes', 'A card, Watson, and a gentleman with no name. Let us go up quietly.'],
  ],
  summary: 'Miles Archer was shot in Burritt Alley last night. Holmes suspects his client, "Miss Wonderly". This morning someone has searched Holmes\'s rooms at the Palace Hotel.',
};

export const CLUES = {
  wonderly: C1.wonderly,
  card: { kind: 'clue', title: 'An engraved card', text: '"Mr. Joel Cairo." Heavy card, fine engraving, and it smells strongly of gardenia.' },
  searched: { kind: 'clue', title: 'A thorough search', text: 'Every drawer out, the cushion slit to the springs, the books pulled from the case. He was looking for something about a foot high, and heavy.' },
  gardenia: { kind: 'clue', title: 'Gardenia', text: 'Chypre and gardenia, a great deal of it, and a voice that learned its English in Smyrna or Beirut.' },
  rings: { kind: 'clue', title: 'Soft hands, good rings', text: 'Three rings, one an emerald. Soft, manicured hands that have never done a day\'s labour: he lives by buying and selling fine things.' },
  tan: { kind: 'clue', title: 'A tan to the cuff', text: 'His wrists are brown to the cuff line and white above it. Weeks on a ship\'s deck, and not long ago.' },
  holster: { kind: 'clue', title: 'A new holster', text: 'A bulge under the left arm, and the leather creaks when he moves: a new holster, for a pistol he has never needed.' },
  profile: { kind: 'memory', title: 'My reading of Cairo', text: 'A Levantine, a collector and dealer in fine things, lately weeks at sea, and carrying a pistol he has never fired.' },
  offer: { kind: 'testimony', who: 'cairo', title: 'Cairo: five thousand dollars', text: 'He will pay $5,000 "on behalf of its rightful owner" for a statuette: the black figure of a bird.' },
  pockets: { kind: 'clue', title: 'Three passports', text: 'Greek, French and British, all in the name of Joel Cairo. A man with a passport for every border.' },
  ticket: { kind: 'clue', title: 'A theatre ticket', text: 'The Geary Theatre, tonight, one seat, the stalls. Somewhere to meet someone in the dark.' },
  clipping: { kind: 'clue', title: 'A shipping clipping', text: 'Torn from the Call: "Arrived, the City of Peking, from Hong Kong by way of Honolulu, the 1st inst."' },
  hongkong: { kind: 'testimony', who: 'cairo', title: 'Cairo: Hong Kong', text: 'He came from Hong Kong on the City of Peking. A lady travelled with him as far as Honolulu, and then left him.' },
  fatman: { kind: 'testimony', who: 'cairo', title: 'Cairo: a fat man', text: 'There is another who wants the bird: a fat man. "If he finds it first, neither of us will live to be sorry."' },
};

export const DEDUCTIONS = {
  believesHolmes: { from: ['searched', 'offer'], title: 'He thinks I have the bird', text: 'He searched my rooms for something a foot high, then offered to buy it. He believes Archer found the bird, and that it came to me.', key: true },
  rival: { from: ['offer', 'fatman'], title: 'Cairo hunts it against another', text: '"On behalf of its rightful owner", he says, and goes white at the thought of a fat man. There are two parties after this bird, and they are not friends.', key: true },
  wonderlyKnown: { from: ['hongkong', 'wonderly'], title: 'Cairo knew Miss Wonderly', text: 'A lady from Hong Kong who left him at Honolulu, and a lady who came to Archer yesterday with a story about a sister. The same lady.', key: true },
  traveller: { from: ['tan', 'clipping'], title: 'Lately from Hong Kong', text: 'A tan to the cuff and the arrivals from Hong Kong in his pocket: he came by sea, this week.' },
  amateur: { from: ['holster', 'rings'], title: 'Not a man of violence', text: 'Soft hands and a new holster. He bought the pistol for this errand and is more afraid of it than I am.' },
  border: { from: ['pockets', 'profile'], title: 'A man of three countries', text: 'Three passports, a dealer\'s eye and a sailor\'s tan. Cairo goes wherever the bird goes.' },
};

const WRONG = [
  'No. Those two facts have nothing to say to one another.',
  'Data, Watson, but not a deduction.',
  'I am tired, and it shows. Again.',
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
  cairo: ['Gardenia, a great deal of it', 'Three rings; soft hands', 'Never takes his eyes off the door'],
  watson: ['Hasn\'t slept', 'Service revolver, right coat pocket'],
};

export const PEOPLE = {
  watson: CH1.watson,
  cairo: {
    name: 'Joel Cairo', role: 'The Levantine',
    note: 'Small-boned, dark, glossy black hair, three rings and a great deal of gardenia. He searched these rooms before we came back.',
    pos: [0.9, 0, -4.4], face: [0, 4],
    look: { model: 'cairo', coat: '#18161c', trousers: '#141218', hair: '#0a0908', longCoat: true, height: 1.7 },
  },
};

export const ABSENT = {
  archer: { name: 'Miles Archer', role: 'Shot last night in Burritt Alley', note: 'Former Pinkerton man. Shot at arm\'s length by someone he trusted.' },
  wonderly: { name: 'Miss Wonderly', role: 'Archer\'s client', note: 'Blue gloves, lavender water, and a story about a sister that I did not believe.' },
};

// The character portrait: meeting Cairo freezes the moment. Markers sit on him (local: x right, y up, z toward
// his front); each gives a reading. Then Holmes's reading is completed line by line.
export const PORTRAITS = {
  cairo: {
    event: 'portrait',
    spots: [
      { local: [0.12, 1.42, 0.17], clue: 'gardenia', label: 'Lapel' },
      { local: [0.3, 0.86, 0.08], clue: 'rings', label: 'Hand' },
      { local: [-0.28, 0.9, 0.06], clue: 'tan', label: 'Cuff' },
      { local: [0.14, 1.22, 0.12], clue: 'holster', label: 'Under the arm' },
    ],
    lines: [
      { lead: 'He is', options: ['an Englishman', 'a Levantine', 'a Frenchman'], answer: 1, why: 'Gardenia and Smyrna English. Look again.' },
      { lead: 'who lives by', options: ['his hands', 'the sea', 'buying and selling fine things'], answer: 2, why: 'Those hands have never pulled a rope or lifted a crate.' },
      { lead: 'lately', options: ['weeks at sea', 'ill in bed', 'in a cold city'], answer: 0, why: 'Brown to the cuff line, white above it. Think.' },
      { lead: 'and carries', options: ['nothing', 'a knife', 'a pistol he has never fired'], answer: 2, why: 'The new leather creaks under his left arm.' },
    ],
    gives: 'profile',
  },
};

// Fight prediction
export const FIGHTS = {
  fight: {
    who: 'cairo',
    title: 'Cairo\'s pistol',
    prompt: 'Time stops. Plan three moves. Remember what you read in him.',
    moves: [
      { id: 'inside', label: 'Step inside the gun arm' },
      { id: 'wrist', label: 'Strike the wrist' },
      { id: 'elbow', label: 'Elbow to the jaw' },
      { id: 'barrel', label: 'Grab the barrel' },
      { id: 'talk', label: 'Keep him talking' },
      { id: 'watson', label: 'Signal to Watson' },
    ],
    plan: ['inside', 'wrist', 'elbow'],
    why: {
      barrel: 'He holds it at arm\'s length. To reach the barrel I must walk into the muzzle.',
      talk: 'He came to search, not to talk. His finger is already on the trigger.',
      watson: 'Watson is across the room. The pistol would swing to him.',
      wrist: 'From out here? He would see it coming and fire. Get inside first.',
      elbow: 'With the pistol still in his hand? The blow would set it off.',
      inside: 'Too late for that now.',
    },
    success: [
      'Holmes steps in under the gun arm, so close that the pistol points at the window.',
      'A short chop to the wrist: the soft hand opens, the pistol thumps onto the rug.',
      'An elbow to the jaw, and Mr. Joel Cairo sits down very suddenly on the slit cushion.',
      ['Holmes', 'Your pistol, Mr. Cairo. And now your pockets, if you please.'],
    ],
    gives: null,
  },
};

export const EVENTS = {
  fight: { type: 'fight' },
};

export const SPOTS = [
  { id: 'card', place: 'salver', label: 'A card on the salver', clue: 'card', r: 1.8 },
  { id: 'desk', place: 'desk', label: 'The writing desk', clue: 'searched', r: 2.2 },
  { id: 'cushion', place: 'cushion', r: 1.8, say: 'Slit with a penknife and searched to the springs. Something the size of a loaf of bread, Watson, or he would not have bothered with the cushion.' },
  { id: 'books', place: 'books', r: 1.8, say: 'Pulled out to look behind them, not to read. A man looking for a hiding place, not a document.' },
  { id: 'bedroom', place: 'bedroom', r: 2.2, say: 'The bedroom has had the same treatment. Even the wardrobe.' },
  { id: 'window', place: 'window', r: 2.4, say: 'Market Street, and the fog coming in off the bay. Somewhere down there is a woman in blue gloves.' },
  { id: 'pockets', pos: [-1.9, 0.9, 0], r: 1.8, label: 'Cairo\'s pockets, on the table', clues: ['pockets', 'ticket', 'clipping'], after: 'fight' },
];

export const CLOSEUP = null;

export const TALK = {
  watson: {
    hello: [['Watson', 'Who on earth would search our rooms, Holmes? We have nothing worth stealing.']],
    topics: [
      { q: 'Somebody thinks we have, Watson.', a: [['Watson', 'Archer\'s business, then?'], ['Holmes', 'Archer\'s business, and Miss Wonderly\'s.']] },
      { q: 'The card, Watson.', needs: ['card'], a: [['Watson', 'Gardenia! One could smell the fellow from the corridor.'], ['Holmes', 'He wished to be remembered. Or he does not know any better.']] },
    ],
  },
  cairo: {
    hello: [['Cairo', 'Mr. Holmes! Forgive the intrusion. I am Joel Cairo.'], ['Holmes', 'You have been through my drawers, Mr. Cairo.'], ['Cairo', 'A misunderstanding, monsieur. Permit me to explain.']],
    topics: [
      { q: 'What do you want here?', gives: 'offer', a: [['Cairo', 'I am trying to recover an ornament that has been mislaid. A statuette: the black figure of a bird.'], ['Cairo', 'I am prepared to pay, on behalf of its rightful owner, five thousand dollars.'], ['Holmes', 'Five thousand. And you thought you might find it in my desk drawer.']] },
      { q: 'I have no bird, Mr. Cairo.', needs: ['offer'], event: 'fight', a: [['Cairo', 'Then you will not object, monsieur, if I finish looking.'], ['Cairo', 'You will please clasp your hands together at the back of your neck.']] },
      {
        q: 'Where have you come from, Mr. Cairo?', after: 'fight',
        a: [['Cairo', 'From New York, monsieur. Last week.']],
        challenge: {
          tell: 'He pulls his cuff down over a line of sunburn.',
          answer: 'lie', evidence: ['tan', 'clipping', 'traveller'], gives: 'hongkong',
          right: [['Holmes', 'New York in November does not brown a man to the cuff, and your pocket holds the arrivals from Hong Kong.'], ['Cairo', '...Hong Kong, then. On the City of Peking. A lady came with me as far as Honolulu. Then she did not.'], ['Holmes', '(A lady. Blue gloves, I fancy.)']],
          wrong: [['Cairo', 'New York, monsieur. A tiresome city.']],
        },
      },
      {
        q: 'Who else is looking for this bird?', after: 'fight',
        a: [['Cairo', 'No one, monsieur. I assure you.']],
        challenge: {
          tell: 'His hand goes to the empty holster, and comes away again.',
          answer: 'doubt', gives: 'fatman',
          right: [['Holmes', 'You are afraid of someone, Mr. Cairo, and it is not me.'], ['Cairo', '...There is a man. A fat man. If he finds it first, monsieur, neither of us will live to be sorry.']],
          wrong: [['Cairo', 'No one at all.']],
        },
      },
      { q: 'Your pistol, Mr. Cairo.', after: 'fight', a: [['Holmes', 'You may have it back when you leave. Unloaded.'], ['Cairo', 'You are very kind, monsieur.']] },
    ],
  },
};

export const CONCLUSION = {
  needs: ['believesHolmes', 'rival', 'wonderlyKnown'],
  question: 'Why did Cairo search your rooms?',
  answers: [
    { a: 'To rob a famous detective', right: false, reply: 'He left my watch on the dresser and my money in the drawer. No.' },
    { a: 'The fat man sent him', right: false, reply: 'Cairo goes white at the thought of a fat man. Nobody sent him; he is running a race.' },
    { a: 'To find Miss Wonderly\'s sister', right: false, reply: 'There is no sister, Watson. There never was.' },
    { a: 'He thinks Miss Wonderly hired Archer to find the bird, and that I have it now', right: true, reply: 'She left him at Honolulu with the bird, he thinks, and came to Archer. Archer is dead, I was in the room, so I must have it.' },
  ],
  epilogue: [
    ['Watson', 'And now he knows you have not got it.'],
    ['Holmes', 'He knows I say so. He will go to the Geary Theatre tonight and tell someone, and I should very much like to know who sits in the next seat.'],
    ['Holmes', 'But first, Watson, Miss Wonderly. Her card in Archer\'s pocket said the St. Mark Hotel, and I think she is not called Wonderly at all.'],
  ],
};

export function objective(s) {
  if (s.solved) return 'Chapter complete';
  if (!s.talked.includes('cairo') && !s.events.includes('portrait')) return s.has('card') || s.has('searched') ? 'The visitor is still here. Speak to him' : 'Look around: who has been in our rooms?';
  if (!s.events.includes('fight')) return s.has('offer') ? 'Hear what Mr. Cairo has to say' : 'Ask Mr. Cairo what he wants';
  if (!['pockets', 'ticket', 'clipping'].every(c => s.has(c))) return 'Empty Mr. Cairo\'s pockets onto the table';
  if (!s.has('hongkong') || !s.has('fatman')) return 'Question Mr. Cairo. He lies, and he is frightened';
  if (s.canConclude) return 'Open the Mind Palace: why did Cairo search your rooms?';
  const missing = CONCLUSION.needs.filter(d => !s.deductions.includes(d)).length;
  return `Mind Palace: ${missing} key deduction${missing > 1 ? 's' : ''} still to make`;
}

for (const id of Object.keys(DEDUCTIONS)) console.assert(!CLUES[id], `id "${id}" is both a clue and a deduction`);
