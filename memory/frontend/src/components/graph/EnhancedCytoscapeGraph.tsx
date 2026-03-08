import { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import { Memory, RelationType } from '../../types/memory';
import { NodeDetailsPanel } from './NodeDetailsPanel';
import { GraphControls } from './GraphControls';
import { getRelatedMemories } from '../../api/memories';
import { X } from 'lucide-react';

interface EnhancedCytoscapeGraphProps {
  elements: any[];
  memories?: Memory[];
}

const MEMORY_TYPE_COLORS: Record<string, string> = {
  error: '#ef4444',
  decision: '#22c55e',
  pattern: '#3b82f6',
  docs: '#a855f7',
  learning: '#f59e0b',
  context: '#6b7280',
};

const TYPE_BADGE_CLASS: Record<string, string> = {
  error: 'bg-red-500/20 text-red-400',
  decision: 'bg-emerald-500/20 text-emerald-400',
  pattern: 'bg-blue-500/20 text-blue-400',
  docs: 'bg-violet-500/20 text-violet-400',
  learning: 'bg-amber-500/20 text-amber-400',
  context: 'bg-slate-500/20 text-slate-400',
};

const RELATION_STYLES: Record<string, any> = {
  [RelationType.FIXES]: { 'line-color': '#22c55e', 'target-arrow-color': '#22c55e', 'line-style': 'solid', 'width': 3 },
  [RelationType.CAUSES]: { 'line-color': '#ef4444', 'target-arrow-color': '#ef4444', 'line-style': 'dashed', 'width': 2.5 },
  [RelationType.SUPPORTS]: { 'line-color': '#60a5fa', 'target-arrow-color': '#60a5fa', 'line-style': 'solid', 'width': 2.5 },
  [RelationType.SUPERSEDES]: { 'line-color': '#3b82f6', 'target-arrow-color': '#3b82f6', 'line-style': 'solid', 'width': 2.5 },
  [RelationType.CONTRADICTS]: { 'line-color': '#f43f5e', 'target-arrow-color': '#f43f5e', 'line-style': 'dashed', 'width': 2 },
  [RelationType.FOLLOWS]: { 'line-color': '#06b6d4', 'target-arrow-color': '#06b6d4', 'line-style': 'solid', 'width': 2 },
  [RelationType.RELATED]: { 'line-color': '#6b7280', 'target-arrow-color': '#6b7280', 'line-style': 'dotted', 'width': 1.5 },
  [RelationType.SIMILAR_TO]: { 'line-color': '#f59e0b', 'target-arrow-color': '#f59e0b', 'line-style': 'dotted', 'width': 1 },
};

function getNodesWithinHops(cy: cytoscape.Core, startId: string, maxHops: number): Set<string> {
  const visited = new Set<string>();
  const queue: Array<[string, number]> = [[startId, 0]];
  visited.add(startId);

  while (queue.length > 0) {
    const [currentId, depth] = queue.shift()!;
    if (depth >= maxHops) continue;

    const node = cy.getElementById(currentId);
    if (!node || node.length === 0) continue;

    node.neighborhood('node').forEach((neighbor: any) => {
      const id = neighbor.id();
      if (!visited.has(id)) {
        visited.add(id);
        queue.push([id, depth + 1]);
      }
    });
  }

  return visited;
}

export function EnhancedCytoscapeGraph({ elements, memories }: EnhancedCytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const layoutRef = useRef<any>(null);
  const pulseTimerRef = useRef<number | null>(null);
  const selectedNodeRef = useRef<any>(null);

  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<any>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [isLayoutRunning, setIsLayoutRunning] = useState(false);
  const [depthFilter, setDepthFilter] = useState(0);
  const [isExpanding, setIsExpanding] = useState(false);

  // Keep ref in sync with state for use in cytoscape event handlers
  useEffect(() => {
    selectedNodeRef.current = selectedNode;
  }, [selectedNode]);

  const applyDepthFilter = useCallback((nodeId: string | null, depth: number) => {
    const cy = cyRef.current;
    if (!cy) return;

    if (!nodeId || depth === 0) {
      cy.elements().removeClass('depth-hidden');
      return;
    }

    const visibleIds = getNodesWithinHops(cy, nodeId, depth);

    cy.batch(() => {
      cy.nodes().forEach((node: any) => {
        if (visibleIds.has(node.id())) node.removeClass('depth-hidden');
        else node.addClass('depth-hidden');
      });
      cy.edges().forEach((edge: any) => {
        if (visibleIds.has(edge.source().id()) && visibleIds.has(edge.target().id()))
          edge.removeClass('depth-hidden');
        else edge.addClass('depth-hidden');
      });
    });
  }, []);

  const applySelectionDimming = useCallback((nodeId: string | null) => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.batch(() => {
      // Remove all direct style overrides so classes take precedence
      cy.elements().removeStyle();

      if (!nodeId) {
        cy.elements().removeClass('dimmed highlighted');
        return;
      }

      const selected = cy.getElementById(nodeId);
      if (!selected || selected.length === 0) return;

      const neighborhood = selected.closedNeighborhood();
      cy.elements().addClass('dimmed').removeClass('highlighted');
      neighborhood.removeClass('dimmed').addClass('highlighted');
    });
  }, []);

  const expandNeighborhood = useCallback(async (nodeId: string) => {
    const cy = cyRef.current;
    if (!cy || isExpanding) return;

    setIsExpanding(true);
    try {
      const related = await getRelatedMemories(nodeId, 2, 20);
      const newElements: any[] = [];
      const sourceNode = cy.getElementById(nodeId);
      const sourcePos = sourceNode.length ? sourceNode.position() : { x: 0, y: 0 };

      related.forEach((mem: Memory) => {
        if (!cy.getElementById(mem.id).length) {
          newElements.push({
            group: 'nodes' as const,
            data: {
              id: mem.id,
              label: (mem.content?.substring(0, 50) + '...') || mem.type,
              type: mem.type,
              project: mem.project,
            },
            position: {
              x: sourcePos.x + (Math.random() - 0.5) * 200,
              y: sourcePos.y + (Math.random() - 0.5) * 200,
            },
          });
        }

        const edgeId = `${nodeId}-${mem.id}`;
        const reverseEdgeId = `${mem.id}-${nodeId}`;
        if (!cy.getElementById(edgeId).length && !cy.getElementById(reverseEdgeId).length) {
          newElements.push({
            group: 'edges' as const,
            data: {
              id: edgeId,
              source: nodeId,
              target: mem.id,
              relation: 'related',
              type: 'RELATED',
              weight: 1.5,
            },
          });
        }
      });

      if (newElements.length > 0) {
        cy.add(newElements);

        // Update orphan status
        cy.nodes().forEach((n: any) => {
          if (n.degree() === 0) n.addClass('orphan');
          else n.removeClass('orphan');
        });

        // Local layout around the expanded node
        const expandedNeighborhood = cy.getElementById(nodeId).closedNeighborhood();
        expandedNeighborhood.layout({
          name: 'concentric',
          animate: true,
          animationDuration: 600,
          fit: false,
          concentric: (node: any) => node.id() === nodeId ? 2 : 1,
          levelWidth: () => 1,
          boundingBox: {
            x1: sourcePos.x - 250,
            y1: sourcePos.y - 250,
            x2: sourcePos.x + 250,
            y2: sourcePos.y + 250,
          },
        } as any).run();
      }
    } catch (err) {
      console.error('Failed to expand neighborhood:', err);
    } finally {
      setIsExpanding(false);
    }
  }, [isExpanding]);

  // Initialize Cytoscape
  useEffect(() => {
    if (!containerRef.current || !elements || elements.length === 0) return;

    // Cleanup previous instance
    if (pulseTimerRef.current) {
      clearInterval(pulseTimerRef.current);
      pulseTimerRef.current = null;
    }
    if (layoutRef.current) {
      try { layoutRef.current.stop(); } catch (_) {}
      layoutRef.current = null;
    }
    if (cyRef.current) {
      try {
        cyRef.current.stop();
        cyRef.current.unmount();
        cyRef.current.destroy();
      } catch (_) {}
      cyRef.current = null;
    }

    try {
      const cy = cytoscape({
        container: containerRef.current,
        elements: elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': (ele: any) => MEMORY_TYPE_COLORS[ele.data('type')] || '#4b5563',
              'label': 'data(label)',
              'color': '#d4d4d8',
              'text-outline-color': '#050508',
              'text-outline-width': 2,
              'font-size': '11px',
              'font-weight': '500',
              'text-valign': 'bottom',
              'text-halign': 'center',
              'text-margin-y': 8,
              'text-wrap': 'ellipsis',
              'text-max-width': '100px',
              'width': 32,
              'height': 32,
              'border-width': 2,
              'border-color': 'rgba(255, 255, 255, 0.08)',
              'border-opacity': 1,
              'opacity': 1,
              'transition-property': 'opacity, border-color, border-width, width, height',
              'transition-duration': '0.25s' as any,
            }
          },
          { selector: 'node[type="error"]', style: { 'shape': 'octagon' } },
          {
            selector: 'node:selected',
            style: {
              'border-width': 4,
              'border-color': '#06b6d4',
              'border-opacity': 1,
              'z-index': 9999,
              'overlay-opacity': 0,
              'width': 42,
              'height': 42,
            }
          },
          { selector: '.dimmed', style: { 'opacity': 0.12 } },
          { selector: '.highlighted', style: { 'opacity': 1 } },
          { selector: '.depth-hidden', style: { 'opacity': 0.04, 'events': 'no' as any } },
          {
            selector: '.orphan',
            style: {
              'border-width': 3,
              'border-color': '#f59e0b',
              'border-style': 'dashed' as any,
              'border-opacity': 1,
            }
          },
          { selector: '.orphan-dim', style: { 'border-opacity': 0.3 } },
          {
            selector: 'edge',
            style: {
              'width': (ele: any) => ele.data('weight') || 2,
              'line-color': '#4b5563',
              'target-arrow-color': '#4b5563',
              'target-arrow-shape': 'triangle',
              'target-arrow-fill': 'filled',
              'arrow-scale': 1,
              'curve-style': 'unbundled-bezier',
              'control-point-distances': [20],
              'control-point-weights': [0.5],
              'opacity': 0.6,
              'transition-property': 'opacity, line-color, width',
              'transition-duration': '0.25s' as any,
            }
          },
          ...Object.entries(RELATION_STYLES).map(([relType, style]) => ({
            selector: `edge[relation="${relType}"]`,
            style,
          })),
          {
            selector: 'edge:selected',
            style: {
              'width': 4,
              'line-color': '#06b6d4',
              'target-arrow-color': '#06b6d4',
              'opacity': 1,
              'z-index': 9999,
            }
          },
          { selector: 'edge.highlighted', style: { 'opacity': 1, 'z-index': 998 } },
        ],
        layout: {
          name: 'cose',
          animate: false,
          idealEdgeLength: 150,
          nodeOverlap: 30,
          refresh: 20,
          fit: true,
          padding: 80,
          randomize: false,
          componentSpacing: 120,
          nodeRepulsion: 8000,
          edgeElasticity: 200,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
        } as any,
        minZoom: 0.05,
        maxZoom: 5,
        wheelSensitivity: 0.2,
      });

      cyRef.current = cy;

      // Detect orphan nodes
      cy.nodes().forEach((node: any) => {
        if (node.degree() === 0) node.addClass('orphan');
      });

      // Orphan pulse animation
      let pulseState = true;
      pulseTimerRef.current = window.setInterval(() => {
        const orphans = cy.nodes('.orphan');
        if (orphans.length === 0) return;
        pulseState = !pulseState;
        if (pulseState) orphans.removeClass('orphan-dim');
        else orphans.addClass('orphan-dim');
      }, 1200);

      // Click: select node
      cy.on('tap', 'node', (evt: any) => {
        const node = evt.target;
        const nodeData = node.data();
        const memory = memories?.find(m => m.id === nodeData.id);

        setSelectedNode(nodeData);
        setSelectedNodeData(memory || nodeData);
        setShowDetails(true);
        applySelectionDimming(nodeData.id);
      });

      // Double-click: expand neighborhood
      cy.on('dbltap', 'node', (evt: any) => {
        expandNeighborhood(evt.target.id());
      });

      // Background click: clear selection
      cy.on('tap', (evt: any) => {
        if (evt.target === cy) {
          setSelectedNode(null);
          setSelectedNodeData(null);
          setShowDetails(false);
          setDepthFilter(0);
          applySelectionDimming(null);
          applyDepthFilter(null, 0);
        }
      });

      // Hover: dim non-neighbors (only when nothing is selected)
      cy.on('mouseover', 'node', (evt: any) => {
        if (selectedNodeRef.current) return;
        const node = evt.target;

        node.style({
          'width': 40,
          'height': 40,
          'border-width': 3,
          'border-color': node.style('background-color'),
          'z-index': 999,
        });
        node.connectedEdges().style({ 'opacity': 1, 'z-index': 998 });
        cy.nodes().not(node).not(node.neighborhood()).style({ 'opacity': 0.15 });
        cy.edges().not(node.connectedEdges()).style({ 'opacity': 0.08 });
      });

      cy.on('mouseout', 'node', () => {
        if (selectedNodeRef.current) return;
        cy.elements().removeStyle();
      });

    } catch (err) {
      console.error('Failed to initialize graph:', err);
    }

    return () => {
      if (pulseTimerRef.current) {
        clearInterval(pulseTimerRef.current);
        pulseTimerRef.current = null;
      }
      if (layoutRef.current) {
        try { layoutRef.current.stop(); } catch (_) {}
        layoutRef.current = null;
      }
      if (cyRef.current) {
        try {
          cyRef.current.stop();
          cyRef.current.unmount();
          cyRef.current.destroy();
        } catch (_) {}
        cyRef.current = null;
      }
    };
  }, [elements, memories]);

  // React to depth filter changes
  useEffect(() => {
    if (selectedNode) {
      applyDepthFilter(selectedNode.id, depthFilter);
    }
  }, [depthFilter, selectedNode, applyDepthFilter]);

  // --- Handlers passed to controls ---

  const handleZoom = useCallback((direction: 'in' | 'out' | 'fit') => {
    const cy = cyRef.current;
    if (!cy) return;

    if (direction === 'fit') {
      cy.fit(undefined, 80);
    } else {
      const zoom = cy.zoom();
      const level = direction === 'in' ? zoom * 1.3 : zoom / 1.3;
      cy.animate({
        zoom: { level, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } },
        duration: 200,
        easing: 'ease-out-cubic',
      } as any);
    }
  }, []);

  const handleFocusSelected = useCallback(() => {
    const cy = cyRef.current;
    if (!cy || !selectedNode) return;
    const node = cy.getElementById(selectedNode.id);
    if (node.length) {
      cy.animate({
        center: { eles: node },
        zoom: 2,
        duration: 400,
        easing: 'ease-out-cubic',
      } as any);
    }
  }, [selectedNode]);

  const handleClearSelection = useCallback(() => {
    const cy = cyRef.current;
    if (cy) {
      cy.elements().removeStyle();
      cy.elements().unselect();
      cy.elements().removeClass('dimmed highlighted depth-hidden');
    }
    setSelectedNode(null);
    setSelectedNodeData(null);
    setShowDetails(false);
    setDepthFilter(0);
  }, []);

  const handleToggleLayout = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;

    if (isLayoutRunning && layoutRef.current) {
      layoutRef.current.stop();
      layoutRef.current = null;
      setIsLayoutRunning(false);
    } else {
      const layout = cy.layout({
        name: 'cose',
        animate: true,
        animationDuration: 2000,
        fit: true,
        padding: 80,
        nodeRepulsion: 8000,
        edgeElasticity: 200,
        gravity: 80,
        numIter: 500,
      } as any);

      layoutRef.current = layout;
      setIsLayoutRunning(true);

      layout.on('layoutstop', () => {
        setIsLayoutRunning(false);
        layoutRef.current = null;
      });

      layout.run();
    }
  }, [isLayoutRunning]);

  const handleDepthChange = useCallback((depth: number) => {
    setDepthFilter(depth);
  }, []);

  return (
    <div className="relative w-full h-full">
      {/* Cytoscape container */}
      <div ref={containerRef} className="w-full h-full" style={{ background: 'transparent' }} />

      {/* Selection info bar — top center */}
      {selectedNode && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3
          bg-[#0c0c14]/95 backdrop-blur-xl rounded-full px-4 py-2 border border-white/[0.08]
          shadow-[0_4px_20px_rgba(0,0,0,0.4)]">
          <div className={`px-2 py-0.5 rounded-full text-[11px] font-medium ${TYPE_BADGE_CLASS[selectedNode.type] || 'bg-white/10 text-white/60'}`}>
            {selectedNode.type}
          </div>
          <span className="text-white/70 text-sm max-w-[300px] truncate">
            {selectedNode.label || selectedNode.id?.substring(0, 20)}
          </span>
          {selectedNode.project && (
            <span className="text-white/30 text-[11px]">{selectedNode.project}</span>
          )}
          <button
            onClick={handleClearSelection}
            className="ml-1 w-6 h-6 flex items-center justify-center rounded-full
              text-white/30 hover:text-white hover:bg-white/[0.1] transition-all"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Controls — bottom right */}
      <GraphControls
        onZoom={handleZoom}
        onFocusSelected={handleFocusSelected}
        onClearSelection={handleClearSelection}
        onToggleLayout={handleToggleLayout}
        isLayoutRunning={isLayoutRunning}
        hasSelection={!!selectedNode}
        depthFilter={depthFilter}
        onDepthChange={handleDepthChange}
      />

      {/* Expansion loading indicator */}
      {isExpanding && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20
          bg-[#0c0c14]/95 backdrop-blur-xl rounded-full px-4 py-2 border border-violet-500/20
          text-violet-400 text-sm flex items-center gap-2">
          <div className="w-3.5 h-3.5 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin" />
          Expanding neighborhood&hellip;
        </div>
      )}

      {/* Node details panel */}
      {showDetails && selectedNodeData && (
        <NodeDetailsPanel
          node={selectedNodeData}
          onClose={() => setShowDetails(false)}
          onExpandNeighborhood={() => selectedNode && expandNeighborhood(selectedNode.id)}
        />
      )}
    </div>
  );
}
