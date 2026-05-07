import os

with open('temp_voiceorb/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

new_html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>Assistente IA</title>
    <style>
        body { margin: 0; padding: 0; background-color: #06060f; overflow: hidden; font-family: 'Segoe UI', system-ui, sans-serif; color: #e0e8ff; }
        canvas { display: block; }
        #subtitle-panel { position: fixed; bottom: 0; left: 0; right: 0; padding: 40px; background: linear-gradient(to top, rgba(6,6,15,0.95), transparent); text-align: center; pointer-events: none; }
        #subtitle-text { font-size: 26px; text-shadow: 0 0 15px rgba(100,160,255,0.6); max-width: 900px; margin: 0 auto; line-height: 1.5; }
        #title { position: fixed; top: 20px; left: 20px; font-weight: bold; letter-spacing: 2px; color: rgba(255,255,255,0.4); }
    </style>
</head>
<body>
    <div id="title">ASSISTENTE IA</div>
    <canvas id="canvas"></canvas>
    <div id="subtitle-panel"><div id="subtitle-text"></div></div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script>
"""

vertex_start = js.find('const vertexShader = `')
vertex_end = js.find('`;', vertex_start) + 2

frag_start = js.find('const fragmentShader = `')
frag_end = js.find('`;', frag_start) + 2

states_start = js.find('const states = {')
states_end = js.find('};\n', states_start) + 2

js_core = js[states_start:states_end] + "\n" + js[vertex_start:vertex_end] + "\n" + js[frag_start:frag_end]

rest_of_js = """
let scene, camera, renderer, orbLayers = [];
let currentState = 'idle';
let currentScale = 1.0, targetScale = 1.0;
let simIntensity = 0;
let lastSub = '';

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;
    
    renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas'), antialias: true, alpha: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    
    const initialState = states.idle;
    initialState.layers.forEach((layerConfig, index) => {
        const geometry = new THREE.SphereGeometry(layerConfig.scale, 80, 80);
        const material = new THREE.ShaderMaterial({
            vertexShader, fragmentShader,
            uniforms: {
                time: { value: 0 }, audioLevel: { value: 0 }, layerOffset: { value: index * 2.0 },
                sphereColor: { value: new THREE.Color(layerConfig.color) }, opacity: { value: layerConfig.opacity },
                chromaticAberration: { value: initialState.chromaticAberration || 0.1 }, cameraPosition: { value: camera.position }
            },
            transparent: true, side: THREE.DoubleSide, blending: THREE.NormalBlending, depthWrite: false
        });
        const sphere = new THREE.Mesh(geometry, material);
        sphere.userData = { baseScale: layerConfig.scale, rotationSpeed: layerConfig.rotationSpeed };
        scene.add(sphere);
        orbLayers.push(sphere);
    });
    
    scene.add(new THREE.AmbientLight(0xffffff, 0.4));
    const pl1 = new THREE.PointLight(0x667eea, 0.6, 100); pl1.position.set(5, 5, 5); scene.add(pl1);
    const pl2 = new THREE.PointLight(0x764ba2, 0.4, 100); pl2.position.set(-5, -5, 5); scene.add(pl2);
    
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight; camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
    
    animate();
    setInterval(pollState, 150);
}

async function pollState() {
    try {
        const res = await fetch('/api/state');
        if (res.ok) {
            const data = await res.json();
            if(data.status && states[data.status]) currentState = data.status;
            if(data.subtitle !== lastSub) {
                lastSub = data.subtitle;
                document.getElementById('subtitle-text').textContent = data.subtitle;
            }
        }
    } catch(e) {}
}

function updateSimulatedAudio() {
    const state = states[currentState];
    const now = Date.now() * 0.001;
    if(currentState === 'speaking') {
        simIntensity = 0.5 + Math.sin(now * 12.0) * 0.3 + Math.sin(now * 3.0) * 0.2;
    } else if(currentState === 'thinking') {
        simIntensity = 0.2 + Math.sin(now * 2.0) * 0.1;
    } else {
        simIntensity = 0.05 + Math.sin(now) * 0.02;
    }
    return Math.max(0, simIntensity);
}

function animate() {
    requestAnimationFrame(animate);
    const state = states[currentState];
    const audioLevel = updateSimulatedAudio();
    
    if (state.pulsate) {
        targetScale = 1.0 + state.pulsateMin + (audioLevel * (state.pulsateMax - state.pulsateMin));
        currentScale += (targetScale - currentScale) * 0.15;
    } else {
        currentScale += (1.0 - currentScale) * 0.1;
    }
    
    orbLayers.forEach((layer, index) => {
        const config = state.layers[index];
        if (config) {
            layer.material.uniforms.sphereColor.value.lerp(new THREE.Color(config.color), 0.05);
            layer.material.uniforms.opacity.value += (config.opacity - layer.material.uniforms.opacity.value) * 0.05;
            layer.material.uniforms.time.value += state.timeSpeed;
            layer.material.uniforms.audioLevel.value = audioLevel;
            layer.material.uniforms.chromaticAberration.value += ((state.chromaticAberration || 0.1) - layer.material.uniforms.chromaticAberration.value) * 0.05;
            
            layer.rotation.x += config.rotationSpeed.x;
            layer.rotation.y += config.rotationSpeed.y;
            layer.rotation.z += config.rotationSpeed.z;
            
            const sc = layer.userData.baseScale * currentScale;
            layer.scale.set(sc, sc, sc);
        }
    });
    renderer.render(scene, camera);
}

window.onload = init;
"""

new_html += js_core + rest_of_js + "</script></body></html>"

os.makedirs('src/static', exist_ok=True)
with open('src/static/visualizer.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

print("HTML generated successfully!")
