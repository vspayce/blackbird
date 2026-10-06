// Investigation progress: what Holmes has found, heard and worked out.
// Saved per browser; the game works the same if storage is unavailable.
import { CLUES, DEDUCTIONS, CONCLUSION } from '../cases/archer.js';

const KEY = 'blackbird.archer.v1';

export class CaseState {
  constructor() { this.reset(); }

  reset() {
    this.clues = ['wonderly'];
    this.deductions = [];
    this.talked = [];
    this.solved = false;
  }

  load() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY));
      if (!s) return false;
      this.clues = s.clues.filter(c => CLUES[c]);
      this.deductions = s.deductions.filter(d => DEDUCTIONS[d]);
      this.talked = s.talked ?? [];
      this.solved = !!s.solved;
      return true;
    } catch { return false; }
  }

  save() {
    try { localStorage.setItem(KEY, JSON.stringify({ clues: this.clues, deductions: this.deductions, talked: this.talked, solved: this.solved })); } catch { /* private mode */ }
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
