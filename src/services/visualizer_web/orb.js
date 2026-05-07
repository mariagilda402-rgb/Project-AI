/* ================================================================
   AI Orb Renderer v2.0 — Multi-State WebGL Visualizer
   ================================================================

   A GPU-accelerated, animated orb that visually represents the
   state of an AI assistant. Designed to be easily embedded in any
   LLM-powered project.

   STATES:
     'idle'      – Slow, calm breathing pulse. Soft glow.
     'thinking'  – Swirling vortex, pulsing irregularly. Purple haze.
     'speaking'  – Active wave distortion, bright & energetic. Cyan.
     'listening' – Gentle inward ripples, attentive look. Blue/green.
     'error'     – Sharp red/orange flicker, unstable edges.
     'loading'   – Spinning ring, cool blue, waiting for connection.
     'success'   – Bright golden-green flash, triumphant pulse.
     'sleeping'  – Nearly dark, ultra-slow breathing, minimal glow.
     'warning'   – Amber pulsing, moderate instability.

   QUICK START (copy-paste into any project):
   ─────────────────────────────────────────
     <div id="ai-orb"></div>
     <script src="orb.js"></script>
     <script>
       const orb = new OrbRenderer(document.getElementById('ai-orb'));
       orb.setState('thinking');   // 'idle' | 'thinking' | 'speaking' | 'listening' | 'error'
       orb.destroy();              // cleanup when done
     </script>
   ─────────────────────────────────────────

   API:
     new OrbRenderer(containerEl, opts?)   – start rendering
     .setState(stateName)                  – change animation state
     .setVolume(0..1)                      – audio-reactive amplitude (for speaking)
     .destroy()                            – cleanup WebGL + listeners

   OPTIONS (opts):
     hue             {number}   – base hue offset in degrees (default: 0)
     backgroundColor {number[]} – [r,g,b] each 0-1 (default: dark navy)
   ================================================================ */

class OrbRenderer {
   /* ─────────────────────────────────────────────────────────────
      STATE DEFINITIONS
      Each state defines target shader uniforms. The renderer
      smoothly interpolates between them for seamless transitions.
   ───────────────────────────────────────────────────────────── */
   static STATES = {
      idle: {
         speed: 0.20,
         pulseAmt: 0.10,
         pulseFreq: 0.55,
         waveAmt: 0.0,
         brightness: 1.05,
         saturation: 0.9,
         hueShift: 0.0,
         noiseScale: 0.60,
         innerR: 0.55,
         glowSize: 1.30,
         rotation: 0.06,
         chromaAber: 0.0,
         flicker: 0.0,
         sparks: 0.05,
      },
      thinking: {
         speed: 0.58,
         pulseAmt: 0.18,
         pulseFreq: 1.5,
         waveAmt: 0.14,
         brightness: 1.15,
         saturation: 1.1,
         hueShift: -25.0,
         noiseScale: 0.82,
         innerR: 0.50,
         glowSize: 1.40,
         rotation: 0.48,
         chromaAber: 0.007,
         flicker: 0.06,
         sparks: 0.40,
      },
      speaking: {
         speed: 0.45,
         pulseAmt: 0.06,
         pulseFreq: 1.8,
         waveAmt: 0.12,
         brightness: 1.1,
         saturation: 1.15,
         hueShift: 30.0,
         noiseScale: 0.65,
         innerR: 0.60,
         glowSize: 1.45,
         rotation: 0.18,
         chromaAber: 0.002,
         flicker: 0.0,
         sparks: 0.35,
      },
      listening: {
         speed: 0.30,
         pulseAmt: 0.12,
         pulseFreq: 1.1,
         waveAmt: 0.06,
         brightness: 1.05,
         saturation: 1.0,
         hueShift: 62.0,
         noiseScale: 0.52,
         innerR: 0.58,
         glowSize: 1.30,
         rotation: -0.14,
         chromaAber: 0.001,
         flicker: 0.0,
         sparks: 0.18,
      },
      error: {
         speed: 1.2,
         pulseAmt: 0.30,
         pulseFreq: 5.0,
         waveAmt: 0.30,
         brightness: 1.2,
         saturation: 1.3,
         hueShift: -130.0,
         noiseScale: 1.1,
         innerR: 0.5,
         glowSize: 1.4,
         rotation: 0.8,
         chromaAber: 0.018,
         flicker: 0.4,
         sparks: 0.9,
      },
      loading: {
         speed: 0.35,
         pulseAmt: 0.08,
         pulseFreq: 0.8,
         waveAmt: 0.03,
         brightness: 0.9,
         saturation: 0.85,
         hueShift: 45.0,
         noiseScale: 0.55,
         innerR: 0.54,
         glowSize: 1.25,
         rotation: 0.65,
         chromaAber: 0.002,
         flicker: 0.0,
         sparks: 0.22,
      },
      success: {
         speed: 0.40,
         pulseAmt: 0.22,
         pulseFreq: 1.0,
         waveAmt: 0.05,
         brightness: 1.35,
         saturation: 1.25,
         hueShift: 85.0,
         noiseScale: 0.58,
         innerR: 0.62,
         glowSize: 1.55,
         rotation: 0.10,
         chromaAber: 0.0,
         flicker: 0.0,
         sparks: 0.55,
      },
      sleeping: {
         speed: 0.08,
         pulseAmt: 0.04,
         pulseFreq: 0.2,
         waveAmt: 0.0,
         brightness: 0.35,
         saturation: 0.5,
         hueShift: 10.0,
         noiseScale: 0.45,
         innerR: 0.52,
         glowSize: 1.10,
         rotation: 0.01,
         chromaAber: 0.0,
         flicker: 0.0,
         sparks: 0.0,
      },
      warning: {
         speed: 0.55,
         pulseAmt: 0.20,
         pulseFreq: 2.2,
         waveAmt: 0.15,
         brightness: 1.1,
         saturation: 1.2,
         hueShift: -100.0,
         noiseScale: 0.75,
         innerR: 0.52,
         glowSize: 1.35,
         rotation: 0.30,
         chromaAber: 0.008,
         flicker: 0.15,
         sparks: 0.50,
      },
   };

