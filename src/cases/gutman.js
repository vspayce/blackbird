// Chapter IV: The Fat Man. The Mark Hopkins Institute of Art on Nob Hill, December 1895.
// Kasper Gutman has asked Holmes to meet him there at ten o'clock. He tells the falcon's history from the top
// of the tower, and drugs Holmes's whisky; Holmes pieces the evening back together and works out where the bird
// is. Same shape as archer.js. Positions are in the Hopkins world (y up; the upper floor is at 6 m, the tower
// observatory at 22 m). worldId spots borrow their place and label from hopkins.json's interactions.
import { PEOPLE as CH1 } from './archer.js';

export const CHAPTER = {
  id: 'gutman',
  number: 'IV',
  title: 'Chapter IV · The Fat Man',
  next: 'Chapter V · The Gunsel',
  world: 'hopkins',
  ride: { to: 'Nob Hill', place: 'The Mark Hopkins Institute of Art', time: 'Ten o\'clock at night' },
  start: 'spawn',
  startClues: ['note'],
  // Gutman asked for Holmes alone: Watson stays below the tower until the whisky
  watsonWaits: { until: 'drugged', above: 15, line: 'Wait here, Watson. He asked for me alone, and I should like him to think he has it.' },
  opening: 'Ten o\'clock, Watson, and the Hopkins house lit up like a lantern. Somewhere inside it is the Fat Man.',
  intro: [
    'San Francisco. November, 1895.',
    'Two nights since Miles Archer died in Burritt Alley, and one since Floyd Thursby died in Geary Street.',
    'Since then a Levantine named Joel Cairo has offered Holmes five thousand dollars for a black statuette of a bird, and Miss Wonderly has become Miss O\'Shaughnessy, and lied four more times in a quarter of an hour.',
    'Everyone who wants the bird is afraid of one man. They call him the Fat Man. His name is Kasper Gutman.',
    'Tonight a note was left at the Palace Hotel. "The Hopkins Institute, ten o\'clock. Come alone. K. G."',
    ['Holmes', 'Alone, Watson. So of course you will come.'],
  ],
  summary: 'Gutman has summoned Holmes to the Mark Hopkins Institute of Art, the old Hopkins mansion on Nob Hill. Cairo wants the black bird; Miss O\'Shaughnessy lies about it; both fear Gutman.',
};

// kind: 'clue' (seen), 'testimony' (heard), 'memory' (already known or remembered)
export const CLUES = {
  note: { kind: 'memory', title: 'Gutman\'s note', text: 'Left at the Palace Hotel: "The Hopkins Institute, ten o\'clock tonight. Come alone. K. G." Heavy cream paper, and a thumbprint of cigar ash.' },
  carriage: { kind: 'clue', title: 'A brougham on the drive', text: 'Hired from the Palace Hotel stables. The seat is crushed deep on one side and still warm: a very heavy man came up the hill in it a few minutes ago.' },
  engravings: { kind: 'clue', title: 'Engravings of Malta', text: 'Valletta, the Grand Harbour, the Grand Master\'s palace: the Association\'s prints, handled tonight. Pencil notes in the margins in a large, careful hand: "1530. 1539. Algiers?"' },
  glove: { kind: 'clue', title: 'A blue kid glove', text: 'Fallen behind the cushion of the model\'s throne. A lady\'s, blue kid, and it smells of lavender water. Miss Wonderly wore blue gloves she would not take off.' },
  tribute: { kind: 'clue', title: 'The Knights\' rent', text: 'A history of the Order of St. John from the Association\'s library, marked at the page: in 1530 the Emperor gave Malta to the Knights for a yearly rent of one falcon.' },
  shipping: { kind: 'clue', title: 'Shipping news', text: 'Folded small under the telescope: the Call\'s column of ships due from the Orient. One is ringed in pencil. La Paloma, from Hong Kong, due at the Pacific Mail wharf on Thursday.' },
  telescope: { kind: 'clue', title: 'The telescope', text: 'Not pointed at the stars. It is trained low over the city, on the Pacific Mail wharf at the foot of Brannan Street, and clamped there.' },
  curator: { kind: 'testimony', who: 'wren', title: 'Wren: Mr. Gutman', text: 'Gutman has read in the library every evening this week: the Knights of St. John, Charles the Fifth, the engravings of Malta. Once a young lady waited for him in the painting studio upstairs.' },
  visitor: { kind: 'testimony', who: 'wren', title: 'Wren: the lady', text: 'She was crying when they left. "I had it in Hong Kong. I had it in my hands." Gutman told her to hush.' },
  history: { kind: 'testimony', who: 'gutman', title: 'Gutman: the black bird', text: 'A falcon of gold crusted with jewels, sent by the Knights to the Emperor in 1539. Taken by corsairs, enamelled black, lost and found across Europe. Gutman has hunted it for seventeen years, and says it is "coming".' },
  notyet: { kind: 'testimony', who: 'gutman', title: 'Gutman: Miss O\'Shaughnessy', text: 'She and Cairo had the bird in Hong Kong. She lost Cairo, and lost the bird, or says she did. Gutman is "a patient man".' },
  drugged: { kind: 'memory', title: 'The drugged whisky', text: 'Gutman poured mine from a different decanter and watched the clock, not the city. Wilmer carried me down to the Print Room. "Thursday, Wilmer. Not before Thursday."' },
};

