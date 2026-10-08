// Investigation progress: what Holmes has found, heard and worked out.
// Saved per browser; the game works the same if storage is unavailable.
import { CLUES, DEDUCTIONS, CONCLUSION, TALK } from '../cases/archer.js';

const CHALLENGES = Object.values(TALK).flatMap(t => t.topics).filter(t => t.challenge).length;

const KEY = 'blackbird.archer.v1';

export class CaseState {
  constructor() { this.reset(); }

  reset() {
    this.clues = ['wonderly'];
    this.deductions = [];
    this.talked = [];
    this.solved = false;
    this.calls = {};        // interrogation challenge id -> true (right) / false (wrong)
    this.reads = [];        // Focus readings noticed, 'person:index'
    this.misses = 0;        // Mind Palace combinations that came to nothing
    this.wrongAccusations = 0;
  }

  load() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY));
      if (!s) return false;
      this.clues = s.clues.filter(c => CLUES[c]);
      this.deductions = s.deductions.filter(d => DEDUCTIONS[d]);
      this.talked = s.talked ?? [];
      this.solved = !!s.solved;
      this.calls = s.calls ?? {};
      this.reads = s.reads ?? [];
      this.misses = s.misses ?? 0;
      this.wrongAccusations = s.wrongAccusations ?? 0;
      return true;
    } catch { return false; }
  }

  save() {
    try { localStorage.setItem(KEY, JSON.stringify({ clues: this.clues, deductions: this.deductions, talked: this.talked, solved: this.solved,
      calls: this.calls, reads: this.reads, misses: this.misses, wrongAccusations: this.wrongAccusations })); } catch { /* private mode */ }
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

  objective() {
    if (this.solved) return 'Chapter complete';
    if (!this.talked.includes('polhaus')) return 'Speak with Sergeant Polhaus';
    if (!this.has('coat') && !this.has('wound')) return 'Examine Archer\'s body';
    const hidden = ['heel', 'scent', 'webley'].filter(c => !this.has(c)).length;
    if (hidden && this.clues.length < 7) return 'Search the alley. Use Focus to see what others miss';
    if (this.canConclude) return 'Open the Mind Palace and name the killer';
    if (this.deductions.length === 0) return 'Combine what you know in the Mind Palace';
    const missing = CONCLUSION.needs.filter(d => !this.deductions.includes(d)).length;
    return `Mind Palace: ${missing} key deduction${missing > 1 ? 's' : ''} still to make`;
  }
}
