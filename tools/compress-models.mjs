// Shrinks the game's models for the download: textures to WebP (characters' skin kept at 2048 for the faces, sets
// capped at 1024), geometry kept Draco-compressed. Run after any Blender build:  npm run compress [names...]
// It never renames or merges anything, so the game's lookups by name (bones, CableCar, glass_clear, lace) hold.
// Textures already in WebP are left alone, so running it twice does no harm.
import { NodeIO } from '@gltf-transform/core';
import { ALL_EXTENSIONS } from '@gltf-transform/extensions';
import { textureCompress, draco } from '@gltf-transform/functions';
import sharp from 'sharp';
import draco3d from 'draco3dgltf';
import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const DIR = 'public/models';
const SETS = new Set(['burritt', 'hopkins', 'kearny', 'palace', 'stmark']);

const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({
  'draco3d.decoder': await draco3d.createDecoderModule(),
  'draco3d.encoder': await draco3d.createEncoderModule(),
});

const only = process.argv.slice(2);
const files = readdirSync(DIR).filter(f => f.endsWith('.glb') && (!only.length || only.includes(f.replace('.glb', ''))));
let before = 0, after = 0;
for (const f of files) {
  const path = join(DIR, f), name = f.replace('.glb', '');
  const size0 = statSync(path).size;
  const doc = await io.read(path);
  const todo = doc.getRoot().listTextures().filter(t => t.getMimeType() !== 'image/webp');
  if (!todo.length) { console.log(`${f}: already compressed`); before += size0; after += size0; continue; }
  const cap = SETS.has(name) ? 1024 : 2048;
  await doc.transform(
    textureCompress({ encoder: sharp, targetFormat: 'webp', quality: 82, resize: [cap, cap], slots: /.*/ }),
    draco({ method: 'edgebreaker', encodeSpeed: 3, decodeSpeed: 5 }),
  );
  await io.write(path, doc);
  const size1 = statSync(path).size;
  before += size0; after += size1;
  console.log(`${f}: ${(size0 / 1048576).toFixed(2)} MB -> ${(size1 / 1048576).toFixed(2)} MB`);
}
console.log(`total ${(before / 1048576).toFixed(1)} MB -> ${(after / 1048576).toFixed(1)} MB`);
