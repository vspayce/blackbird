// Chapter III: The St. Mark. "Miss Wonderly" at the St. Mark Hotel, packing to leave, the morning after Floyd
// Thursby was shot dead in Geary Street. She lies about everything. Focus shows her tells while she speaks, and a
// lie can be broken mid-sentence by presenting the fact that contradicts it. The question: who shot Thursby?
// Positions in the stmark world (art/build_stmark.py).
import { PEOPLE as CH1, CLUES as C1 } from './archer.js';
import { CLUES as C2 } from './cairo.js';

export const CHAPTER = {
  id: 'brigid',
  number: 'III',
  title: 'Chapter III · The St. Mark',
  next: 'Chapter IV · The Fat Man',
  world: 'stmark',
  start: 'spawn',
  focusTalk: true,
  startClues: ['wonderly', 'offer', 'hongkong', 'fatman', 'theatre'],
  ride: { to: 'Ellis Street', place: 'The St. Mark Hotel', time: 'The next morning' },
  opening: 'Trunks, Watson, and a hatbox by the door. We are only just in time.',
  intro: [
    'Last night Holmes sat three rows behind Joel Cairo at the Geary Theatre. The seat beside Cairo stayed empty.',
    'At half past eleven, three streets away, a man named Floyd Thursby was shot dead outside his hotel.',
    'In the morning Holmes goes to the St. Mark Hotel, and asks for a lady with blue gloves.',
    ['Holmes', 'She will lie to us, Watson. Watch her hands, not her face. Her face has had a great deal of practice.'],
  ],
  summary: 'Miles Archer was shot in Burritt Alley. Joel Cairo offered Holmes $5,000 for a black bird. Last night Floyd Thursby, the man "Miss Wonderly" asked Archer to follow, was shot dead in Geary Street.',
};

export const CLUES = {
  wonderly: C1.wonderly,
  offer: C2.offer,
  hongkong: C2.hongkong,
  fatman: C2.fatman,
  theatre: { kind: 'memory', title: 'Cairo at the Geary', text: 'Last night, the Geary Theatre. Cairo sat alone through all three acts, and I sat three rows behind him. The curtain came down at a quarter to twelve.' },
  thursby: { kind: 'clue', title: 'The morning Call', text: '"Floyd Thursby shot dead outside the Hotel Geary at half past eleven. Two shots. The police seek a woman seen with him earlier in the evening."' },
  boots: { kind: 'clue', title: 'Walking boots', text: 'Small, narrow boots set to dry on the fender, wet street mud caked to the ankle. Someone walked a long way last night, in the rain.' },
  letters: { kind: 'clue', title: 'Letters on the desk', text: 'Three letters and the hotel\'s bill, every one addressed to "Miss Brigid O\'Shaughnessy". Not one to Miss Wonderly.' },
  label: { kind: 'clue', title: 'A steamer label', text: 'Pasted on the end of the trunk: "Pacific Mail S.S. Co. City of Peking. Hong Kong. Stateroom." Half scraped off, as if someone had thought better of it.' },
  scrap: { kind: 'clue', title: 'A scrap in the grate', text: 'Burnt newsprint, the shipping column: "...due from Hong Kong, the La Paloma, Capt. Jacobi..." The rest is ash.' },
  realname: { kind: 'testimony', who: 'brigid', title: 'Brigid O\'Shaughnessy', text: 'Her name is Brigid O\'Shaughnessy. "Wonderly" was borrowed for Archer.' },
  nosister: { kind: 'testimony', who: 'brigid', title: 'No sister', text: 'There is no sister and never was. She hired Archer to follow Thursby, not to find anyone.' },
  sawit: { kind: 'testimony', who: 'brigid', title: 'She was there', text: 'She went out at eleven to warn Thursby, and was across the street when he was shot.' },
  boy: { kind: 'testimony', who: 'brigid', title: 'A boy in a cap', text: '"Hardly more than a boy. A cap and an overcoat too big for him. He fired twice from a doorway and walked away. He didn\'t run."' },
  partner: { kind: 'testimony', who: 'brigid', title: 'Partners in Hong Kong', text: 'She and Cairo came from Hong Kong together, with Thursby. They were after the same thing, and fell out at Honolulu.' },
};

