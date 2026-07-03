/* ================================================================
   AI Orb Renderer v2.1 — Stark Edition
   ================================================================ */

console.log("[OrbV2] Arquivo orb_v2.js carregado!");

class OrbRenderer {
   static STATES = {
      idle: {
         speed: 0.20, pulseAmt: 0.10, pulseFreq: 0.55, waveAmt: 0.0,
         brightness: 1.1, saturation: 1.0, hueShift: 0.0, noiseScale: 0.60,
         innerR: 0.55, glowSize: 1.30, rotation: 0.06, chromaAber: 0.0,
         flicker: 0.0, sparks: 0.05,
      },
      thinking: {
         speed: 0.60, pulseAmt: 0.20, pulseFreq: 1.5, waveAmt: 0.15,
         brightness: 1.2, saturation: 1.2, hueShift: -30.0, noiseScale: 0.80,
         innerR: 0.50, glowSize: 1.40, rotation: 0.50, chromaAber: 0.01,
         flicker: 0.05, sparks: 0.40,
      },
      speaking: {
         speed: 0.45, pulseAmt: 0.08, pulseFreq: 1.8, waveAmt: 0.12,
         brightness: 1.3, saturation: 1.2, hueShift: 0.0, noiseScale: 0.65,
         innerR: 0.60, glowSize: 1.45, rotation: 0.20, chromaAber: 0.0,
         flicker: 0.0, sparks: 0.35,
      },
      listening: {
         speed: 0.30, pulseAmt: 0.12, pulseFreq: 1.1, waveAmt: 0.06,
         brightness: 1.1, saturation: 1.0, hueShift: 60.0, noiseScale: 0.52,
         innerR: 0.58, glowSize: 1.30, rotation: -0.15, chromaAber: 0.0,
         flicker: 0.0, sparks: 0.15,
      },
      error: {
         speed: 1.2, pulseAmt: 0.35, pulseFreq: 5.0, waveAmt: 0.40,
         brightness: 1.3, saturation: 1.4, hueShift: -130.0, noiseScale: 1.1,
         innerR: 0.5, glowSize: 1.4, rotation: 1.0, chromaAber: 0.02,
         flicker: 0.5, sparks: 1.0,
      }
   };

   static VERT = `
    precision highp float;
    attribute vec2 position;
    attribute vec2 uv;
    varying vec2 vUv;
    void main(){ vUv=uv; gl_Position=vec4(position,0.0,1.0); }`;

