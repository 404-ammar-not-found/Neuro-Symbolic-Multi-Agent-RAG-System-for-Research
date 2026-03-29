import React, { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph3D from "react-force-graph-3d";
import * as THREE from "three";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";

function makeGlowSprite(color = "#7ee0ff") {
  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext("2d");

  const toRGBA = (c, alpha) => {
    const col = new THREE.Color(c);
    const r = Math.round(col.r * 255);
    const g = Math.round(col.g * 255);
    const b = Math.round(col.b * 255);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  };

  const gradient = ctx.createRadialGradient(
    size / 2,
    size / 2,
    0,
    size / 2,
    size / 2,
    size / 2
  );
  gradient.addColorStop(0, toRGBA(color, 1));
  gradient.addColorStop(0.4, toRGBA(color, 0.67));
  gradient.addColorStop(1, toRGBA(color, 0));
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const texture = new THREE.CanvasTexture(canvas);
  const material = new THREE.SpriteMaterial({
    map: texture,
    color,
    blending: THREE.AdditiveBlending,
    transparent: true,
    depthWrite: false,
  });
  const sprite = new THREE.Sprite(material);
  sprite.scale.set(14, 14, 1);
  return sprite;
}

function useNeighbors(data) {
  return useMemo(() => {
    const map = new Map();
    data.links.forEach((link) => {
      const { source, target } = link;
      if (!map.has(source)) map.set(source, new Set());
      if (!map.has(target)) map.set(target, new Set());
      map.get(source).add(target);
      map.get(target).add(source);
    });
    return map;
  }, [data]);
}

function GlobeGraph({ data, highlightNode, showEdges, onNodeHover, onNodeClick }) {
  const fgRef = useRef();
  const [composer, setComposer] = useState(null);
  const neighborMap = useNeighbors(data);

  const nodeThreeObject = (node) => {
    const color = node.color || node.groupColor || "#7ee0ff";
    return makeGlowSprite(color);
  };

  const nodeColor = (node) => {
    if (!highlightNode) return node.color || node.groupColor || "#7ee0ff";
    if (node.id === highlightNode) return "#ffffff";
    const neighbors = neighborMap.get(highlightNode) || new Set();
    return neighbors.has(node.id) ? "#b6f3ff" : "#2c3e50";
  };

  const linkColor = (link) => {
    const type = link.type || "sequence";
    const srcId = link.source.id || link.source;
    const tgtId = link.target.id || link.target;
    const baseColor =
      type === "similarity"
        ? "rgba(255, 180, 120, 0.35)"
        : "rgba(126, 224, 255, 0.2)";

    if (!highlightNode) return baseColor;
    const neighbors = neighborMap.get(highlightNode) || new Set();
    const isConnected =
      srcId === highlightNode ||
      tgtId === highlightNode ||
      neighbors.has(srcId) ||
      neighbors.has(tgtId);

    if (!isConnected) return "rgba(44,62,80,0.1)";
    return type === "similarity" ? "rgba(255, 210, 160, 0.65)" : "rgba(180, 235, 255, 0.6)";
  };

  const linkVisibility = () => showEdges;

  const linkWidth = (link) => {
    const sim = link.similarity || 0.5;
    if (link.type === "similarity") {
      return 0.5 + sim * 2;
    }
    return 1.2;
  };

  useEffect(() => {
    if (!fgRef.current) return;
    const scene = fgRef.current.scene();

    const stars = createStars(scene);
    scene.fog = new THREE.FogExp2("#02040b", 0.0015);
    const composerInstance = setupBloom(fgRef.current);
    setComposer(composerInstance);

    return () => {
      scene.remove(stars);
    };
  }, []);

  useEffect(() => {
    if (!fgRef.current) return;
    fgRef.current.zoomToFit(400, 100);
  }, [data]);

  const nodeLabel = (node) => `${node.label || node.id}\n${node.group || ""}`;

  return (
    <ForceGraph3D
      ref={fgRef}
      graphData={data}
      backgroundColor="#01030a"
      nodeThreeObject={nodeThreeObject}
      nodeThreeObjectExtend={true}
      nodeLabel={nodeLabel}
      nodeColor={nodeColor}
      linkColor={linkColor}
      linkOpacity={0.5}
      linkDirectionalParticles={2}
      linkDirectionalParticleWidth={0.5}
      linkWidth={linkWidth}
      linkVisibility={linkVisibility}
      enableNodeDrag={false}
      showNavInfo={false}
      onNodeHover={(node) => onNodeHover(node ? node.id : null)}
      onNodeClick={(node) => onNodeClick(node ? node.id : null)}
      extraRenderers={composer ? [composer] : []}
    />
  );
}

export default GlobeGraph;

function createStars(scene) {
  const starGeometry = new THREE.BufferGeometry();
  const starCount = 800;
  const positions = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    const radius = 600;
    positions[i * 3] = (Math.random() - 0.5) * radius;
    positions[i * 3 + 1] = (Math.random() - 0.5) * radius;
    positions[i * 3 + 2] = (Math.random() - 0.5) * radius;
  }
  starGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const starMaterial = new THREE.PointsMaterial({
    color: "#3a5f9b",
    size: 1.0,
    transparent: true,
    opacity: 0.5,
    depthWrite: false,
  });
  const stars = new THREE.Points(starGeometry, starMaterial);
  stars.name = "__stars";
  scene.add(stars);
  return stars;
}

function setupBloom(graphRef) {
  const renderer = graphRef.renderer();
  const { width, height } = renderer.getSize(new THREE.Vector2());
  const composerInstance = graphRef.postProcessingComposer();
  const renderScene = composerInstance.renderScene;
  const bloomPass = new UnrealBloomPass(
    new THREE.Vector2(width, height),
    1.35,
    0.85,
    0.08
  );
  composerInstance.addPass(bloomPass);
  composerInstance.renderScene = renderScene;
  return composerInstance;
}
