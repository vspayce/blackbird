// One glTF loader for the game, with Draco geometry decoding (decoder in public/draco).
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

export const gltfLoader = new GLTFLoader().setDRACOLoader(new DRACOLoader().setDecoderPath('draco/'));