   static FRAG = `
    precision highp float;
    uniform float iTime;
    uniform vec3  iResolution;
    uniform float hue;
    uniform float uSpeed;
    uniform float uPulseAmt;
    uniform float uPulsePhase;
    uniform float uWaveAmt;
    uniform float uBrightness;
    uniform float uSaturation;
    uniform float uHueShift;
    uniform float uNoiseScale;
    uniform float uInnerR;
    uniform float uGlowSize;
    uniform float uRotation;
    uniform float uChromaAber;
    uniform float uFlicker;
    uniform float uSparks;
    uniform float uVolume;
    varying vec2  vUv;

    vec3 rgb2yiq(vec3 c){ return vec3(dot(c,vec3(.299,.587,.114)),dot(c,vec3(.596,-.274,-.322)),dot(c,vec3(.211,-.523,.312))); }
    vec3 yiq2rgb(vec3 c){ return vec3(c.x+.956*c.y+.621*c.z,c.x-.272*c.y-.647*c.z,c.x-1.106*c.y+1.703*c.z); }
    vec3 adjustHue(vec3 color, float hDeg){
        float h=hDeg*3.14159/180.0;
        vec3 yiq=rgb2yiq(color);
        float c2=cos(h); float s2=sin(h);
        float i2=yiq.y*c2-yiq.z*s2;
        float q2=yiq.y*s2+yiq.z*c2;
        yiq.y=i2; yiq.z=q2;
        return clamp(yiq2rgb(yiq),0.0,1.0);
    }

    float hash21(vec2 p){ p=fract(p*vec2(127.1,311.7)); p+=dot(p,p+19.19); return fract(p.x*p.y); }
    
    vec3 hash33(vec3 p){
        p=fract(p*vec3(.1031,.11369,.13787));
        p+=dot(p,p.yxz+19.19);
        return -1.0+2.0*fract(vec3(p.x+p.y,p.x+p.z,p.y+p.z)*p.zyx);
    }

    float snoise3(vec3 p){
        const float K1=.333333; const float K2=.166667;
        vec3 i=floor(p+(p.x+p.y+p.z)*K1);
        vec3 d0=p-(i-(i.x+i.y+i.z)*K2);
        vec3 e=step(vec3(0.0),d0-d0.yzx);
        vec3 i1=e*(1.0-e.zxy); vec3 i2=1.0-e.zxy*(1.0-e);
        vec3 d1=d0-(i1-K2); vec3 d2=d0-(i2-K1); vec3 d3=d0-0.5;
        vec4 h=max(0.6-vec4(dot(d0,d0),dot(d1,d1),dot(d2,d2),dot(d3,d3)),0.0);
        vec4 n=h*h*h*h*vec4(dot(d0,hash33(i)),dot(d1,hash33(i+i1)),dot(d2,hash33(i+i2)),dot(d3,hash33(i+1.0)));
        return dot(vec4(31.316),n);
    }

    float light1(float i,float a,float d){return i/(1.0+d*a);}
    float light2(float i,float a,float d){return i/(1.0+d*d*a);}

    vec4 extractAlpha(vec3 c){
        float a=max(max(c.r,c.g),c.b);
        return vec4(c/(a+1e-5),a);
    }

    const vec3 baseColor1=vec3(.0, .8, 1.0); // Ciano Stark
    const vec3 baseColor2=vec3(.0, .3, 1.0); // Azul Profundo

    vec4 draw(vec2 uv){
        float totalHue = hue + uHueShift;
        vec3 c1=adjustHue(baseColor1,totalHue);
        vec3 c2=adjustHue(baseColor2,totalHue);

        float len = length(uv);
        float invLen = len > 0.0 ? 1.0/len : 0.0;
        float pulse = sin(uPulsePhase * 6.2832) * uPulseAmt + uVolume * 0.2;
        float n0 = snoise3(vec3(uv*uNoiseScale, iTime*uSpeed))*0.5+0.5;

        float r0 = uInnerR + pulse + n0 * 0.05;
        
        // Núcleo
        float core = light2(1.5, 5.0, len / r0);
        core *= smoothstep(1.1, 0.0, len / r0);

        // Borda
        float d0 = distance(uv, (r0*invLen)*uv);
        float v0 = light1(1.2, 20.0, d0) * smoothstep(r0*1.2, r0*0.5, len);

        vec3 finalCol = mix(c1, c2, n0) * (v0 + core * 0.8);
        
        // Highlights
        float a2 = iTime * uSpeed * -1.5;
        vec2 hPos = vec2(cos(a2), sin(a2)) * r0;
        float d1 = distance(uv, hPos);
        finalCol += light2(2.0, 4.0, d1) * light1(1.0, 40.0, d0) * c1;

        finalCol = pow(finalCol * uBrightness, vec3(0.9));
        return extractAlpha(finalCol);
    }

    void main(){
        vec2 center = iResolution.xy * 0.5;
        float sz = min(iResolution.x, iResolution.y);
        vec2 uv = (vUv * iResolution.xy - center) / sz * 2.0;

        float s=sin(uRotation); float c=cos(uRotation);
        uv = vec2(c*uv.x-s*uv.y, s*uv.x+c*uv.y);

        float wave = uWaveAmt * 0.1 + uVolume * 0.15;
        uv.x += wave * sin(uv.y * 5.0 + iTime);
        uv.y += wave * cos(uv.x * 5.0 + iTime);

        vec4 col = draw(uv);
        gl_FragColor = vec4(col.rgb * col.a, col.a);
    }
   `;

   constructor(container, opts = {}) {
      this.container = container;
      this.hue = opts.hue ?? 0;
      this._current = { ...OrbRenderer.STATES.idle };
      this._target = { ...OrbRenderer.STATES.idle };
      this._rot = 0;
      this._lastTs = 0;
      this._pulsePhase = 0;
      this._volume = 0;
      this.canvas = document.createElement('canvas');
      this.canvas.style.cssText = 'width:100%;height:100%;display:block;';
      container.appendChild(this.canvas);
      this.gl = this.canvas.getContext('webgl', { alpha: true });
      this._build();
      this._resize();
      window.addEventListener('resize', () => this._resize());
      this._loop(0);
   }

