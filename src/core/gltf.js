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
gltfLoader.loadAsync = (url, onProgress) => loadAsync(url, e => {
  files.set(url, [e.loaded, e.lengthComputable ? e.total : 0]);
  report();
  onProgress?.(e);
});
