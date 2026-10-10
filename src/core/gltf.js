// One glTF loader for the game, with Draco geometry decoding (decoder in public/draco). It also adds up the bytes
// of every model in flight, so the loading screen can show real progress on a slow connection.
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

export const gltfLoader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('draco/'));

const files = new Map();  // url -> [loaded, total]
let listener = null;
export function onLoadProgress(fn) { listener = fn; }
function report() {
  let loaded = 0, total = 0;
  for (const [l, t] of files.values()) { loaded += l; total += Math.max(t, l); }
  listener?.(loaded, total);
}
const loadAsync = gltfLoader.loadAsync.bind(gltfLoader);
// a download the server drops halfway (it happens on slow links) is tried again, up to three more times
gltfLoader.loadAsync = async (url, onProgress) => {
  for (let attempt = 0; ; attempt++) {
    try {
      return await loadAsync(url, e => {
        files.set(url, [e.loaded, e.lengthComputable ? e.total : 0]);
        report();
        onProgress?.(e);
      });
    } catch (err) {
      if (attempt >= 3) throw err;
      files.set(url, [0, files.get(url)?.[1] ?? 0]); report();
      await new Promise(r => setTimeout(r, 1000 * 2 ** attempt));
    }
  }
};

// a set's data file, tried again like the models if the connection drops it
export async function fetchJSON(url) {
  for (let attempt = 0; ; attempt++) {
    try {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`${url}: ${r.status}`);
      return await r.json();
    } catch (err) {
      if (attempt >= 3) throw err;
      await new Promise(r => setTimeout(r, 1000 * 2 ** attempt));
    }
  }
}