   setState(name) {
      const def = OrbRenderer.STATES[name];
      if (def) { this._target = { ...def }; this.container.dataset.orbState = name; }
   }

   setVolume(v) { this._volume = v; }

   _compile(type, src) {
      const s = this.gl.createShader(type);
      this.gl.shaderSource(s, src);
      this.gl.compileShader(s);
      if (!this.gl.getShaderParameter(s, this.gl.COMPILE_STATUS)) return null;
      return s;
   }

   _build() {
      const gl = this.gl;
      const vs = this._compile(gl.VERTEX_SHADER, OrbRenderer.VERT);
      const fs = this._compile(gl.FRAGMENT_SHADER, OrbRenderer.FRAG);
      this.pgm = gl.createProgram();
      gl.attachShader(this.pgm, vs);
      gl.attachShader(this.pgm, fs);
      gl.linkProgram(this.pgm);
      gl.useProgram(this.pgm);
      const posBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, posBuf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 3,-1, -1,3]), gl.STATIC_DRAW);
      const posLoc = gl.getAttribLocation(this.pgm, 'position');
      gl.enableVertexAttribArray(posLoc);
      gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 0, 0);
      const uvBuf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, uvBuf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0,0, 2,0, 0,2]), gl.STATIC_DRAW);
      const uvLoc = gl.getAttribLocation(this.pgm, 'uv');
      gl.enableVertexAttribArray(uvLoc);
      gl.vertexAttribPointer(uvLoc, 2, gl.FLOAT, false, 0, 0);
      this.u = {};
      ['iTime','iResolution','hue','uSpeed','uPulseAmt','uPulsePhase','uWaveAmt','uBrightness','uSaturation','uHueShift','uNoiseScale','uInnerR','uGlowSize','uRotation','uChromaAber','uFlicker','uSparks','uVolume'].forEach(n => {
         this.u[n] = gl.getUniformLocation(this.pgm, n);
      });
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
   }

   _resize() {
      const dpr = window.devicePixelRatio || 1;
      this.canvas.width = this.container.clientWidth * dpr;
      this.canvas.height = this.container.clientHeight * dpr;
      this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
   }

   _loop(ts) {
      requestAnimationFrame(t => this._loop(t));
      const t = ts * 0.001;
      const dt = this._lastTs ? t - this._lastTs : 0.016;
      this._lastTs = t;
      const k = Math.min(dt * 4.0, 1.0);
      for (const key in this._target) this._current[key] += (this._target[key] - this._current[key]) * k;
      this._rot += this._current.rotation * dt;
      this._pulsePhase += this._current.pulseFreq * dt;
      this.gl.clear(this.gl.COLOR_BUFFER_BIT);
      this.gl.uniform1f(this.u.iTime, t);
      this.gl.uniform3f(this.u.iResolution, this.canvas.width, this.canvas.height, 1.0);
      this.gl.uniform1f(this.u.hue, this.hue);
      this.gl.uniform1f(this.u.uSpeed, this._current.speed);
      this.gl.uniform1f(this.u.uPulseAmt, this._current.pulseAmt);
      this.gl.uniform1f(this.u.uPulsePhase, this._pulsePhase);
      this.gl.uniform1f(this.u.uWaveAmt, this._current.waveAmt);
      this.gl.uniform1f(this.u.uBrightness, this._current.brightness);
      this.gl.uniform1f(this.u.uSaturation, this._current.saturation);
      this.gl.uniform1f(this.u.uHueShift, this._current.hueShift);
      this.gl.uniform1f(this.u.uNoiseScale, this._current.noiseScale);
      this.gl.uniform1f(this.u.uInnerR, this._current.innerR);
      this.gl.uniform1f(this.u.uGlowSize, this._current.glowSize);
      this.gl.uniform1f(this.u.uRotation, this._rot);
      this.gl.uniform1f(this.u.uChromaAber, this._current.chromaAber);
      this.gl.uniform1f(this.u.uFlicker, this._current.flicker);
      this.gl.uniform1f(this.u.uSparks, this._current.sparks);
      this.gl.uniform1f(this.u.uVolume, this._volume);
      this.gl.drawArrays(this.gl.TRIANGLES, 0, 3);
   }
}