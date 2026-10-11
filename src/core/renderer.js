// Renderer: the scene renders HDR into a multisampled target, a bloom pass
// lets only the truly bright things (gas flames, lit windows) glow into the
// fog, then one grade pass does ACES, sRGB, a cold night grade, vignette,
// grain and the Focus look (bleached, blue, only the brightest keep colour).
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const Grade = {
  uniforms: {
    tDiffuse: { value: null },
    uTime: { value: 0 },
    uFocus: { value: 0 },
    uExposure: { value: 1.25 },
    uAspect: { value: 1.7 },
  },
  vertexShader: /* glsl */`
    varying vec2 vUv;
    void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse;
    uniform float uTime, uFocus, uExposure, uAspect;
    varying vec2 vUv;
    vec3 aces(vec3 x) {
      const float a = 2.51, b = 0.03, c = 2.43, d = 0.59, e = 0.14;
      return clamp((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0);
    }
    float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
    void main() {
      vec2 cc = vUv - 0.5;
      // Focus pulls the frame inward a touch
      vec2 uv = vUv - cc * dot(cc, cc) * 0.08 * uFocus;
      vec3 c = texture2D(tDiffuse, uv).rgb * uExposure;
      float lum = dot(c, vec3(0.2126, 0.7152, 0.0722));
      // night grade: cool shadows, warm lamplight
      c = mix(c, c * vec3(0.86, 0.95, 1.12), smoothstep(0.35, 0.0, lum));
      // Focus: drain colour except from the brightest (revealed) things
      float keep = smoothstep(0.75, 1.6, lum);
      vec3 grey = vec3(lum) * vec3(0.82, 0.92, 1.08);
      c = mix(c, mix(grey, c, keep), uFocus * 0.92);
      c = aces(c);
      c = pow(c, vec3(1.0 / 2.2));
      float v = smoothstep(0.85, 0.2, length(cc * vec2(uAspect * 0.7, 1.0)));
      c *= mix(1.0, v, 0.55 + uFocus * 0.3);
      c += (hash(vUv * 900.0 + uTime) - 0.5) * (0.035 + uFocus * 0.03);
      gl_FragColor = vec4(c, 1.0);
    }`,
};

export class Renderer {
  constructor(canvas) {
    this.r = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
    this.r.setPixelRatio(Math.min(devicePixelRatio, 1.75));
    this.r.toneMapping = THREE.NoToneMapping;
  }

  setup(scene, camera) {
    this.scene = scene; this.camera = camera;
    const rt = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
    this.composer = new EffectComposer(this.r, rt);
    this.composer.addPass(new RenderPass(scene, camera));
    // threshold above 1: lamplit walls never bloom, only light sources do
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.38, 0.45, 1.3);
    this.composer.addPass(this.bloom);
    this.grade = new ShaderPass(Grade);
    this.composer.addPass(this.grade);
    this.resize();
    addEventListener('resize', () => this.resize());
  }

  resize() {
    const w = innerWidth, h = innerHeight;
    this.r.setSize(w, h, false);
    this.composer.setPixelRatio(this.r.getPixelRatio());
    this.composer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.grade.uniforms.uAspect.value = w / h;
  }

  render(t, focus) {
    this.grade.uniforms.uTime.value = t % 100;
    this.grade.uniforms.uFocus.value = focus;
    this.composer.render();
  }
}