export const DEDUCTIONS = {
  notHeld: { from: ['history', 'engravings'], title: 'Gutman has not got the bird', text: 'He says it is "coming", and he spends his evenings over engravings of the harbour it sailed from. A man who held the bird would be looking at it, not at pictures.', key: true },
  brigidHere: { from: ['glove', 'curator'], title: 'Brigid has been here with Gutman', text: 'Her blue glove on the model\'s throne, the young lady who waited upstairs while Gutman read. Miss O\'Shaughnessy and the Fat Man are not strangers, whatever either of them says.', key: true },
  atSea: { from: ['shipping', 'telescope'], title: 'He is waiting for a ship', text: 'A telescope clamped on the Pacific Mail wharf and one ship ringed in the shipping news. Gutman is watching for La Paloma.' },
  paloma: { from: ['atSea', 'drugged'], title: 'The bird is aboard La Paloma', text: '"Thursday, not before." He drugged me to keep me out of the way until the ship is in. The bird is at sea, aboard La Paloma, and Gutman means to be on the wharf when she docks.', key: true },
  worth: { from: ['tribute', 'history'], title: 'Why men kill for it', text: 'The rent of an island, in gold and jewels. Archer died for it, and Thursby. There will be others.' },
  hongkong: { from: ['visitor', 'shipping'], title: 'She sent it by sea', text: '"I had it in Hong Kong." La Paloma sails from Hong Kong. She put it aboard herself, or had it put.' },
  partners: { from: ['notyet', 'brigidHere'], title: 'Partners who fell out', text: 'Brigid, Cairo and Gutman hunted it together, and each tried to cheat the others. That is why they all lie: each fears the others more than the police.' },
};

