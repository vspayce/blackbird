// The chapter being played, chosen by the URL (?chapter=4). Everything else imports the case from here,
// so the engine never names a chapter. A chapter module exports the same names as archer.js.
import * as archer from './archer.js';
import * as cairo from './cairo.js';
import * as brigid from './brigid.js';
import * as gutman from './gutman.js';
import * as gunsel from './gunsel.js';

const CHAPTERS = { 1: archer, 2: cairo, 3: brigid, 4: gutman, 5: gunsel };
// the next chapter that can be played after each
export const NEXT_PLAYABLE = { 1: 2, 2: 3, 3: 4, 4: 5 };
export const chapterNames = { 1: archer.CHAPTER.title, 2: cairo.CHAPTER.title, 3: brigid.CHAPTER.title, 4: gutman.CHAPTER.title, 5: gunsel.CHAPTER.title };
export const chapterNumber = Number(new URLSearchParams(location.search).get('chapter')) || 1;
const c = CHAPTERS[chapterNumber] ?? archer;

export const { CHAPTER, CLUES, DEDUCTIONS, PEOPLE, ABSENT, SPOTS, CLOSEUP, TALK, READS, CONCLUSION, EVENTS, TAIL, PORTRAITS, FIGHTS,
  combine, wrongLine, objective } = c;
