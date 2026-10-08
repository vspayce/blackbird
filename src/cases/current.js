// The chapter being played, chosen by the URL (?chapter=4). Everything else imports the case from here,
// so the engine never names a chapter. A chapter module exports the same names as archer.js.
import * as archer from './archer.js';
import * as gutman from './gutman.js';
import * as gunsel from './gunsel.js';

const CHAPTERS = { 1: archer, 4: gutman, 5: gunsel };
export const chapterNumber = Number(new URLSearchParams(location.search).get('chapter')) || 1;
const c = CHAPTERS[chapterNumber] ?? archer;

export const { CHAPTER, CLUES, DEDUCTIONS, PEOPLE, ABSENT, SPOTS, CLOSEUP, TALK, READS, CONCLUSION, EVENTS, TAIL,
  combine, wrongLine, objective } = c;
