// Investigation progress: what Holmes has found, heard and worked out.
// Saved per browser; the game works the same if storage is unavailable.
import { CHAPTER, CLUES, DEDUCTIONS, CONCLUSION, TALK, objective } from '../cases/current.js';

const CHALLENGES = Object.values(TALK).flatMap(t => t.topics).filter(t => t.challenge).length;

const KEY = `blackbird.${CHAPTER.id}.v1`;

export class CaseState {
  constructor() { this.reset(); }

  reset() {
    this.clues = [];
    this.deductions = [];
    this.talked = [];
    this.solved = false;
    this.calls = {};        // interrogation challenge id -> true (right) / false (wrong)
    this.reads = [];        // Focus readings noticed, 'person:index'
    this.misses = 0;        // Mind Palace combinations that came to nothing
    this.wrongAccusations = 0;
    this.events = [];       // story events that have happened (Chapter IV: 'drugged')
    for (const c of CHAPTER.startClues ?? []) if (!this.clues.includes(c)) this.clues.push(c);
  }

  load() {
    try { return this.fromJSON(JSON.parse(localStorage.getItem(KEY))); } catch { return false; }
  }

  // the case as plain data (for saves), and back
  toJSON() {
    return { clues: this.clues, deductions: this.deductions, talked: this.talked, solved: this.solved,
      calls: this.calls, reads: this.reads, misses: this.misses, wrongAccusations: this.wrongAccusations, events: this.events };
  }

  fromJSON(s) {
    if (!s) return false;
    this.clues = s.clues.filter(c => CLUES[c]);
    this.deductions = s.deductions.filter(d => DEDUCTIONS[d]);
    this.talked = s.talked ?? [];
    this.solved = !!s.solved;
    this.calls = s.calls ?? {};
    this.reads = s.reads ?? [];
    this.misses = s.misses ?? 0;
    this.wrongAccusations = s.wrongAccusations ?? 0;
    this.events = s.events ?? [];
    return true;
  }

  save() {
    try { localStorage.setItem(KEY, JSON.stringify(this.toJSON())); } catch { /* private mode */ }
  }

  static hasSave() {
    try { return !!localStorage.getItem(KEY); } catch { return false; }
  }

  has(id) { return this.clues.includes(id) || this.deductions.includes(id); }

  addClue(id) {
    if (this.clues.includes(id)) return false;
    this.clues.push(id); this.save();
    return true;
  }

  addDeduction(id) {
    if (this.deductions.includes(id)) return false;
    this.deductions.push(id); this.save();
    return true;
  }

  addEvent(e) {
    if (!this.events.includes(e)) { this.events.push(e); this.save(); }
  }

  addRead(key) {
    if (this.reads.includes(key)) return;
    this.reads.push(key); this.save();
  }

  // An L.A. Noire style case rating: what you found, how you read people, and
  // how often you guessed.
  rating() {
    const clues = Object.keys(CLUES).length, deds = Object.keys(DEDUCTIONS).length;
    const calls = Object.values(this.calls);
    const found = this.clues.length / clues, drawn = this.deductions.length / deds;
    const read = calls.filter(Boolean).length / CHALLENGES;
    const score = found * 2 + drawn * 1.5 + read * 1.5 - Math.min(1, this.misses * 0.15) - this.wrongAccusations * 0.75;
    return {
      stars: Math.max(1, Math.min(5, Math.round(score))),
      rows: [
        ['Clues found', `${this.clues.length} / ${clues}`],
        ['Deductions drawn', `${this.deductions.length} / ${deds}`],
        ['Interrogations read', `${calls.filter(Boolean).length} / ${CHALLENGES}`],
        ['False starts in the Mind Palace', String(this.misses)],
        ['Wrong accusations', String(this.wrongAccusations)],
      ],
    };
  }

  get canConclude() { return CONCLUSION.needs.every(d => this.deductions.includes(d)); }

  objective() { return objective(this); }

}