export const DEDUCTIONS = {
  notCairo: { from: ['theatre', 'thursby'], title: 'Not Cairo', text: 'Thursby died at half past eleven. At half past eleven Cairo was in the stalls of the Geary Theatre with me three rows behind. Whoever fired, it was not Cairo.', key: true },
  gunman: { from: ['boy', 'fatman'], title: 'The fat man\'s boy', text: 'Cairo fears a fat man; a boy in a cap fired twice and walked away like a man who had done it before. A fat man does not do his own shooting. He keeps a gunman.', key: true },
  allLies: { from: ['realname', 'nosister'], title: 'Every word a lie', text: 'A false name, a sister who never was. Everything she told Archer was invented, and Archer died of it.', key: true },
  paloma: { from: ['scrap', 'label'], title: 'Something coming by sea', text: 'She came from Hong Kong, and she burnt the column that says when the La Paloma comes in from Hong Kong. What she is waiting for is on that ship.' },
  witness: { from: ['boots', 'sawit'], title: 'She walked to Geary Street', text: 'Mud to the ankle: she walked there and back, alone, in the rain. Frightened of something, but not too frightened to go.' },
};

const WRONG = [
  'No. Those two facts have nothing to say to one another.',
  'Data, Watson, but not a deduction.',
  'She has me thinking crookedly. Again.',
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
  brigid: ['Blue gloves, never off', 'Lavender water', 'Packing in a hurry', 'Hasn\'t slept'],
  watson: ['Hasn\'t slept', 'Already half in love with her'],
};

export const PEOPLE = {
  watson: { ...CH1.watson, pos: [-2.6, 0, 3.2], face: [-1.6, -3.6] },
  brigid: {
    name: 'Brigid O\'Shaughnessy', role: '"Miss Wonderly"',
    note: 'Tall, slender, dark red hair, eyes of cobalt blue. Blue gloves she will not take off. She lies the way other people breathe.',
    pos: [-1.6, 0, -3.6], face: [0, 4],
    look: { model: 'brigid', coat: '#34498a', trousers: '#34498a', hair: '#7a2a16', height: 1.7 },
  },
};

export const ABSENT = {
  archer: { name: 'Miles Archer', role: 'Shot in Burritt Alley', note: 'Shot at arm\'s length by someone he trusted.' },
  thursby: { name: 'Floyd Thursby', role: 'Shot last night in Geary Street', note: 'The man Archer was hired to follow. A gunman himself, by his reputation in the Orient.' },
  cairo: { name: 'Joel Cairo', role: 'The Levantine', note: 'At the Geary Theatre last night, all three acts. I was three rows behind him.' },
};

export const PORTRAITS = null;
export const FIGHTS = null;
export const EVENTS = {};
export const TAIL = null;

export const SPOTS = [
  { id: 'paper', place: 'paper', label: 'The morning paper', clue: 'thursby', r: 1.8 },
  { id: 'boots', place: 'boots', label: 'Boots on the fender', clue: 'boots', r: 1.6 },
  { id: 'desk', place: 'desk', label: 'Letters on the desk', clue: 'letters', r: 2.0 },
  { id: 'trunk', place: 'trunk', label: 'The steamer trunk', clue: 'label', r: 1.9 },
  { id: 'grate', place: 'grate', label: 'Something in the grate', clue: 'scrap', r: 1.6, focus: true },
  { id: 'bedroom', place: 'bedroom', r: 2.2, say: 'The wardrobe is empty and the bed not slept in. She meant to be gone before anyone came.' },
  { id: 'window', place: 'window', r: 2.2, say: 'Ellis Street. A cab is waiting at the kerb with a trunk-strap over the roof. Hers, I imagine.' },
];

export const CLOSEUP = null;

// Lines Brigid says carry a third element: { tell } (seen in Focus) and { present } (break it with a fact).
const B = (text, opts) => ['Brigid', text, opts];