   /* ─────────────────────────────────────────────────────────────
      VERTEX SHADER
      Full-screen triangle trick: 3 verts cover the entire viewport.
   ───────────────────────────────────────────────────────────── */
   static VERT = `
    precision highp float;
    attribute vec2 position;
    attribute vec2 uv;
    varying vec2 vUv;
    void main(){ vUv=uv; gl_Position=vec4(position,0.0,1.0); }`;

   /* ─────────────────────────────────────────────────────────────
      FRAGMENT SHADER
      All visual magic happens here. Uniforms drive every state.
   ───────────────────────────────────────────────────────────── */
   static FRAG = `
    precision highp float;

    /* ── Uniforms ── */
    uniform float iTime;
    uniform vec3  iResolution;
    uniform float hue;          // global hue offset (degrees)

    /* State uniforms — all smoothly interpolated on the JS side */
    uniform float uSpeed;
    uniform float uPulseAmt;
    uniform float uPulsePhase;   // accumulated phase (avoids freq*time jump)
    uniform float uWaveAmt;
    uniform float uBrightness;
    uniform float uSaturation;
    uniform float uHueShift;    // per-state hue offset
    uniform float uNoiseScale;
    uniform float uInnerR;
    uniform float uGlowSize;
    uniform float uRotation;    // current accumulated rotation (radians)
    uniform float uChromaAber;
    uniform float uFlicker;
    uniform float uSparks;
    uniform float uVolume;      // external audio amplitude 0-1

    uniform vec3  backgroundColor;
    varying vec2  vUv;

    /* ── Color helpers ── */
    vec3 rgb2yiq(vec3 c){
        return vec3(dot(c,vec3(.299,.587,.114)),dot(c,vec3(.596,-.274,-.322)),dot(c,vec3(.211,-.523,.312)));
    }
    vec3 yiq2rgb(vec3 c){
        return vec3(c.x+.956*c.y+.621*c.z,c.x-.272*c.y-.647*c.z,c.x-1.106*c.y+1.703*c.z);
    }
    vec3 adjustHue(vec3 color, float hueDeg){
        float h=hueDeg*3.14159265/180.0;
        vec3 yiq=rgb2yiq(color);
        float c2=cos(h); float s2=sin(h);
        float i2=yiq.y*c2-yiq.z*s2;
        float q2=yiq.y*s2+yiq.z*c2;
        yiq.y=i2; yiq.z=q2;
        return clamp(yiq2rgb(yiq),0.0,1.0);
    }

    /* ── Hash & Noise ── */
    vec3 hash33(vec3 p){
        p=fract(p*vec3(.1031,.11369,.13787));
        p+=dot(p,p.yxz+19.19);
        return -1.0+2.0*fract(vec3(p.x+p.y,p.x+p.z,p.y+p.z)*p.zyx);
    }
    float snoise3(vec3 p){
        const float K1=.333333333; const float K2=.166666667;
        vec3 i=floor(p+(p.x+p.y+p.z)*K1);
        vec3 d0=p-(i-(i.x+i.y+i.z)*K2);
        vec3 e=step(vec3(0.0),d0-d0.yzx);
        vec3 i1=e*(1.0-e.zxy); vec3 i2=1.0-e.zxy*(1.0-e);
        vec3 d1=d0-(i1-K2); vec3 d2=d0-(i2-K1); vec3 d3=d0-0.5;
        vec4 h=max(0.6-vec4(dot(d0,d0),dot(d1,d1),dot(d2,d2),dot(d3,d3)),0.0);
        vec4 n=h*h*h*h*vec4(dot(d0,hash33(i)),dot(d1,hash33(i+i1)),dot(d2,hash33(i+i2)),dot(d3,hash33(i+1.0)));
        return dot(vec4(31.316),n);
    }

    /* Hash to float in [0,1] from vec2 */
    float hash21(vec2 p){
        p=fract(p*vec2(127.1,311.7));
        p+=dot(p,p+19.19);
        return fract(p.x*p.y);
    }

    /* ── Chromatic Aberration ── */
    /* Sample the orb color at a slightly offset UV for fringe effect */
    vec3 chromaticSample(vec2 uv, float amt){
        vec2 dir=normalize(uv+vec2(0.001))*amt;
        return vec3(
            snoise3(vec3((uv+dir)*uNoiseScale,iTime*uSpeed))*0.5+0.5,
            snoise3(vec3(uv*uNoiseScale,iTime*uSpeed+10.0))*0.5+0.5,
            snoise3(vec3((uv-dir)*uNoiseScale,iTime*uSpeed+20.0))*0.5+0.5
        );
    }

    /* ── Soft glow falloff ── */
    float light1(float i,float a,float d){return i/(1.0+d*a);}
    float light2(float i,float a,float d){return i/(1.0+d*d*a);}

    /* ── Extract alpha from brightness ── */
    vec4 extractAlpha(vec3 c){
        float a=max(max(c.r,c.g),c.b);
        return vec4(c/(a+1e-5),a);
    }

    /* ── Base palette ── */
    const vec3 baseColor1=vec3(.611765,.262745,.996078);   // vivid purple
    const vec3 baseColor2=vec3(.298039,.760784,.913725);   // cyan / teal
    const vec3 baseColor3=vec3(.062745,.078431,.600000);   // deep indigo

    /* ── Spark / particle helper ── */
    /* Returns a tiny bright flare at position 'pos' */
    float spark(vec2 uv, vec2 pos, float size){
        float d=length(uv-pos);
        return smoothstep(size,0.0,d)*light2(1.0,800.0,d);
    }

    /* ── Main orb draw ── */
    vec4 draw(vec2 uv){
        float totalHue = hue + uHueShift;
        vec3 c1=adjustHue(baseColor1,totalHue);
        vec3 c2=adjustHue(baseColor2,totalHue);
        vec3 c3=adjustHue(baseColor3,totalHue);

        float ang = atan(uv.y, uv.x);
        float len = length(uv);
        float invLen = len > 0.0 ? 1.0/len : 0.0;
        float bgLum = dot(backgroundColor, vec3(.299,.587,.114));

        /* ── Pulse (breathing / beat) ── */
        float pulse = sin(uPulsePhase * 6.2832) * uPulseAmt;
        /* Volume boost for speaking state */
        pulse += uVolume * uPulseAmt * 2.0;

        /* ── Noise for organic edge ── */
        float n0;
        if(uChromaAber > 0.001){
            /* Multi-sample noise for chromatic edge in thinking/error */
            vec3 ns = chromaticSample(uv, uChromaAber*30.0);
            n0 = (ns.r*0.33 + ns.g*0.34 + ns.b*0.33);
        } else {
            n0 = snoise3(vec3(uv*uNoiseScale, iTime*uSpeed))*0.5+0.5;
        }

        /* ── Wobbly radius ── */
        float innerR = uInnerR + pulse;
        float r0 = mix(mix(innerR,1.0,0.4), mix(innerR,1.0,0.6), n0);

        /* ── Wave distortion (speaking / error) ── */
        /* Already applied before draw() in mainImage, reflected in uv */

        /* ── Core glow ── */
        float d0 = distance(uv, (r0*invLen)*uv);
        float v0 = light1(1.0, 10.0, d0);
        v0 *= smoothstep(r0*1.05, r0, len);
        float innerFade = smoothstep(r0*0.75, r0*0.92, len);
        v0 *= mix(innerFade, 1.0, bgLum*0.7);

        /* ── Orbiting highlight ── */
        float a2 = iTime * uSpeed * -1.5;
        vec2 hPos = vec2(cos(a2), sin(a2)) * r0;
        float d1 = distance(uv, hPos);
        float v1 = light2(1.5, 5.0, d1) * light1(1.0, 50.0, d0);

        /* ── Second, slower highlight for depth ── */
        float a3 = iTime * uSpeed * 0.8 + 1.5;
        vec2 hPos2 = vec2(cos(a3)*0.8, sin(a3)*0.8) * r0;
        float d2 = distance(uv, hPos2);
        float v1b = light2(0.8, 8.0, d2) * light1(1.0, 60.0, d0);

        /* ── Outer / inner fade masks ── */
        float v2 = smoothstep(uGlowSize*0.92, mix(innerR, 1.0, n0*0.5), len);
        float v3 = smoothstep(innerR*0.9, mix(innerR, 1.0, 0.5), len);

        /* ── Sparks / particles ── */
        float sparkVal = 0.0;
        if(uSparks > 0.05){
            /* Generate a few sparks at random edge positions */
            for(int i=0;i<6;i++){
                float fi=float(i);
                float angle = iTime*uSpeed*1.3 + fi*1.047 + sin(iTime*0.7+fi)*0.5;
                float radius = r0*(0.85+0.15*sin(iTime*1.2+fi*2.3));
                vec2 sPos = vec2(cos(angle), sin(angle)) * radius;
                float sz = 0.04 * (0.5+0.5*sin(iTime*2.0+fi));
                sparkVal += spark(uv, sPos, sz) * uSparks;
            }
        }

        /* ── Flicker (error state) ── */
        float flickerMult = 1.0;
        if(uFlicker > 0.01){
            /* Use hash of time to get sharp random flicker */
            float ft = floor(iTime*18.0);
            flickerMult = 1.0 - uFlicker * hash21(vec2(ft, 3.7));
        }

        /* ── Angular color blend ── */
        float cl = cos(ang + iTime*uSpeed*1.5)*0.5+0.5;

        /* ── Compose ── */
        vec3 colBase = mix(c1, c2, cl) * uSaturation;
        colBase = mix(colBase, colBase * 1.3, uBrightness - 1.0); // allow super-brightness
        float fadeAmt = mix(1.0, 0.1, bgLum);

        vec3 darkCol = mix(c3, colBase, v0);
        darkCol = (darkCol + v1 + v1b) * v2 * v3;
        darkCol += vec3(sparkVal) * colBase;
        darkCol = clamp(darkCol * uBrightness * flickerMult, 0.0, 1.0);

        vec3 lightCol = (colBase + v1 + v1b) * mix(1.0, v2*v3, fadeAmt);
        lightCol = mix(backgroundColor, lightCol, v0);
        lightCol += vec3(sparkVal) * colBase;
        lightCol = clamp(lightCol * uBrightness * flickerMult, 0.0, 1.0);

        vec3 fc = mix(darkCol, lightCol, bgLum);
        return extractAlpha(fc);
    }

    /* ── Entry point ── */
    vec4 mainImage(vec2 fragCoord){
        vec2 center = iResolution.xy * 0.5;
        float sz = min(iResolution.x, iResolution.y);
        vec2 uv = (fragCoord - center) / sz * 2.0;

        /* Apply accumulated rotation */
        float s2=sin(uRotation); float c2=cos(uRotation);
        uv = vec2(c2*uv.x-s2*uv.y, s2*uv.x+c2*uv.y);

        /* Wave distortion — multi-octave, volume-reactive */
        float ph = uPulsePhase * 6.2832;
        float volWave = uVolume * 0.7;  // volume drives most of the wave energy
        float baseWave = uWaveAmt * 0.06;  // subtle base wave from state
        float wave = baseWave + volWave * uWaveAmt;

        /* Octave 1: large, slow undulation */
        float t1 = iTime * uSpeed * 2.5;
        uv.x += wave * 0.55 * sin(uv.y * 4.5 + t1 + ph * 0.3);
        uv.y += wave * 0.55 * sin(uv.x * 4.5 + t1 * 1.1 + ph * 0.4);

        /* Octave 2: medium, faster detail */
        uv.x += wave * 0.30 * sin(uv.y * 11.0 + t1 * 1.7 + 2.0);
        uv.y += wave * 0.30 * sin(uv.x * 9.5  + t1 * 1.5 + 3.1);

        /* Octave 3: fine, rapid ripple (only when volume is high) */
        float fineWave = wave * volWave * 0.6;
        uv.x += fineWave * sin(uv.y * 22.0 + t1 * 3.0 + 5.0);
        uv.y += fineWave * sin(uv.x * 18.0 + t1 * 2.8 + 7.0);

        return draw(uv);
    }

    void main(){
        vec2 fc = vUv * iResolution.xy;
        vec4 col = mainImage(fc);
        gl_FragColor = vec4(col.rgb * col.a, col.a);
    }`;

