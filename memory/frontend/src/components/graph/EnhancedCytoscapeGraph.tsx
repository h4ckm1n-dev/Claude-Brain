import { useEffect, useRef, useState, useCallback } from 'react';
import cytoscape from 'cytoscape';
import { Memory, RelationType } from '../../types/memory';
import { NodeDetailsPanel } from './NodeDetailsPanel';
import { GraphControls } from './GraphControls';

interface EnhancedCytoscapeGraphProps {
  elements: any[];
  memories?: Memory[];
}

const MEMORY_TYPE_COLORS = {
  error: '#ef4444',
  decision: '#22c55e',
  pattern: '#3b82f6',
  docs: '#a855f7',
  learning: '#f59e0b',
  context: '#6b7280',
};

const RELATION_STYLES: Record<string, any> = {
  [RelationType.FIXES]: {
    'line-color': '#22c55e',
    'target-arrow-color': '#22c55e',
    'line-style': 'solid',
    'width': 3,
  },
  [RelationType.CAUSES]: {
    'line-color': '#ef4444',
    'target-arrow-color': '#ef4444',
    'line-style': 'dashed',
    'width': 2,
  },
  [RelationType.RELATED]: {
    'line-color': '#6b7280',
    'target-arrow-color': '#6b7280',
    'line-style': 'dotted',
    'width': 2,
  },
  [RelationType.SUPERSEDES]: {
    'line-color': '#3b82f6',
    'target-arrow-color': '#3b82f6',
    'line-style': 'solid',
    'width': 4,
  },
};