export const TALK = {
  watson: {
    hello: [['Watson', 'She is very young, Holmes. And very frightened.']],
    topics: [
      { q: 'Frightened, Watson, and lying.', a: [['Watson', 'You cannot know that.'], ['Holmes', 'Watch her hands while she talks. Use your eyes as I use mine.']] },
      { q: 'What do you make of the trunks?', needs: ['label'], a: [['Watson', 'She means to leave the city. Today.'], ['Holmes', 'She means to leave it by sea. The question is which ship.']] },
      { q: 'Did you see her face, Watson?', needs: ['boy'], a: [['Watson', 'She was terrified when she spoke of that boy. That was real, Holmes, I would swear to it.'], ['Holmes', 'So would I. The rest of it, not.']] },
    ],
  },
  brigid: {
    hello: [
      ['Brigid', 'Mr. Holmes! I... how did you find me?'],
      ['Holmes', 'The Palace Hotel has a bell captain who forgets nothing, and the St. Mark has a doorman who will take a dollar.'],
      ['Brigid', 'You must think me dreadful. Please, sit down. I have so little time.'],
    ],
    topics: [
      {
        q: 'Good morning, Miss Wonderly.',
        a: [
          B('Yes. Of course. I\'m so sorry about Mr. Archer, truly I am.'),
          B('Wonderly is my name, Mr. Holmes. Whatever you have heard.', {
            tell: 'Her eyes flick to the desk by the window, and away.',
            present: {
              id: 'name', evidence: ['letters'], gives: 'realname',
              right: [['Holmes', 'Then your correspondents are mistaken. Every letter on that desk says O\'Shaughnessy. So does your hotel bill.'], B('...Brigid O\'Shaughnessy. Wonderly was... something I borrowed. I couldn\'t go to Mr. Archer with my own name.')],
              wrong: [B('I don\'t know what you mean by that, Mr. Holmes.')],
            },
          }),
          ['Holmes', '(The desk. Something on it she does not want me to read.)'],
        ],
      },
      {
        q: 'Tell me about your sister.', needs: ['realname'],
        a: [B('Corinne. She ran away with Thursby, and I came to bring her home. That is all it ever was.')],
        challenge: {
          tell: 'Not a tremor. Her hands lie still in her lap. The gloves do not move at all.',
          focusTell: true, answer: 'doubt', gives: 'nosister',
          right: [['Holmes', 'Yesterday your glove twisted at every mention of Thursby, and never once for your poor sister. There is no Corinne.'], B('...No. There isn\'t. I needed Mr. Archer to follow Floyd, and a sister was the kind of story people believe.')],
          wrong: [B('You\'re very kind, Mr. Holmes. Poor Corinne.')],
        },
      },
      {
        q: 'Where were you last night?',
        a: [
          B('Here. I didn\'t go out at all.', {
            tell: 'Her eyes go, just once, to the fender, and come back to you.',
            present: {
              id: 'night', evidence: ['boots', 'witness'], gives: 'sawit',
              right: [['Holmes', 'Then someone has borrowed your boots and walked them through the mud of half of San Francisco. They are still drying on the fender.'], B('...I went to warn Floyd. At eleven. He wouldn\'t listen to me. I was across the street when...'), B('When it happened. I ran all the way back.')],
              wrong: [B('Nowhere. Truly.')],
            },
          }),
          B('I was ill. I went to bed early.'),
        ],
      },
      {
        q: 'Who shot Floyd Thursby?', needs: ['sawit'],
        a: [B('I didn\'t see. It was dark, and the fog...')],
        challenge: {
          tell: 'Her left glove: she twists it at the wrist, hard enough to hurt.',
          focusTell: true, answer: 'doubt', gives: 'boy',
          right: [['Holmes', 'You were across the street under a lamp. You saw.'], B('...A boy. Hardly more than a boy, in a cap and an overcoat too big for him.'), B('He stepped out of a doorway and fired twice, and then he walked away. He didn\'t run, Mr. Holmes. That was the worst of it.')],
          wrong: [B('I wish I could help you. I can\'t.')],
        },
      },
      {
        q: 'Where are you going, Miss O\'Shaughnessy?', needs: ['realname'],
        a: [
          B('Only to friends in Oakland, until all this is over.', {
            tell: 'She steps between you and the trunk without seeming to.',
            present: {
              id: 'ship', evidence: ['label', 'hongkong', 'paloma'], gives: 'partner',
              right: [['Holmes', 'Friends in Oakland, and a Pacific Mail label from Hong Kong on your trunk. Mr. Cairo says a lady came with him from Hong Kong, as far as Honolulu.'], B('...Joel told you that. Yes. Joel and Floyd and I came from Hong Kong together. We were after the same thing.'), B('At Honolulu Floyd and I left Joel behind. You can imagine how he took it.')],
              wrong: [B('Oakland, Mr. Holmes. It\'s quite near.')],
            },
          }),
        ],
      },
      {
        q: 'And the black bird?', needs: ['offer'],
        a: [
          B('Bird? I don\'t know anything about a bird.', {
            tell: 'For a moment she is perfectly still, like a cat at a mousehole.',
            present: {
              id: 'bird', evidence: ['offer', 'partner'], gives: null,
              right: [['Holmes', 'Mr. Cairo offered me five thousand dollars for it yesterday, and you came from Hong Kong with Mr. Cairo.'], B('...I can\'t tell you about the bird. Not yet. Please. If I tell you, they\'ll kill me the way they killed Floyd.'), ['Holmes', '(They. Not he.)']],
              wrong: [B('You\'re talking in riddles, Mr. Holmes.')],
            },
          }),
        ],
      },
      { q: 'And Miles Archer?', needs: ['sawit'], a: [B('Poor Mr. Archer. I liked him.'), ['Holmes', '(Nothing. Not a twist of the glove. Nothing at all.)']] },
    ],
  },
};

