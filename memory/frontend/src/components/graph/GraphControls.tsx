import { useState } from 'react';
import { ZoomIn, ZoomOut, Maximize2, Search, Download, Layout, Map } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Select } from '../ui/select';

interface GraphControlsProps {
  onLayoutChange: (layout: string) => void;
  onZoom: (direction: 'in' | 'out' | 'fit') => void;
  onSearch: (query: string) => void;
  onExport: (format: 'png' | 'jpg') => void;
  onToggleMinimap?: () => void;
  currentLayout: string;
  showMinimap?: boolean;
}

export function GraphControls({
  onLayoutChange,
  onZoom,
  onSearch,
  onExport,
  onToggleMinimap,
  currentLayout,
  showMinimap = true,
}: GraphControlsProps) {
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    onSearch(value);
  };

  return (
    <div className="absolute top-4 left-4 right-4 z-10 flex items-center gap-2 bg-white/90 dark:bg-gray-800/90 backdrop-blur-lg p-3 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
      {/* Layout Selector */}
      <div className="flex items-center gap-2">
        <Layout className="h-4 w-4 text-gray-500" />
        <Select
          value={currentLayout}
          onChange={(e) => onLayoutChange(e.target.value)}
          className="w-32"
        >
          <option value="cose">Force</option>
          <option value="circle">Circle</option>
          <option value="grid">Grid</option>
          <option value="breadthfirst">Hierarchy</option>
          <option value="concentric">Concentric</option>
        </Select>
      </div>

      {/* Search */}
      <div className="flex-1 max-w-md relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search nodes..."
          value={searchQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Zoom Controls */}
      <div className="flex items-center gap-1 border-l pl-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onZoom('in')}
          title="Zoom In"
        >
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onZoom('out')}
          title="Zoom Out"
        >
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onZoom('fit')}
          title="Fit to Screen"
        >
          <Maximize2 className="h-4 w-4" />
        </Button>
      </div>

      {/* Minimap Toggle */}
      {onToggleMinimap && (
        <div className="flex items-center gap-1 border-l pl-2">
          <Button
            variant={showMinimap ? "default" : "ghost"}
            size="sm"
            onClick={onToggleMinimap}
            title={showMinimap ? "Hide Minimap" : "Show Minimap"}
          >
            <Map className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Export */}
      <div className="flex items-center gap-1 border-l pl-2">
        <div className="relative inline-flex items-center">
          <Download className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none z-10" />
          <Select
            onChange={(e) => {
              if (e.target.value) {
                onExport(e.target.value as 'png' | 'jpg');
                e.target.value = ''; // Reset after export
              }
            }}
            className="w-32 pl-10"
          >
            <option value="">Export</option>
            <option value="png">PNG Image</option>
            <option value="jpg">JPG Image</option>
          </Select>
        </div>
      </div>
    </div>
  );
}