export function EnhancedCytoscapeGraph({ elements, memories }: EnhancedCytoscapeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const minimapRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<any>(null);
  const minimapCyRef = useRef<any>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [layout, setLayout] = useState<string>('cose');
  const [showMinimap, setShowMinimap] = useState(true);

  useEffect(() => {
    if (!containerRef.current || !elements || elements.length === 0) return;

    if (cyRef.current) {
      cyRef.current.destroy();
    }

    try {
      const cy = cytoscape({
        container: containerRef.current,
        elements: elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': (ele: any) => {
                const type = ele.data('type');
                return MEMORY_TYPE_COLORS[type as keyof typeof MEMORY_TYPE_COLORS] || '#0088FE';
              },
              'label': 'data(label)',
              'color': '#1f2937',
              'text-outline-color': '#fff',
              'text-outline-width': 3,
              'font-size': (ele: any) => {
                const importance = ele.data('importance') || 0.5;
                return Math.max(12, 10 + importance * 10);
              },
              'font-weight': '600',
              'text-valign': 'center',
              'text-halign': 'center',
              'text-wrap': 'wrap',
              'text-max-width': '120px',
              'width': (ele: any) => {
                const importance = ele.data('importance') || 0.5;
                return Math.max(35, 25 + importance * 50);
              },
              'height': (ele: any) => {
                const importance = ele.data('importance') || 0.5;
                return Math.max(35, 25 + importance * 50);
              },
              'opacity': (ele: any) => {
                const recency = ele.data('recency') || 0.5;
                return Math.max(0.5, 0.4 + recency * 0.6);
              },
              'border-width': (ele: any) => {
                return ele.data('pinned') ? 5 : 2;
              },
              'border-color': (ele: any) => {
                return ele.data('pinned') ? '#f59e0b' : 'rgba(0, 0, 0, 0.2)';
              },
              'border-opacity': 0.8,
              'shadow-blur': 8,
              'shadow-color': 'rgba(0, 0, 0, 0.3)',
              'shadow-offset-x': 2,
              'shadow-offset-y': 2,
              'transition-property': 'background-color, border-width, border-color, width, height, shadow-blur',
              'transition-duration': '0.3s',
              'transition-timing-function': 'ease-in-out',
            }
          },
          {
            selector: 'node[type="error"]',
            style: {
              'shape': 'octagon',
            }
          },
          {
            selector: 'node[?resolved]',
            style: {
              'border-width': 2,
              'border-color': '#22c55e',
            }
          },
          {
            selector: 'node[!resolved]',
            style: {
              'border-width': 3,
              'border-style': 'double',
              'border-color': '#ef4444',
            }
          },
          {
            selector: 'node:selected',
            style: {
              'border-width': 6,
              'border-color': '#3b82f6',
              'border-opacity': 1,
              'shadow-blur': 20,
              'shadow-color': '#3b82f6',
              'shadow-opacity': 0.6,
              'z-index': 9999,
              'overlay-opacity': 0,
            }
          },
          {
            selector: 'node:active',
            style: {
              'overlay-opacity': 0.2,
              'overlay-color': '#3b82f6',
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 2.5,
              'line-color': '#9ca3af',
              'target-arrow-color': '#9ca3af',
              'target-arrow-shape': 'triangle',
              'target-arrow-fill': 'filled',
              'arrow-scale': 1.2,
              'curve-style': 'bezier',
              'label': 'data(type)',
              'font-size': '10px',
              'font-weight': '600',
              'text-rotation': 'autorotate',
              'text-margin-y': -12,
              'text-background-color': '#fff',
              'text-background-opacity': 0.8,
              'text-background-padding': '3px',
              'text-background-shape': 'roundrectangle',
              'color': '#4b5563',
              'opacity': 0.75,
              'transition-property': 'line-color, target-arrow-color, width, opacity',
              'transition-duration': '0.3s',
              'transition-timing-function': 'ease-in-out',
            }
          },
          ...Object.entries(RELATION_STYLES).map(([relType, style]) => ({
            selector: `edge[relation="${relType}"]`,
            style,
          })),
          {
            selector: 'edge:selected',
            style: {
              'width': 5,
              'line-color': '#3b82f6',
              'target-arrow-color': '#3b82f6',
              'opacity': 1,
              'z-index': 9999,
              'overlay-opacity': 0,
            }
          },
          {
            selector: 'edge:active',
            style: {
              'overlay-opacity': 0.2,
              'overlay-color': '#3b82f6',
            }
          },
        ],
        layout: {
          name: layout,
          animate: true,
          animationDuration: 1000,
          animationEasing: 'ease-out',
          idealEdgeLength: 150,
          nodeOverlap: 30,
          refresh: 20,
          fit: true,
          padding: 60,
          randomize: false,
          componentSpacing: 100,
          nodeRepulsion: 8000,
          edgeElasticity: 200,
          nestingFactor: 5,
          gravity: 80,
          numIter: 1000,
          initialTemp: 200,
          coolingFactor: 0.95,
          minTemp: 1.0,
        } as any,
        minZoom: 0.1,
        maxZoom: 4,
        wheelSensitivity: 0.2,
      });

      cyRef.current = cy;

      // Node click handler
      cy.on('tap', 'node', (evt: any) => {
        const node = evt.target;
        const nodeData = node.data();

        // Find full memory data
        const memory = memories?.find(m => m.id === nodeData.id);
        setSelectedNode(memory || nodeData);
      });

      // Background click handler
      cy.on('tap', (evt: any) => {
        if (evt.target === cy) {
          setSelectedNode(null);
        }
      });

      // Hover effects
      cy.on('mouseover', 'node', (evt: any) => {
        const node = evt.target;
        const importance = node.data('importance') || 0.5;
        const baseSize = Math.max(35, 25 + importance * 50);

        // Store original size if not already stored
        if (!node.data('_originalWidth')) {
          node.data('_originalWidth', baseSize);
          node.data('_originalHeight', baseSize);
        }

        node.style({
          'width': baseSize * 1.3,
          'height': baseSize * 1.3,
          'shadow-blur': 20,
          'shadow-color': node.style('background-color'),
          'shadow-opacity': 0.6,
          'z-index': 999,
        });

        // Highlight connected edges
        node.connectedEdges().style({
          'width': 5,
          'opacity': 1,
          'z-index': 998,
        });

        // Dim other nodes
        cy.nodes().not(node).not(node.neighborhood()).style({
          'opacity': 0.3,
        });

        // Dim other edges
        cy.edges().not(node.connectedEdges()).style({
          'opacity': 0.2,
        });
      });

      cy.on('mouseout', 'node', (evt: any) => {
        const node = evt.target;
        const importance = node.data('importance') || 0.5;
        const baseSize = Math.max(35, 25 + importance * 50);
        const recency = node.data('recency') || 0.5;

        node.style({
          'width': baseSize,
          'height': baseSize,
          'shadow-blur': 8,
          'shadow-color': 'rgba(0, 0, 0, 0.3)',
          'shadow-opacity': 0.3,
          'z-index': 1,
        });

        // Reset edges to their original width based on relationship type
        node.connectedEdges().forEach((edge: any) => {
          const relType = edge.data('type');
          const relStyle = RELATION_STYLES[relType as keyof typeof RELATION_STYLES];
          edge.style({
            'width': relStyle?.width || 2.5,
            'opacity': 0.75,
            'z-index': 1,
          });
        });

        // Restore all nodes and edges opacity
        cy.nodes().style({
          'opacity': (ele: any) => {
            const nodeRecency = ele.data('recency') || 0.5;
            return Math.max(0.5, 0.4 + nodeRecency * 0.6);
          },
        });

        cy.edges().style({
          'opacity': 0.75,
        });
      });

    } catch (error) {
      console.error('Failed to initialize graph:', error);
    }

    return () => {
      if (cyRef.current) {
        cyRef.current.destroy();
      }
    };
  }, [elements, layout, memories]);

  // Minimap initialization
  useEffect(() => {
    if (!minimapRef.current || !cyRef.current || !showMinimap || !elements || elements.length === 0) {
      return;
    }

    // Cleanup existing minimap
    if (minimapCyRef.current) {
      minimapCyRef.current.destroy();
    }

    try {
      // Create simplified minimap version
      const minimapCy = cytoscape({
        container: minimapRef.current,
        elements: elements,
        style: [
          {
            selector: 'node',
            style: {
              'background-color': (ele: any) => {
                const type = ele.data('type');
                return MEMORY_TYPE_COLORS[type as keyof typeof MEMORY_TYPE_COLORS] || '#0088FE';
              },
              'width': 8,
              'height': 8,
              'border-width': 0,
            }
          },
          {
            selector: 'edge',
            style: {
              'width': 1,
              'line-color': '#999',
              'opacity': 0.3,
              'curve-style': 'bezier',
            }
          },
        ],
        layout: {
          name: layout,
          animate: false,
          fit: true,
          padding: 10,
        } as any,
        userZoomingEnabled: false,
        userPanningEnabled: false,
        boxSelectionEnabled: false,
        autoungrabify: true,
        minZoom: 0.1,
        maxZoom: 1,
      });

      minimapCyRef.current = minimapCy;

      // Sync viewport between main graph and minimap
      const syncViewport = () => {
        if (!cyRef.current || !minimapCyRef.current) return;

        const mainPan = cyRef.current.pan();
        const mainZoom = cyRef.current.zoom();
        const mainExtent = cyRef.current.extent();

        // Visual indicator of main viewport on minimap (could be enhanced with overlay)
        minimapCyRef.current.fit(undefined, 10);
      };

      // Listen to viewport changes on main graph
      cyRef.current.on('pan zoom', syncViewport);
      syncViewport(); // Initial sync

      return () => {
        if (cyRef.current) {
          cyRef.current.off('pan zoom', syncViewport);
        }
      };
    } catch (error) {
      console.error('Failed to initialize minimap:', error);
    }

    return () => {
      if (minimapCyRef.current) {
        minimapCyRef.current.destroy();
      }
    };
  }, [cyRef.current, elements, layout, showMinimap]);

  const handleLayoutChange = (newLayout: string) => {
    setLayout(newLayout);
    if (cyRef.current) {
      cyRef.current.layout({
        name: newLayout,
        animate: true,
        animationDuration: 800,
        fit: true,
        padding: 50,
      }).run();
    }
  };

  const handleZoom = (direction: 'in' | 'out' | 'fit') => {
    if (!cyRef.current) return;

    if (direction === 'fit') {
      cyRef.current.fit(undefined, 50);
    } else {
      const zoom = cyRef.current.zoom();
      const newZoom = direction === 'in' ? zoom * 1.2 : zoom / 1.2;
      cyRef.current.zoom({
        level: newZoom,
        renderedPosition: {
          x: cyRef.current.width() / 2,
          y: cyRef.current.height() / 2,
        },
      });
    }
  };

  const handleSearch = (query: string) => {
    if (!cyRef.current) return;

    if (!query) {
      cyRef.current.nodes().style('opacity', 1);
      return;
    }

    cyRef.current.nodes().forEach((node: any) => {
      const label = node.data('label')?.toLowerCase() || '';
      const content = node.data('content')?.toLowerCase() || '';
      const match = label.includes(query.toLowerCase()) || content.includes(query.toLowerCase());

      node.style('opacity', match ? 1 : 0.2);
    });
  };

  const handleExport = (format: 'png' | 'jpg') => {
    if (!cyRef.current) return;

    const imageData = cyRef.current[format]({
      output: 'blob',
      bg: '#ffffff',
      full: true,
      scale: 2,
    });

    const url = URL.createObjectURL(imageData);
    const a = document.createElement('a');
    a.href = url;
    a.download = `memory-graph-${Date.now()}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative w-full h-full">
      <GraphControls
        onLayoutChange={handleLayoutChange}
        onZoom={handleZoom}
        onSearch={handleSearch}
        onExport={handleExport}
        onToggleMinimap={() => setShowMinimap(!showMinimap)}
        currentLayout={layout}
        showMinimap={showMinimap}
      />

      <div
        ref={containerRef}
        className="w-full h-full border rounded-lg bg-gray-50 dark:bg-gray-900"
      />

      {selectedNode && (
        <NodeDetailsPanel
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
        />
      )}

      {showMinimap && elements && elements.length > 0 && (
        <div className="absolute bottom-4 right-4 w-56 h-40 bg-white dark:bg-gray-800 border-2 border-blue-500 dark:border-blue-400 rounded-lg shadow-2xl overflow-hidden">
          <div className="w-full h-6 bg-blue-500 dark:bg-blue-600 flex items-center justify-between px-2">
            <span className="text-xs font-semibold text-white">Overview</span>
            <button
              onClick={() => setShowMinimap(false)}
              className="text-white hover:text-gray-200 text-xs font-bold"
            >
              ×
            </button>
          </div>
          <div
            ref={minimapRef}
            className="w-full h-[calc(100%-1.5rem)] bg-gray-50 dark:bg-gray-900"
          />
        </div>
      )}
    </div>
  );
}
