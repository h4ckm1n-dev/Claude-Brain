import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { getRelatedMemories } from '../../api/memories';
import { GraphControls } from './GraphControls';
import { NodeDetailsPanel } from './NodeDetailsPanel';
import { CommandPalette } from './CommandPalette';
import type { Memory } from '../../types/memory';

interface GraphNode {
  id: string;
  label: string;
  type: string;
  project?: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  type: string;
  relation: string;
  weight: number;
}

interface ForceGraphViewProps {
  graphData: { nodes: GraphNode[]; links: GraphLink[] };
  memories?: Memory[];
}

// --- Animation system ---
type AnimationType = 'pulse' | 'ripple' | 'glow';

interface NodeAnimation {
  type: AnimationType;
  startTime: number;
  duration: number;
}

const NODE_COLORS: Record<string, string> = {
  error: '#ef4444',
  decision: '#22c55e',
  pattern: '#3b82f6',
  docs: '#a855f7',
  learning: '#f59e0b',
  context: '#6b7280',
};

const LINK_COLORS: Record<string, string> = {
  FIXES: '#22c55e',
  CAUSES: '#ef4444',
  SUPPORTS: '#60a5fa',
  SUPERSEDES: '#3b82f6',
  CONTRADICTS: '#f43f5e',
  FOLLOWS: '#06b6d4',
  RELATED: '#6b7280',
  SIMILAR_TO: '#f59e0b',
};

function getNodeId(n: string | GraphNode): string {
  return typeof n === 'string' ? n : n.id;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}

// BFS: compute hops from a source node
function bfsHops(sourceId: string, links: GraphLink[]): Map<string, number> {
  const dist = new Map<string, number>();
  dist.set(sourceId, 0);
  const queue = [sourceId];
  while (queue.length > 0) {
    const curr = queue.shift()!;
    const currDist = dist.get(curr)!;
    for (const link of links) {
      const s = getNodeId(link.source);
      const t = getNodeId(link.target);
      let neighbor: string | null = null;
      if (s === curr && !dist.has(t)) neighbor = t;
      if (t === curr && !dist.has(s)) neighbor = s;
      if (neighbor) {
        dist.set(neighbor, currDist + 1);
        queue.push(neighbor);
      }
    }
  }
  return dist;
}