   /* ─────────────────────────────────────────────────────────────
      CONSTRUCTOR
   ───────────────────────────────────────────────────────────── */
   /**
    * @param {HTMLElement} container  – DOM element to render into
    * @param {Object}      opts
    * @param {number}      opts.hue             – global hue offset (degrees)
    * @param {number[]}    opts.backgroundColor – [r,g,b] each 0–1
    */
   constructor(container, opts = {}) {
      this.container = container;
      this.hue = opts.hue ?? 0;
      this.bgColor = opts.backgroundColor ?? [0.02, 0.02, 0.06];

      /* Current interpolated uniform values (start at 'idle') */
      const idle = OrbRenderer.STATES.idle;
      this._current = { ...idle };
      this._target = { ...idle };

      /* Accumulated rotation angle (radians) */
      this._rot = 0;
      this._lastTs = 0;

      /* Accumulated pulse phase (radians) — avoids freq*time jump */
      this._pulsePhase = 0;

      /* External volume (0–1) for speaking state audio-reactivity */
      this._volume = 0;

      /* Active state name */
      this._state = 'idle';

      /* Build WebGL */
      this.canvas = document.createElement('canvas');
      this.canvas.style.cssText = 'width:100%;height:100%;display:block;';
      container.appendChild(this.canvas);

      this.gl = this.canvas.getContext('webgl', { alpha: true, premultipliedAlpha: false, antialias: false });
      if (!this.gl) { console.warn('[OrbRenderer] WebGL not available'); return; }

      this._build();
      this._resize();
      this._onResize = this._resize.bind(this);
      window.addEventListener('resize', this._onResize);
      this._raf = requestAnimationFrame(this._loop.bind(this));
   }