export const CONCLUSION = {
  needs: ['notCairo', 'gunman', 'allLies'],
  question: 'Who shot Floyd Thursby?',
  answers: [
    { a: 'Brigid O\'Shaughnessy', right: false, reply: 'Mud on her boots, Watson, not powder on her gloves. And she was terrified of that boy. Not this time.' },
    { a: 'Joel Cairo', right: false, reply: 'At half past eleven Cairo was in the stalls at the Geary, and I was three rows behind him.' },
    { a: 'A stranger from Thursby\'s past in the Orient', right: false, reply: 'A stranger who fires twice and walks away, the night after Cairo speaks of a fat man? No.' },
    { a: 'The fat man\'s gunman: the boy in the cap', right: true, reply: 'A boy who walks away from a killing, in the pay of a fat man who does not do his own. Thursby stood between the fat man and the bird.' },
  ],
  epilogue: [
    ['Watson', 'A boy, Holmes. And that poor girl in the middle of it.'],
    ['Holmes', 'That poor girl, Watson, told us four lies in a quarter of an hour, and one truth because she was frightened.'],
    ['Holmes', 'Her glove twisted for Thursby and for the boy. For Miles Archer it did not move at all. I find that more interesting than all the rest.'],
    ['Holmes', 'Now: the fat man. A fat man who keeps a gunman will want to meet the man Cairo could not buy. I think we shall be invited.'],
  ],
};

export function objective(s) {
  if (s.solved) return 'Chapter complete';
  if (!s.talked.includes('brigid')) return 'Look around the room, then speak to Miss Wonderly';
  if (!s.has('realname')) return 'She lies. Focus while she speaks, and Present the fact that breaks it';
  if (!s.has('sawit') || !s.has('boy')) return 'Where was she last night? Watch her hands';
  if (!s.has('nosister')) return 'Ask about her sister. Focus on her gloves';
  if (s.canConclude) return 'Open the Mind Palace: who shot Floyd Thursby?';
  const missing = CONCLUSION.needs.filter(d => !s.deductions.includes(d)).length;
  return `Mind Palace: ${missing} key deduction${missing > 1 ? 's' : ''} still to make`;
}

for (const id of Object.keys(DEDUCTIONS)) console.assert(!CLUES[id], `id "${id}" is both a clue and a deduction`);