const WRONG = [
  'No. Those two facts have nothing to say to one another.',
  'Data, Watson, but not a deduction.',
  'The whisky is still talking. Again.',
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

// Focus reads on people
export const READS = {
  gutman: ['Waistcoat buttons strained: eats well, sits much', 'Cigar ash on the third button', 'Watches the clock, not the city'],
  wilmer: ['Two guns under the overcoat', 'New shoes, cheap: hired, not trusted', 'Right hand never leaves the pocket'],
  wren: ['Ink on the second finger: keeps the ledgers himself', 'Has not slept well this week'],
  watson: ['Service revolver, right coat pocket', 'Annoyed at being told to wait'],
};

// pos is [x, y, z] in the Hopkins world; face is the [x, z] they look toward. leaves: gone after that event.
export const PEOPLE = {
  watson: CH1.watson,
  wren: {
    name: 'Mr. Wren', role: 'Keeper of the collection',
    note: 'Keeper of the Art Association\'s collection at the Institute. Precise, tidy, and afraid of his most generous patron.',
    pos: [-9.0, 0, -11.6], face: [-11, -8],
    look: { model: 'wren', coat: '#2a2622', trousers: '#2a2622', hair: '#b8b4ac', moustache: '#c8c4bc', height: 1.74 },
  },
  wilmer: {
    name: 'Wilmer', role: 'Gutman\'s gunsel',
    note: 'A boy of twenty with a man\'s overcoat and two guns. He takes Gutman\'s orders and nobody else\'s.',
    pos: [2.2, 0, 17.6], face: [2.2, 25], leaves: 'drugged',
    look: { model: 'wilmer', coat: '#2c2e30', trousers: '#2a2a2c', hat: 'bowler', hatColor: '#3a3632', longCoat: true, height: 1.66 },
  },
  gutman: {
    name: 'Kasper Gutman', role: 'The Fat Man',
    note: 'Enormously fat, enormously polite. Has hunted the black bird across the world for seventeen years.',
    pos: [1.7, 22, 8.8], face: [0, 11.7], leaves: 'drugged',
    look: { model: 'gutman', coat: '#151515', trousers: '#2a2a2c', hair: '#3a3632', longCoat: true, height: 1.78 },
  },
};

// Not here, but in the case
export const ABSENT = {
  brigid: { name: 'Brigid O\'Shaughnessy', role: 'Once "Miss Wonderly"', note: 'Archer\'s client. Blue gloves, lavender water, a different story every time she is caught in the last one.' },
  cairo: { name: 'Joel Cairo', role: 'The Levantine', note: 'Gardenia, a soft voice, a collector\'s eye, and a pistol he did not know how to use.' },
  archer: { name: 'Miles Archer', role: 'Murdered in Burritt Alley', note: 'Shot at arm\'s length by someone he trusted. Holmes has not forgotten him.' },
  jacobi: { name: 'Captain Jacobi', role: 'Master of La Paloma', note: 'Bringing a ship from Hong Kong. Does he know what is in his hold?', needs: 'shipping' },
};

// Places to examine. worldId: placed at that interaction in hopkins.json. needs: clues that must be held first
// (until then the spot says `early`). after: a story event that must have happened. focus: only seen in Focus.
export const SPOTS = [
  { id: 'carriage', label: 'The carriage on the drive', pos: [-8.2, 1.5, 19.2], r: 2.8, clue: 'carriage' },
  { id: 'engravings', worldId: 'prints', label: 'Engravings on the table', clue: 'engravings' },
  { id: 'glove', worldId: 'studio', label: 'The model\'s throne', clue: 'glove', focus: true },
  { id: 'tribute', worldId: 'archive', label: 'The Association\'s library', clue: 'tribute', needs: ['curator'],
    early: 'Histories, catalogues, travels: the whole Association\'s library. Without knowing what Gutman read, I could be here a week.' },
  { id: 'telescope', worldId: 'telescope', label: 'The telescope', clue: 'telescope', after: 'drugged' },
  { id: 'shipping', label: 'A newspaper under the telescope', pos: [1.1, 22.9, 8.1], r: 1.8, clue: 'shipping', after: 'drugged' },
  { id: 'view', worldId: 'view', say: 'The whole city in gaslight, down to the wharves. Somewhere down there a woman in blue gloves is lying to someone.' },
  { id: 'bedroom', worldId: 'bedroom', say: 'Mrs. Hopkins never slept here. She built it, furnished it, and went back East.' },
  { id: 'casts', worldId: 'casts', say: 'Plaster gods, Watson. The students draw them for a year before they are allowed a living model.' },
  { id: 'fountain', worldId: 'fountain', say: 'Dry since the Association took the house. Water costs money on Nob Hill.' },
  { id: 'flood', worldId: 'flood', say: 'Bronze, the length of the block. Flood made his money in silver and wanted everyone to know it.' },
  { id: 'curatorDesk', worldId: 'curator', say: 'A tidy desk and an untidy correspondence: dealers in Paris, Vienna, Constantinople.' },
];

export const CLOSEUP = null;

// Story events. 'reconstruct': the scene breaks off, and the player puts the fragments back in order.
export const EVENTS = {
  drugged: {
    type: 'reconstruct',
    before: ['The whisky is smooth, and very old.', 'Gutman is still talking. His voice comes from a long way off.'],
    title: 'The whisky',
    prompt: 'The room tilts. Put the evening back together, in the order it happened.',
    fragments: [
      'Gutman pours. Two fingers of whisky for me, and his own glass from a different decanter.',
      'He talks of Kemidov and Constantinople, and watches the clock, not the city.',
      'The lamps along East Street slide sideways down the window.',
      'Wilmer\'s hands under my arms. The stair turning, and turning, and turning.',
      'Engravings of Malta under my cheek. Gutman\'s voice, far off: "Thursday, Wilmer. Not before Thursday."',
    ],
    wrong: ['No. That came later.', 'Before that. Think, man.', 'The drug lies. Again.'],
    gives: 'drugged',
    wake: [-11, 6, -7.8],
    after: [['Watson', 'Holmes! Thank God. That boy held me in the hall at the point of a revolver for an hour, and then they simply walked out.'],
      ['Holmes', 'An hour, Watson. He needed me asleep for an hour. Let us see what the Fat Man has left behind in his tower.']],
  },
};

export const TALK = {
  watson: {
    hello: [['Watson', 'Come alone, he says. I have my service revolver, Holmes, and I am coming.']],
    topics: [
      { q: 'What do you make of the house, Watson?', a: [['Watson', 'A railway fortune turned into a castle, and the castle into a school. Hopkins never lived in it, they say.'], ['Holmes', 'He built it for his wife and died before it was done. A house full of pictures and nobody to look at them, until the students came.']] },
      { q: 'What do we know of Gutman?', a: [['Watson', 'Cairo is afraid of him and Miss O\'Shaughnessy is afraid of him, and both of them lie about everything else.'], ['Holmes', 'Fear is the one thing they have both told the truth about. That is worth remembering.']] },
    ],
  },
  wilmer: {
    hello: [['Wilmer', 'Keep walking.'], ['Holmes', 'I was asked here, young man. Ten o\'clock.'], ['Wilmer', 'Then you go in alone. The doctor waits.'], ['Watson', 'The doctor does nothing of the kind.']],
    topics: [
      {
        q: 'Where is Mr. Gutman?',
        a: [['Wilmer', 'He ain\'t here.']],
        challenge: {
          tell: 'His eyes go up to the tower before he answers, and his right hand stays in his overcoat pocket.',
          answer: 'lie', evidence: ['carriage', 'note'],
          right: [['Holmes', 'His carriage is on the drive with the seat still warm, and his own note named this house and this hour. Where is he?'], ['Wilmer', '...Up top. He said you\'d find him. Go on, then.']],
          wrong: [['Wilmer', 'You heard me. Beat it.']],
        },
      },
      { q: 'How long have you worked for Gutman?', a: [['Wilmer', 'Keep on riding me and they\'ll be picking iron out of your liver.'], ['Holmes', '(Twenty, at most. Frightened of everyone in this house except himself.)']] },
    ],
  },
  wren: {
    hello: [['Wren', 'The Institute is closed, sir. Oh! Mr. Holmes. Tobias Wren, keeper of the collection. The Association is honoured.'], ['Holmes', 'Forgive the hour, Mr. Wren. I am told a Mr. Gutman keeps late hours here.']],
    topics: [
      { q: 'What has Mr. Gutman been doing here?', a: [['Wren', 'Reading, sir. Every evening this week, in the library. Histories of the Knights of St. John, our engravings of Malta, anything on the Emperor Charles the Fifth.'], ['Wren', 'A most generous patron. And once a young lady waited for him upstairs, in the painting studio, while he read.']], gives: 'curator' },
      {
        q: 'Tell me about the young lady.', needs: ['curator'],
        a: [['Wren', 'There is nothing to tell, sir. A lady. She waited, and they left together.']],
        challenge: {
          tell: 'He straightens a blotter that is already straight, and does not look up.',
          answer: 'doubt', gives: 'visitor',
          right: [['Holmes', 'There is something, Mr. Wren, or you would not be tidying a tidy desk.'], ['Wren', '...She was crying when they left, sir. She said, "I had it in Hong Kong. I had it in my hands." Mr. Gutman told her to hush. I should not have listened.']],
          wrong: [['Wren', 'Then we understand each other, sir. Good night.']],
        },
      },
      { q: 'The engravings of Malta.', needs: ['engravings'], a: [['Wren', 'Still out on the table? He asked for them every night. He said he was studying the harbour. I think, sir, he was looking at the ships.']] },
    ],
  },
  gutman: {
    hello: [['Gutman', 'Mr. Holmes! By Gad, sir, you came alone, or near enough. I like a man who keeps an appointment.'], ['Gutman', 'From up here one can see the whole city, and the whole bay. I have spent a week looking at it.']],
    topics: [
      {
        q: 'Tell me about the bird.', gives: 'history',
        a: [
          ['Gutman', 'In 1530, sir, the Emperor Charles the Fifth gave the island of Malta to the Knights of St. John. The rent was one falcon a year.'],
          ['Gutman', 'In 1539 the Knights, rich beyond counting from their Turkish prizes, sent him no live bird. They sent a falcon of gold, a foot high, crusted from head to foot with the finest jewels in their coffers.'],
          ['Gutman', 'It never reached him. Corsairs took the galley, and the bird went to Algiers. From there to Sicily, to Naples, to Paris. Somewhere along the way some careful soul gave it a coat of black enamel, and it became a curiosity worth a few hundred francs.'],
          ['Gutman', 'Seventeen years I have followed it, sir. To Constantinople, to a Russian general named Kemidov who did not know what he had. And now it is coming here.'],
          ['Holmes', 'Coming, Mr. Gutman? Not here already?'],
          ['Gutman', 'Ha! You are a man after my own heart, sir. Coming. Yes.'],
        ],
      },
      {
        q: 'And Miss O\'Shaughnessy?',
        a: [['Gutman', 'A charming name, sir. I don\'t believe I know the lady.']],
        challenge: {
          tell: 'He laughs, and his chins shake, a moment too long. His eyes do not laugh at all.',
          answer: 'lie', evidence: ['glove', 'visitor', 'brigidHere'], gives: 'notyet',
          right: [['Holmes', 'She left her glove on the model\'s throne downstairs, Mr. Gutman.'], ['Gutman', 'By Gad, sir. Very well. She had the bird in Hong Kong, she and Cairo between them, and she contrived to lose both Cairo and the bird. I have been patient with her. I am a patient man.']],
          wrong: [['Gutman', 'Shall we talk of things that matter, sir?']],
        },
      },
      {
        q: 'Why are you telling me all this?', needs: ['history'], event: 'drugged',
        a: [['Gutman', 'Because I like you, sir, and because I need a man of your talents. Will you take a drink? This whisky came round the Horn.'], ['Gutman', 'To the black bird, sir.']],
      },
    ],
  },
};

export const CONCLUSION = {
  needs: ['notHeld', 'brigidHere', 'paloma'],
  question: 'Where is the black bird?',
  answers: [
    { a: 'In Gutman\'s rooms at the Alexandria', right: false, reply: 'If he had it, Watson, he would not spend his evenings reading about it.' },
    { a: 'With Miss O\'Shaughnessy', right: false, reply: 'She had it in Hong Kong. She has not got it now, or Gutman would not be watching the harbour.' },
    { a: 'Hidden here, in the Institute', right: false, reply: 'Among the pictures? Gutman came here to read, not to hide things. The Association\'s treasures are its books.' },
    { a: 'Aboard La Paloma, coming from Hong Kong', right: true, reply: 'The clamped telescope, the ringed ship, and "Thursday, not before". It is at sea, and Gutman is waiting for it.' },
  ],
  epilogue: [
    ['Watson', 'Then we go down to the wharf on Thursday.'],
    ['Holmes', 'Gutman will be there before us, and the boy will be watching us long before that. He followed us up the hill tonight, Watson. He is outside now.'],
    ['Holmes', 'Let him follow. I have a fancy to see how well young Wilmer knows the fog.'],
  ],
};

export function objective(s) {
  if (s.solved) return 'Chapter complete';
  if (!s.events.includes('drugged')) {
    if (!s.talked.includes('gutman')) {
      if (!s.has('curator')) return 'Find out what Gutman has been doing here. The keeper may know';
      return 'Gutman is waiting at the top of the tower';
    }
    return 'Hear the Fat Man out';
  }
  if (!s.has('shipping') || !s.has('telescope')) return 'Gutman has gone. Search the tower observatory';
  if (s.canConclude) return 'Open the Mind Palace: where is the black bird?';
  if (!s.has('glove')) return 'Someone else has been here. Use Focus in the studios upstairs';
  if (!s.has('engravings')) return 'What has Gutman been reading? Try the Print Room';
  const missing = CONCLUSION.needs.filter(d => !s.deductions.includes(d)).length;
  return `Mind Palace: ${missing} key deduction${missing > 1 ? 's' : ''} still to make`;
}

for (const id of Object.keys(DEDUCTIONS)) console.assert(!CLUES[id], `id "${id}" is both a clue and a deduction`);
