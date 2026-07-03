
// ═══════════════════════════════════════════════════════════════
//  JARVIS ORB  —  Advanced Emotional Visualizer  v2.0
//  States: idle | listening | thinking | speaking | alert | success
//  Backend mappings also accept executing | processing | loading | searching | browsing | warning | error | sleeping
// ═══════════════════════════════════════════════════════════════

const canvas = document.getElementById('orb');
const ctx    = canvas.getContext('2d');
const label  = document.getElementById('emotion-label');

let W, H, CX, CY, R;
function resize() {
  W = canvas.width  = canvas.offsetWidth  || window.innerWidth;
  H = canvas.height = canvas.offsetHeight || window.innerHeight;
  CX = W / 2; CY = H / 2;
  R  = Math.min(W, H) * 0.34;
}
window.addEventListener('resize', resize);
resize();

// ─── EMOTION PROFILES ───────────────────────────────────────────
const EMOTIONS = {
  idle:      { label:'STANDBY',    core:[0,180,255],  glow:[0,100,220],   ring:[0,210,255],  speed:.008, pulseAmp:.038, pulseFq:1.1, rings:2, scan:false, pts:10, brt:.72 },
  listening: { label:'ESCUTANDO',  core:[70,225,115], glow:[15,175,75],   ring:[80,255,145], speed:.018, pulseAmp:.080, pulseFq:2.0, rings:3, scan:true,  pts:22, brt:.88 },
  thinking:  { label:'PROCESSANDO',core:[175,70,255], glow:[130,20,220],  ring:[200,100,255],speed:.034, pulseAmp:.120, pulseFq:3.0, rings:5, scan:true,  pts:36, brt:1.0  },
  speaking:  { label:'FALANDO',    core:[0,200,255],  glow:[0,130,240],   ring:[60,225,255], speed:.026, pulseAmp:.140, pulseFq:4.5, rings:4, scan:false, pts:28, brt:1.0  },
  alert:     { label:'ALERTA',     core:[255,75,55],  glow:[220,20,15],   ring:[255,120,80], speed:.052, pulseAmp:.180, pulseFq:5.0, rings:4, scan:true,  pts:40, brt:1.0  },
  success:   { label:'CONCLUÍDO',  core:[55,230,155], glow:[15,185,115],  ring:[80,255,175], speed:.012, pulseAmp:.055, pulseFq:1.5, rings:3, scan:false, pts:24, brt:.90 },
};

// ─── STATE ──────────────────────────────────────────────────────
let curEmo = 'idle', tgtEmo = 'idle', blendT = 1.0;
let emo = { ...EMOTIONS.idle };
let T = 0, volume = 0, scanA = 0;
let wsConnected = false;
let demoCycle = null;
let demoIndex = 0;

function startDemoCycle() {
  if (demoCycle || wsConnected) return;
  demoCycle = setInterval(() => {
    setEmotion(_CYCLE[demoIndex++ % _CYCLE.length]);
  }, 2800);
}

function stopDemoCycle() {
  if (demoCycle) {
    clearInterval(demoCycle);
    demoCycle = null;
  }
}

// ─── LERP ────────────────────────────────────────────────────────
const lerp = (a, b, t) => a + (b - a) * t;
const lerpRGB = (a, b, t) => [lerp(a[0],b[0],t), lerp(a[1],b[1],t), lerp(a[2],b[2],t)];
const rgb = (c, a = 1) => `rgba(${c[0]|0},${c[1]|0},${c[2]|0},${a})`;

// ─── PARTICLES ───────────────────────────────────────────────────
class Particle {
  constructor() { this.reset(true); }
  reset(first = false) {
    const ang = Math.random() * Math.PI * 2;
    const d   = R * (.82 + Math.random() * .55);
    this.x  = CX + Math.cos(ang) * d;
    this.y  = CY + Math.sin(ang) * d;
    this.vx = (Math.random() - .5) * .55;
    this.vy = (Math.random() - .5) * .55;
    this.a  = Math.random() * .55 + .15;
    this.sz = Math.random() * 2.4 + .5;
    this.lt = first ? Math.random() * 200 : (Math.random() * 180 + 60);
    this.ml = this.lt;
  }
  tick() { this.x += this.vx; this.y += this.vy; this.lt--; if (this.lt <= 0) this.reset(); }
  draw(c) {
    const f = this.lt / this.ml;
    ctx.beginPath();
    ctx.arc(this.x, this.y, this.sz * f, 0, Math.PI * 2);
    ctx.fillStyle = rgb(c, this.a * f);
    ctx.fill();
  }
}
let parts = [];
function ensureParts(n) {
  while (parts.length < n) parts.push(new Particle());
  if (parts.length > n) parts.length = n;
}
ensureParts(12);