   /* ─────────────────────────────────────────────────────────────
      PUBLIC API
   ───────────────────────────────────────────────────────────── */

   /**
    * Change the orb's visual state.
    * @param {'idle'|'thinking'|'speaking'|'listening'|'error'} name
    */
   setState(name) {
      const def = OrbRenderer.STATES[name];
      if (!def) { console.warn(`[OrbRenderer] Unknown state: "${name}"`); return; }
      this._state = name;
      this._target = { ...def };

      /* Update CSS class for external styling hooks */
      this.container.dataset.orbState = name;
   }

   /**
    * Set audio volume for speaking-state reactivity.
    * @param {number} v  0 (silent) – 1 (loud)
    */
   setVolume(v) {
      this._volume = Math.max(0, Math.min(1, v));
   }

   /**
    * Clean up all resources.
    */
   destroy() {
      cancelAnimationFrame(this._raf);
      window.removeEventListener('resize', this._onResize);
      if (this.canvas.parentNode) this.canvas.parentNode.removeChild(this.canvas);
      const ext = this.gl?.getExtension('WEBGL_lose_context');
      if (ext) ext.loseContext();
   }

   /* ─────────────────────────────────────────────────────────────
      INTERNAL — SHADER SETUP
   ───────────────────────────────────────────────────────────── */
   _compile(type, src) {
      const gl = this.gl;
      const s = gl.createShader(type);
      gl.shaderSource(s, src);
      gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
         console.error('[OrbRenderer] Shader error:', gl.getShaderInfoLog(s));
         gl.deleteShader(s);
         return null;
      }
      return s;
   }

   _build() {
      const gl = this.gl;
      const vs = this._compile(gl.VERTEX_SHADER, OrbRenderer.VERT);
      const fs = this._compile(gl.FRAGMENT_SHADER, OrbRenderer.FRAG);
      if (!vs || !fs) return;

      this.pgm = gl.createProgram();
      gl.attachShader(this.pgm, vs);
      gl.attachShader(this.pgm, fs);
      gl.linkProgram(this.pgm);
      if (!gl.getProgramParameter(this.pgm, gl.LINK_STATUS)) {
         console.error('[OrbRenderer] Link error:', gl.getProgramInfoLog(this.pgm));
         return;
      }
      gl.useProgram(this.pgm);

      /* Full-screen triangle */
      const posLoc = gl.getAttribLocation(this.pgm, 'position');
      const uvLoc = gl.getAttribLocation(this.pgm, 'uv');

      const posBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);

      const uvBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, uvBuf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 0, 2, 0, 0, 2]), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(uvLoc);
      gl.vertexAttribPointer(uvLoc, 2, gl.FLOAT, false, 0, 0);

      /* Cache all uniform locations */
      this.u = {};
      [
         'iTime', 'iResolution', 'hue',
         'uSpeed', 'uPulseAmt', 'uPulsePhase', 'uWaveAmt',
         'uBrightness', 'uSaturation', 'uHueShift',
         'uNoiseScale', 'uInnerR', 'uGlowSize', 'uRotation',
         'uChromaAber', 'uFlicker', 'uSparks', 'uVolume',
         'backgroundColor',
      ].forEach(n => { this.u[n] = gl.getUniformLocation(this.pgm, n); });

      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.clearColor(0, 0, 0, 0);
   }

   /* ─────────────────────────────────────────────────────────────
      INTERNAL — RESIZE
   ───────────────────────────────────────────────────────────── */
   _resize() {
      const dpr = window.devicePixelRatio || 1;
      const w = this.container.clientWidth;
      const h = this.container.clientHeight;
      this.canvas.width = w * dpr;
      this.canvas.height = h * dpr;
      if (this.gl) this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
   }

   /* ─────────────────────────────────────────────────────────────
      INTERNAL — ANIMATION LOOP
   ───────────────────────────────────────────────────────────── */
   _loop(ts) {
      this._raf = requestAnimationFrame(this._loop.bind(this));
      if (!this.pgm) return;

      const gl = this.gl;
      const t = ts * 0.001;
      const dt = this._lastTs ? t - this._lastTs : 0.016;
      this._lastTs = t;

      /* Smooth interpolation of all state parameters */
      const k = Math.min(dt * 3.5, 1);   // ~0.28 s transition
      const cur = this._current;
      const tgt = this._target;
      for (const key in tgt) {
         cur[key] += (tgt[key] - cur[key]) * k;
      }

      /* Accumulate rotation */
      this._rot += cur.rotation * dt;

      /* Accumulate pulse phase using current freq — no freq*time jump */
      this._pulsePhase += cur.pulseFreq * dt;

      /* Upload uniforms */
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.useProgram(this.pgm);

      gl.uniform1f(this.u.iTime, t);
      gl.uniform3f(this.u.iResolution, this.canvas.width, this.canvas.height, this.canvas.width / this.canvas.height);
      gl.uniform1f(this.u.hue, this.hue);

      gl.uniform1f(this.u.uSpeed, cur.speed);
      gl.uniform1f(this.u.uPulseAmt, cur.pulseAmt);
      gl.uniform1f(this.u.uPulsePhase, this._pulsePhase);
      gl.uniform1f(this.u.uWaveAmt, cur.waveAmt);
      gl.uniform1f(this.u.uBrightness, cur.brightness);
      gl.uniform1f(this.u.uSaturation, cur.saturation);
      gl.uniform1f(this.u.uHueShift, cur.hueShift);
      gl.uniform1f(this.u.uNoiseScale, cur.noiseScale);
      gl.uniform1f(this.u.uInnerR, cur.innerR);
      gl.uniform1f(this.u.uGlowSize, cur.glowSize);
      gl.uniform1f(this.u.uRotation, this._rot);
      gl.uniform1f(this.u.uChromaAber, cur.chromaAber);
      gl.uniform1f(this.u.uFlicker, cur.flicker);
      gl.uniform1f(this.u.uSparks, cur.sparks);
      gl.uniform1f(this.u.uVolume, this._volume);

      gl.uniform3f(this.u.backgroundColor, this.bgColor[0], this.bgColor[1], this.bgColor[2]);

      gl.drawArrays(gl.TRIANGLES, 0, 3);
   }
}