export function ForceGraphView({ graphData, memories }: ForceGraphViewProps) {
  const fgRef = useRef<any>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [isLayoutRunning, setIsLayoutRunning] = useState(true);
  const [depthFilter, setDepthFilter] = useState(0);
  const [detailNode, setDetailNode] = useState<any>(null);
  const lastClickTime = useRef(0);
  const lastClickNodeId = useRef<string | null>(null);

  // Animation state
  const animatedNodes = useRef<Map<string, NodeAnimation>>(new Map());
  const animFrameRef = useRef<number>(0);

  // Blast radius state
  const [blastNodeIds, setBlastNodeIds] = useState<Set<string>>(new Set());
  const blastStartTime = useRef(0);

  // Expanded nodes from double-click
  const [expandedNodes, setExpandedNodes] = useState<GraphNode[]>([]);
  const [expandedLinks, setExpandedLinks] = useState<GraphLink[]>([]);

  // Merge initial data with expanded data
  const mergedData = useMemo(() => {
    const nodeMap = new Map<string, GraphNode>();
    graphData.nodes.forEach(n => nodeMap.set(n.id, n));
    expandedNodes.forEach(n => { if (!nodeMap.has(n.id)) nodeMap.set(n.id, n); });

    const linkSet = new Set<string>();
    const allLinks: GraphLink[] = [];
    const addLink = (l: GraphLink) => {
      const key = `${getNodeId(l.source)}-${getNodeId(l.target)}-${l.type}`;
      if (!linkSet.has(key)) {
        linkSet.add(key);
        allLinks.push(l);
      }
    };
    graphData.links.forEach(addLink);
    expandedLinks.forEach(addLink);

    return { nodes: Array.from(nodeMap.values()), links: allLinks };
  }, [graphData, expandedNodes, expandedLinks]);

  // Orphan detection: nodes with 0 connections
  const orphanIds = useMemo(() => {
    const connected = new Set<string>();
    mergedData.links.forEach(l => {
      connected.add(getNodeId(l.source));
      connected.add(getNodeId(l.target));
    });
    return new Set(mergedData.nodes.filter(n => !connected.has(n.id)).map(n => n.id));
  }, [mergedData]);

  // Depth filtering: BFS from selected node
  const visibleNodeIds = useMemo(() => {
    if (!selectedNodeId || depthFilter === 0) return null;
    const hops = bfsHops(selectedNodeId, mergedData.links);
    const visible = new Set<string>();
    hops.forEach((d, id) => { if (d <= depthFilter) visible.add(id); });
    return visible;
  }, [selectedNodeId, depthFilter, mergedData.links]);

  // Neighbor set for dimming
  const neighborIds = useMemo(() => {
    if (!selectedNodeId) return null;
    const neighbors = new Set<string>();
    neighbors.add(selectedNodeId);
    mergedData.links.forEach(l => {
      const s = getNodeId(l.source);
      const t = getNodeId(l.target);
      if (s === selectedNodeId) neighbors.add(t);
      if (t === selectedNodeId) neighbors.add(s);
    });
    return neighbors;
  }, [selectedNodeId, mergedData.links]);

  // --- Animation loop ---
  useEffect(() => {
    let running = true;
    const tick = () => {
      if (!running) return;
      const now = Date.now();
      let needsRedraw = false;

      // Clean expired animations
      animatedNodes.current.forEach((anim, id) => {
        if (now - anim.startTime > anim.duration) {
          animatedNodes.current.delete(id);
        } else {
          needsRedraw = true;
        }
      });

      // Blast radius animations
      if (blastNodeIds.size > 0 && now - blastStartTime.current < 2000) {
        needsRedraw = true;
      } else if (blastNodeIds.size > 0 && now - blastStartTime.current >= 2000) {
        setBlastNodeIds(new Set());
      }

      // Orphan pulse always needs redraw
      if (orphanIds.size > 0) needsRedraw = true;

      if (needsRedraw) {
        fgRef.current?.d3ReheatSimulation?.();
      }

      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
    return () => { running = false; cancelAnimationFrame(animFrameRef.current); };
  }, [orphanIds, blastNodeIds]);

  // --- Trigger animations ---
  const triggerAnimation = useCallback((nodeId: string, type: AnimationType, duration = 1200) => {
    animatedNodes.current.set(nodeId, { type, startTime: Date.now(), duration });
  }, []);

  // Blast radius: BFS from node, animate all reached nodes
  const triggerBlastRadius = useCallback((nodeId: string) => {
    const hops = bfsHops(nodeId, mergedData.links);
    const affected = new Set<string>();
    hops.forEach((d, id) => { if (d > 0 && d <= 4) affected.add(id); });
    setBlastNodeIds(affected);
    blastStartTime.current = Date.now();
    // Also trigger ripple on each affected node with staggered timing
    affected.forEach(id => {
      const hop = hops.get(id) || 1;
      setTimeout(() => triggerAnimation(id, 'ripple', 1500), hop * 150);
    });
  }, [mergedData.links, triggerAnimation]);

  // ResizeObserver
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    ro.observe(el);
    setDimensions({ width: el.clientWidth, height: el.clientHeight });
    return () => ro.disconnect();
  }, []);

  // Configure forces after mount
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force('charge')?.strength(-120);
    fg.d3Force('link')?.distance((link: any) => {
      const w = link.weight || 1;
      return 80 + (4 - w) * 20;
    });
    fg.d3Force('center')?.strength(0.05);
  }, [mergedData]);

  // Initial zoom to fit
  useEffect(() => {
    const timeout = setTimeout(() => {
      fgRef.current?.zoomToFit(400, 60);
    }, 1500);
    return () => clearTimeout(timeout);
  }, []);

  // Reset expanded data when graphData changes
  useEffect(() => {
    setExpandedNodes([]);
    setExpandedLinks([]);
    setSelectedNodeId(null);
    setDetailNode(null);
    setBlastNodeIds(new Set());
  }, [graphData]);

  const handleNodeClick = useCallback((node: any) => {
    const now = Date.now();
    const isDoubleClick = lastClickNodeId.current === node.id && now - lastClickTime.current < 400;
    lastClickTime.current = now;
    lastClickNodeId.current = node.id;

    if (isDoubleClick) {
      expandNode(node.id);
    } else {
      setSelectedNodeId(prev => prev === node.id ? null : node.id);
      const mem = memories?.find(m => m.id === node.id);
      setDetailNode(mem || node);
      triggerAnimation(node.id, 'pulse', 800);
    }
  }, [memories, triggerAnimation]);

  const expandNode = useCallback(async (nodeId: string) => {
    try {
      const related = await getRelatedMemories(nodeId, 2, 20);
      const newNodes: GraphNode[] = [];
      const newLinks: GraphLink[] = [];

      related.forEach((mem: Memory) => {
        newNodes.push({
          id: mem.id,
          label: mem.content?.substring(0, 50) + '...' || mem.type,
          type: mem.type,
          project: mem.project,
        });
        newLinks.push({
          source: nodeId,
          target: mem.id,
          type: 'RELATED',
          relation: 'related',
          weight: 1.5,
        });
      });

      setExpandedNodes(prev => [...prev, ...newNodes]);
      setExpandedLinks(prev => [...prev, ...newLinks]);

      // Animate new nodes
      newNodes.forEach(n => triggerAnimation(n.id, 'glow', 1500));

      setTimeout(() => fgRef.current?.d3ReheatSimulation(), 100);
    } catch {
      // silently fail
    }
  }, [triggerAnimation]);

  // --- Dynamic node sizing by degree ---
  const nodeDegrees = useMemo(() => {
    const degrees = new Map<string, number>();
    mergedData.links.forEach(l => {
      const s = getNodeId(l.source);
      const t = getNodeId(l.target);
      degrees.set(s, (degrees.get(s) || 0) + 1);
      degrees.set(t, (degrees.get(t) || 0) + 1);
    });
    return degrees;
  }, [mergedData.links]);

  const maxDegree = useMemo(() => {
    let max = 1;
    nodeDegrees.forEach(d => { if (d > max) max = d; });
    return max;
  }, [nodeDegrees]);

  // Custom node renderer with animations, tooltip, blast radius
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const nodeId = node.id as string;
    const color = NODE_COLORS[node.type] || '#6b7280';
    const [cr, cg, cb] = hexToRgb(color);

    // Dynamic sizing: base 4, scale up by degree
    const degree = nodeDegrees.get(nodeId) || 0;
    const sizeScale = 1 + (degree / maxDegree) * 0.8;
    const baseR = 4.5 * sizeScale;

    const isSelected = selectedNodeId === nodeId;
    const isHovered = hoveredNodeId === nodeId;
    const isNeighbor = neighborIds ? neighborIds.has(nodeId) : true;
    const isVisible = visibleNodeIds ? visibleNodeIds.has(nodeId) : true;
    const isOrphan = orphanIds.has(nodeId);
    const isBlast = blastNodeIds.has(nodeId);
    const anim = animatedNodes.current.get(nodeId);

    if (!isVisible) return;

    const dimmed = selectedNodeId && !isNeighbor;
    const alpha = dimmed ? 0.12 : 1;

    ctx.save();
    ctx.globalAlpha = alpha;

    const now = Date.now();

    // --- Blast radius: red expanding ring ---
    if (isBlast && !dimmed) {
      const elapsed = now - blastStartTime.current;
      const progress = Math.min(elapsed / 2000, 1);
      const ringAlpha = 1 - progress;
      const ringR = baseR + progress * 20;
      ctx.strokeStyle = `rgba(239, 68, 68, ${ringAlpha * 0.6})`;
      ctx.lineWidth = 2 / globalScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, ringR, 0, 2 * Math.PI);
      ctx.stroke();
      // Inner glow
      const glow = ctx.createRadialGradient(node.x, node.y, baseR, node.x, node.y, ringR * 0.6);
      glow.addColorStop(0, `rgba(239, 68, 68, ${ringAlpha * 0.15})`);
      glow.addColorStop(1, 'rgba(239, 68, 68, 0)');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(node.x, node.y, ringR * 0.6, 0, 2 * Math.PI);
      ctx.fill();
    }

    // --- Animation effects ---
    let animR = baseR;
    if (anim && !dimmed) {
      const progress = (now - anim.startTime) / anim.duration;
      if (progress < 1) {
        const wave = Math.sin(progress * Math.PI * 4);
        if (anim.type === 'pulse') {
          animR = baseR * (1 + wave * 0.25);
        } else if (anim.type === 'ripple') {
          const rippleR = baseR + progress * 18;
          const rippleAlpha = (1 - progress) * 0.5;
          ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, ${rippleAlpha})`;
          ctx.lineWidth = 1.5 / globalScale;
          ctx.beginPath();
          ctx.arc(node.x, node.y, rippleR, 0, 2 * Math.PI);
          ctx.stroke();
          // Second ring offset
          if (progress > 0.2) {
            const p2 = progress - 0.2;
            const r2 = baseR + p2 * 18;
            ctx.globalAlpha = alpha * (1 - p2) * 0.3;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r2, 0, 2 * Math.PI);
            ctx.stroke();
            ctx.globalAlpha = alpha;
          }
        } else if (anim.type === 'glow') {
          const glowR = baseR * (2.5 + wave * 0.5);
          const glowAlpha = (1 - progress) * 0.3;
          const gradient = ctx.createRadialGradient(node.x, node.y, baseR * 0.5, node.x, node.y, glowR);
          gradient.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, ${glowAlpha})`);
          gradient.addColorStop(1, `rgba(${cr}, ${cg}, ${cb}, 0)`);
          ctx.fillStyle = gradient;
          ctx.beginPath();
          ctx.arc(node.x, node.y, glowR, 0, 2 * Math.PI);
          ctx.fill();
        }
      }
    }

    // Glow halo for selected/hovered
    if ((isSelected || isHovered) && !dimmed) {
      const gradient = ctx.createRadialGradient(node.x, node.y, animR * 0.5, node.x, node.y, animR * 3.5);
      gradient.addColorStop(0, `rgba(${cr}, ${cg}, ${cb}, 0.35)`);
      gradient.addColorStop(1, `rgba(${cr}, ${cg}, ${cb}, 0)`);
      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(node.x, node.y, animR * 3.5, 0, 2 * Math.PI);
      ctx.fill();
    }

    // Orphan pulsing ring
    if (isOrphan && !dimmed) {
      const pulse = 0.5 + 0.5 * Math.sin(now / 600);
      ctx.strokeStyle = `rgba(245, 158, 11, ${0.3 + pulse * 0.4})`;
      ctx.lineWidth = 1.5 / globalScale;
      ctx.setLineDash([3 / globalScale, 3 / globalScale]);
      ctx.beginPath();
      ctx.arc(node.x, node.y, animR + 3, 0, 2 * Math.PI);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Node body
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(node.x, node.y, animR, 0, 2 * Math.PI);
    ctx.fill();

    // Bright ring on selected
    if (isSelected) {
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5 / globalScale;
      ctx.beginPath();
      ctx.arc(node.x, node.y, animR + 1.5, 0, 2 * Math.PI);
      ctx.stroke();
    }

    // --- Dark Pill Hover Tooltip ---
    if (isHovered && !dimmed && globalScale > 0.4) {
      const label = node.label || node.type;
      const truncated = label.length > 40 ? label.substring(0, 38) + '..' : label;
      const typeName = (node.type || 'node').toUpperCase();
      const fontSize = Math.max(11 / globalScale, 3);
      const typeSize = fontSize * 0.8;
      const padding = 8 / globalScale;
      const gap = 4 / globalScale;

      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const labelWidth = ctx.measureText(truncated).width;
      ctx.font = `bold ${typeSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      const typeWidth = ctx.measureText(typeName).width;

      const dotSize = 3 / globalScale;
      const totalWidth = dotSize + gap + typeWidth + gap * 2 + labelWidth + padding * 2;
      const height = fontSize + padding * 2;
      const radius = height / 2;
      const tooltipX = node.x - totalWidth / 2;
      const tooltipY = node.y - animR - height - 6 / globalScale;

      // Pill background
      ctx.fillStyle = 'rgba(12, 12, 20, 0.92)';
      ctx.beginPath();
      ctx.roundRect(tooltipX, tooltipY, totalWidth, height, radius);
      ctx.fill();

      // Colored border
      ctx.strokeStyle = `rgba(${cr}, ${cg}, ${cb}, 0.5)`;
      ctx.lineWidth = 1 / globalScale;
      ctx.beginPath();
      ctx.roundRect(tooltipX, tooltipY, totalWidth, height, radius);
      ctx.stroke();

      // Colored dot
      const cx = tooltipX + padding + dotSize / 2;
      const cy = tooltipY + height / 2;
      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(cx, cy, dotSize, 0, 2 * Math.PI);
      ctx.fill();

      // Type label
      ctx.font = `bold ${typeSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.fillStyle = `rgba(${cr}, ${cg}, ${cb}, 0.8)`;
      ctx.textAlign = 'left';
      ctx.textBaseline = 'middle';
      ctx.fillText(typeName, cx + dotSize + gap, cy);

      // Separator
      const sepX = cx + dotSize + gap + typeWidth + gap;
      ctx.strokeStyle = 'rgba(255,255,255,0.1)';
      ctx.lineWidth = 0.5 / globalScale;
      ctx.beginPath();
      ctx.moveTo(sepX, tooltipY + padding * 0.6);
      ctx.lineTo(sepX, tooltipY + height - padding * 0.6);
      ctx.stroke();

      // Content label
      ctx.font = `${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`;
      ctx.fillStyle = 'rgba(255,255,255,0.85)';
      ctx.fillText(truncated, sepX + gap, cy);
    }
    // Regular label (when not hovered)
    else if (globalScale > 0.8 && !dimmed && !isHovered) {
      const label = node.label || node.type;
      const truncated = label.length > 24 ? label.substring(0, 22) + '..' : label;
      const fontSize = Math.max(10 / globalScale, 2.5);
      ctx.font = `${fontSize}px sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = 'rgba(255,255,255,0.7)';
      ctx.fillText(truncated, node.x, node.y + animR + 3);
    }

    ctx.restore();
  }, [selectedNodeId, hoveredNodeId, neighborIds, visibleNodeIds, orphanIds, blastNodeIds, nodeDegrees, maxDegree]);

  // Node visibility for depth filtering
  const nodeVisibility = useCallback((node: any) => {
    if (!visibleNodeIds) return true;
    return visibleNodeIds.has(node.id);
  }, [visibleNodeIds]);

  // Link visibility
  const linkVisibility = useCallback((link: any) => {
    if (!visibleNodeIds) return true;
    return visibleNodeIds.has(getNodeId(link.source)) && visibleNodeIds.has(getNodeId(link.target));
  }, [visibleNodeIds]);

  // Link color with dimming
  const linkColor = useCallback((link: any) => {
    const color = LINK_COLORS[link.type] || '#6b7280';
    if (!selectedNodeId) return color + '60';
    const s = getNodeId(link.source);
    const t = getNodeId(link.target);
    if (neighborIds?.has(s) && neighborIds?.has(t)) return color + 'cc';
    return color + '15';
  }, [selectedNodeId, neighborIds]);

  // Link particles
  const linkParticles = useCallback((link: any) => {
    if (!selectedNodeId) return 1;
    const s = getNodeId(link.source);
    const t = getNodeId(link.target);
    if (s === selectedNodeId || t === selectedNodeId) return 3;
    return 0;
  }, [selectedNodeId]);

  const linkParticleColor = useCallback((link: any) => {
    return LINK_COLORS[link.type] || '#6b7280';
  }, []);

  // Controls
  const handleZoom = useCallback((dir: 'in' | 'out' | 'fit') => {
    const fg = fgRef.current;
    if (!fg) return;
    if (dir === 'fit') { fg.zoomToFit(400, 60); return; }
    const currentZoom = fg.zoom();
    fg.zoom(dir === 'in' ? currentZoom * 1.5 : currentZoom / 1.5, 400);
  }, []);

  const handleFocusSelected = useCallback(() => {
    if (!selectedNodeId) return;
    const node = mergedData.nodes.find(n => n.id === selectedNodeId);
    if (node?.x != null && node?.y != null) {
      fgRef.current?.centerAt(node.x, node.y, 400);
      fgRef.current?.zoom(3, 400);
    }
  }, [selectedNodeId, mergedData.nodes]);

  const handleClearSelection = useCallback(() => {
    setSelectedNodeId(null);
    setDetailNode(null);
    setDepthFilter(0);
    setBlastNodeIds(new Set());
  }, []);

  const handleToggleLayout = useCallback(() => {
    const fg = fgRef.current;
    if (!fg) return;
    if (isLayoutRunning) {
      fg.pauseAnimation();
    } else {
      fg.resumeAnimation();
      fg.d3ReheatSimulation();
    }
    setIsLayoutRunning(prev => !prev);
  }, [isLayoutRunning]);

  const handleExpandFromPanel = useCallback(() => {
    if (detailNode?.id) expandNode(detailNode.id);
  }, [detailNode, expandNode]);

  const handleBlastFromPanel = useCallback(() => {
    if (detailNode?.id) triggerBlastRadius(detailNode.id);
  }, [detailNode, triggerBlastRadius]);

  // Command palette handlers
  const handlePaletteSelect = useCallback((nodeId: string) => {
    setSelectedNodeId(nodeId);
    const mem = memories?.find(m => m.id === nodeId);
    const node = mergedData.nodes.find(n => n.id === nodeId);
    setDetailNode(mem || node || { id: nodeId });
    triggerAnimation(nodeId, 'pulse', 1000);
  }, [memories, mergedData.nodes, triggerAnimation]);

  const handlePaletteFocus = useCallback((nodeId: string) => {
    const node = mergedData.nodes.find(n => n.id === nodeId);
    if (node?.x != null && node?.y != null) {
      fgRef.current?.centerAt(node.x, node.y, 400);
      fgRef.current?.zoom(3, 400);
    }
  }, [mergedData.nodes]);

  return (
    <div ref={containerRef} className="absolute inset-0">
      <ForceGraph2D
        ref={fgRef}
        width={dimensions.width}
        height={dimensions.height}
        graphData={mergedData}
        nodeCanvasObject={paintNode}
        nodePointerAreaPaint={(node: any, color: string, ctx: CanvasRenderingContext2D) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
          ctx.fill();
        }}
        nodeVisibility={nodeVisibility}
        linkVisibility={linkVisibility}
        linkColor={linkColor}
        linkWidth={(link: any) => Math.max(0.5, (link.weight || 1) * 0.6)}
        linkCurvature={0.15}
        linkDirectionalParticles={linkParticles}
        linkDirectionalParticleWidth={2.5}
        linkDirectionalParticleSpeed={0.005}
        linkDirectionalParticleColor={linkParticleColor}
        onNodeClick={handleNodeClick}
        onNodeHover={(node: any) => setHoveredNodeId(node?.id || null)}
        onBackgroundClick={() => {
          setSelectedNodeId(null);
          setDetailNode(null);
          setBlastNodeIds(new Set());
        }}
        backgroundColor="rgba(0,0,0,0)"
        cooldownTicks={200}
        onEngineStop={() => setIsLayoutRunning(false)}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        enableNodeDrag={true}
      />

      {/* Selection info bar */}
      {selectedNodeId && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3
          bg-[#0c0c14]/90 backdrop-blur-xl border border-white/[0.08] rounded-xl px-4 py-2
          shadow-[0_4px_24px_rgba(0,0,0,0.4)]">
          <div
            className="w-2.5 h-2.5 rounded-full"
            style={{ backgroundColor: NODE_COLORS[detailNode?.type] || '#6b7280' }}
          />
          <span className="text-[11px] text-white/50 uppercase tracking-wider font-medium">
            {detailNode?.type || 'node'}
          </span>
          <span className="text-xs text-white/80 max-w-[300px] truncate">
            {detailNode?.label || detailNode?.content?.substring(0, 50) || selectedNodeId.substring(0, 12) + '...'}
          </span>
          {/* Blast radius button */}
          <button
            onClick={handleBlastFromPanel}
            className="ml-1 px-2 py-0.5 text-[10px] rounded-md bg-red-500/10 text-red-400/80
              border border-red-500/20 hover:bg-red-500/20 hover:text-red-400 transition-all"
            title="Show blast radius"
          >
            blast
          </button>
          <button
            onClick={handleClearSelection}
            className="ml-1 text-white/30 hover:text-white/70 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Cmd+K hint */}
      {!selectedNodeId && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2
          bg-[#0c0c14]/60 backdrop-blur-sm border border-white/[0.04] rounded-lg px-3 py-1.5
          opacity-40 hover:opacity-80 transition-opacity cursor-pointer"
          onClick={() => {
            window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true }));
          }}
        >
          <kbd className="px-1.5 py-0.5 text-[10px] text-white/30 bg-white/[0.06] rounded border border-white/[0.08] font-mono">
            {navigator.platform.includes('Mac') ? '\u2318' : 'Ctrl'}+K
          </kbd>
          <span className="text-[11px] text-white/25">Search nodes</span>
        </div>
      )}

      <GraphControls
        onZoom={handleZoom}
        onFocusSelected={handleFocusSelected}
        onClearSelection={handleClearSelection}
        onToggleLayout={handleToggleLayout}
        isLayoutRunning={isLayoutRunning}
        hasSelection={!!selectedNodeId}
        depthFilter={depthFilter}
        onDepthChange={setDepthFilter}
      />

      {detailNode && (
        <NodeDetailsPanel
          node={detailNode}
          onClose={() => { setDetailNode(null); setSelectedNodeId(null); setBlastNodeIds(new Set()); }}
          onExpandNeighborhood={handleExpandFromPanel}
        />
      )}

      <CommandPalette
        nodes={mergedData.nodes}
        onSelectNode={handlePaletteSelect}
        onFocusNode={handlePaletteFocus}
      />
    </div>
  );
}