// ─── BLEND ───────────────────────────────────────────────────────
function blended() {
  if (blendT >= 1) return EMOTIONS[curEmo];
  const a = EMOTIONS[curEmo], b = EMOTIONS[tgtEmo], k = blendT;
  return {
    core:  lerpRGB(a.core, b.core, k), glow: lerpRGB(a.glow, b.glow, k),
    ring:  lerpRGB(a.ring, b.ring, k), speed: lerp(a.speed, b.speed, k),
    pulseAmp: lerp(a.pulseAmp, b.pulseAmp, k), pulseFq: lerp(a.pulseFq, b.pulseFq, k),
    rings: Math.round(lerp(a.rings, b.rings, k)), scan: k > .5 ? b.scan : a.scan,
    pts:   Math.round(lerp(a.pts,  b.pts,  k)), brt: lerp(a.brt, b.brt, k),
  };
}

// ─── DRAW LOOP ───────────────────────────────────────────────────
function frame() {
  requestAnimationFrame(frame);

  if (blendT < 1) {
    blendT = Math.min(1, blendT + .022);
    if (blendT >= 1) { curEmo = tgtEmo; label.textContent = EMOTIONS[curEmo].label; }
  }

  emo = blended();
  T += emo.speed;
  scanA += emo.speed * .55;
  volume *= .92;

  const breath = 1 + Math.sin(T * emo.pulseFq) * emo.pulseAmp;
  const cR = R * (breath + volume * .22);
  const brt = emo.brt;

  ctx.clearRect(0, 0, W, H);

  // — outer glow halos —
  for (let i = 5; i >= 0; i--) {
    const gr = cR * (1 + i * .16);
    const al = (.055 - i * .008) * brt;
    const g  = ctx.createRadialGradient(CX, CY, cR * .5, CX, CY, gr);
    g.addColorStop(0, rgb(emo.glow, al * 2.2));
    g.addColorStop(1, rgb(emo.glow, 0));
    ctx.beginPath(); ctx.arc(CX, CY, gr, 0, Math.PI * 2);
    ctx.fillStyle = g; ctx.fill();
  }

  // — rotating dashed rings —
  for (let ri = 0; ri < emo.rings; ri++) {
    const frac = ri / emo.rings;
    const rr   = cR * (1.06 + frac * .38);
    const al   = (.38 - frac * .08) * brt;
    const ang  = scanA + ri * (Math.PI * 2 / emo.rings);
    ctx.save();
    ctx.translate(CX, CY);
    ctx.rotate(ang * (ri % 2 === 0 ? 1 : -1.3));
    ctx.translate(-CX, -CY);
    ctx.beginPath(); ctx.arc(CX, CY, rr, 0, Math.PI * 2);
    ctx.setLineDash([4 + ri * 2, 8 + ri * 3]);
    ctx.strokeStyle = rgb(emo.ring, al);
    ctx.lineWidth = 1.5; ctx.stroke();
    ctx.setLineDash([]); ctx.restore();
  }

  // — orb core gradient —
  const cg = ctx.createRadialGradient(CX - cR*.26, CY - cR*.26, cR*.04, CX, CY, cR);
  cg.addColorStop(0,   rgb(emo.core, .95 * brt));
  cg.addColorStop(.38, rgb(emo.glow, .68 * brt));
  cg.addColorStop(.75, rgb([5,10,32], .88));
  cg.addColorStop(1,   rgb([2,4,16],  1));
  ctx.beginPath(); ctx.arc(CX, CY, cR, 0, Math.PI * 2);
  ctx.fillStyle = cg; ctx.fill();

  // — horizontal scan line —
  if (emo.scan) {
    const sy = CY + Math.sin(scanA * 1.6) * cR * .72;
    const sg = ctx.createLinearGradient(CX - cR, sy, CX + cR, sy);
    sg.addColorStop(0, rgb(emo.core, 0));
    sg.addColorStop(.5, rgb(emo.core, .18 * brt));
    sg.addColorStop(1, rgb(emo.core, 0));
    ctx.save(); ctx.beginPath(); ctx.arc(CX, CY, cR, 0, Math.PI * 2);
    ctx.clip(); ctx.fillStyle = sg; ctx.fillRect(CX - cR, sy - 1.5, cR * 2, 3);
    ctx.restore();
  }

  // — specular highlight —
  const hg = ctx.createRadialGradient(CX - cR*.28, CY - cR*.28, 0, CX - cR*.28, CY - cR*.28, cR*.52);
  hg.addColorStop(0, `rgba(255,255,255,${.28 * brt})`);
  hg.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.save(); ctx.beginPath(); ctx.arc(CX, CY, cR, 0, Math.PI * 2);
  ctx.clip(); ctx.beginPath(); ctx.arc(CX, CY, cR, 0, Math.PI * 2);
  ctx.fillStyle = hg; ctx.fill(); ctx.restore();

  // — reactive waveform ring —
  const wn = 80;
  ctx.beginPath();
  for (let i = 0; i <= wn; i++) {
    const a  = (i / wn) * Math.PI * 2;
    const w  = Math.sin(a * 6 + T * 4) * .042
             + Math.sin(a * 3 - T * 2.6) * .026
             + volume * .09;
    const pr = cR * (1 + w);
    const px = CX + Math.cos(a) * pr, py = CY + Math.sin(a) * pr;
    i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
  }
  ctx.closePath();
  ctx.strokeStyle = rgb(emo.ring, .52 * brt);
  ctx.lineWidth = 1.6; ctx.stroke();

  // — particles —
  ensureParts(emo.pts);
  for (const p of parts) { p.tick(); p.draw(emo.ring); }

  // — floor reflection —
  const rg = ctx.createRadialGradient(CX, CY + cR * .88, 0, CX, CY + cR * .88, cR * .55);
  rg.addColorStop(0, rgb(emo.glow, .14 * brt));
  rg.addColorStop(1, rgb(emo.glow, 0));
  ctx.beginPath(); ctx.arc(CX, CY + cR * .88, cR * .55, 0, Math.PI * 2);
  ctx.fillStyle = rg; ctx.fill();
}

