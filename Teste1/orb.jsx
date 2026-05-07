import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

const VanillaOrb = ({ isListening = false }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    
    const container = containerRef.current;
    const { clientWidth, clientHeight } = container;
    renderer.setSize(clientWidth, clientHeight);
    container.appendChild(renderer.domElement);

    // Geometry
    const geometry = new THREE.IcosahedronGeometry(1, 15);
    const material = new THREE.MeshPhongMaterial({
      color: 0x00ff88,
      wireframe: true,
      transparent: true,
      opacity: 0.8,
    });
    const sphere = new THREE.Mesh(geometry, material);
    scene.add(sphere);

    // Lighting
    const light = new THREE.PointLight(0xffffff, 1, 100);
    light.position.set(5, 5, 5);
    scene.add(light);
    scene.add(new THREE.AmbientLight(0x404040));

    camera.position.z = 3;

    let animationId;
    const animate = () => {
      animationId = requestAnimationFrame(animate);
      
      sphere.rotation.x += 0.005;
      sphere.rotation.y += 0.01;
      
      const time = Date.now() * 0.001;
      const scale = isListening ? 1.2 + Math.sin(time * 10) * 0.1 : 1;
      sphere.scale.set(scale, scale, scale);
      
      renderer.render(scene, camera);
    };

    animate();

    const handleResize = () => {
      const { clientWidth, clientHeight } = container;
      camera.aspect = clientWidth / clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(clientWidth, clientHeight);
    };

    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationId);
      window.removeEventListener('resize', handleResize);
      container.removeChild(renderer.domElement);
      geometry.dispose();
      material.dispose();
    };
  }, [isListening]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
};

export default VanillaOrb;