frame();

// ─── PUBLIC API ──────────────────────────────────────────────────
function setEmotion(name) {
  if (!EMOTIONS[name] || name === curEmo && blendT >= 1) return;
  tgtEmo = name; blendT = 0;
  label.textContent = EMOTIONS[name].label;
}
function setVolume(v) { volume = Math.max(0, Math.min(1, +v || 0)); }

window.JarvisOrb = { setEmotion, setVolume };

// ─── WEBSOCKET ────────────────────────────────────────────────────
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/ws`);
  ws.onopen = () => {
    wsConnected = true;
    stopDemoCycle();
  };
  ws.onmessage = e => {
    try {
      const d = JSON.parse(e.data);
      if (d.type === 'state') {
        const backendStatus = String(d.status || 'idle').toLowerCase();
        const map = {
          idle: 'idle',
          listening: 'listening',
          thinking: 'thinking',
          speaking: 'speaking',
          executing: 'thinking',
          processing: 'thinking',
          loading: 'thinking',
          searching: 'thinking',
          browsing: 'thinking',
          alert: 'alert',
          warning: 'alert',
          error: 'alert',
          success: 'success',
          sleeping: 'idle',
        };
        setEmotion(map[backendStatus] || 'idle');
      } else if (d.type === 'volume') {
        setVolume(d.value);
      } else if (d.type === 'play_audio' && d.url) {
        playAudio(d.url);
      } else if (d.type === 'stop_audio') {
        stopAudio();
      }
    } catch(_) {}
  };
  ws.onclose = () => {
    wsConnected = false;
    startDemoCycle();
    setTimeout(connectWS, 3000);
  };
  ws.onerror = () => {
    wsConnected = false;
    startDemoCycle();
  };
}

// ─── AUDIO ENGINE ─────────────────────────────────────────────────
let aCtx=null, analyser_=null, dataBuf=null, aSrc=null;
function initAudio() {
  if (aCtx) return;
  try {
    aCtx = new (window.AudioContext || window.webkitAudioContext)();
    analyser_ = aCtx.createAnalyser(); analyser_.fftSize = 128;
    analyser_.smoothingTimeConstant = .85; analyser_.connect(aCtx.destination);
    dataBuf = new Uint8Array(analyser_.frequencyBinCount);
    setInterval(() => {
      if (!analyser_ || !aSrc) return;
      analyser_.getByteFrequencyData(dataBuf);
      let s = 0; for (const v of dataBuf) s += v;
      setVolume((s / dataBuf.length) / 255);
    }, 50);
  } catch(e) {}
}
async function playAudio(url) {
  initAudio();
  try {
    const r = await fetch(url); if (!r.ok) return;
    const dec = await aCtx.decodeAudioData(await r.arrayBuffer());
    stopAudio();
    aSrc = aCtx.createBufferSource(); aSrc.buffer = dec;
    aSrc.connect(analyser_);
    aSrc.onended = () => { aSrc = null; fetch('/api/audio_finished',{method:'POST'}).catch(()=>{}); };
    aSrc.start(0);
  } catch(e) {}
}
function stopAudio() { if(aSrc){try{aSrc.stop()}catch(_){}; aSrc=null;} }
document.addEventListener('click',  initAudio, {once:true});
document.addEventListener('keydown', initAudio, {once:true});

// ─── DEMO CYCLE (when no WS) ──────────────────────────────────────
const _CYCLE = ['idle','listening','thinking','speaking','success','alert'];
let _di = 0;
setTimeout(() => {
  if (!wsConnected) {
    startDemoCycle();
  }
}, 3500);

connectWS();
