import { ZoomIn, ZoomOut, Maximize2, Crosshair, XCircle, Play, Pause } from 'lucide-react';

interface GraphControlsProps {
  onZoom: (direction: 'in' | 'out' | 'fit') => void;
  onFocusSelected: () => void;
  onClearSelection: () => void;
  onToggleLayout: () => void;
  isLayoutRunning: boolean;
  hasSelection: boolean;
  depthFilter: number;
  onDepthChange: (depth: number) => void;
}

export function GraphControls({
  onZoom,
  onFocusSelected,
  onClearSelection,
  onToggleLayout,
  isLayoutRunning,
  hasSelection,
  depthFilter,
  onDepthChange,
}: GraphControlsProps) {
  const btn = `w-9 h-9 flex items-center justify-center rounded-lg
    text-white/40 hover:text-white hover:bg-white/[0.08] transition-all duration-200`;
  const disabled = 'opacity-30 cursor-not-allowed hover:bg-transparent hover:text-white/40';

  return (
    <div className="absolute bottom-4 right-4 z-20 flex flex-col items-center gap-1
      bg-[#0c0c14]/90 backdrop-blur-xl rounded-xl border border-white/[0.06] p-1.5
      shadow-[0_8px_32px_rgba(0,0,0,0.4)]">

      {/* Zoom */}
      <button onClick={() => onZoom('in')} className={btn} title="Zoom In">
        <ZoomIn className="h-4 w-4" />
      </button>
      <button onClick={() => onZoom('out')} className={btn} title="Zoom Out">
        <ZoomOut className="h-4 w-4" />
      </button>
      <button onClick={() => onZoom('fit')} className={btn} title="Fit to Screen">
        <Maximize2 className="h-4 w-4" />
      </button>

      <div className="w-6 h-px bg-white/[0.08] my-0.5" />

      {/* Selection */}
      <button
        onClick={onFocusSelected}
        disabled={!hasSelection}
        className={`${btn} ${!hasSelection ? disabled : ''}`}
        title="Focus Selected"
      >
        <Crosshair className="h-4 w-4" />
      </button>
      <button
        onClick={onClearSelection}
        disabled={!hasSelection}
        className={`${btn} ${!hasSelection ? disabled : ''}`}
        title="Clear Selection"
      >
        <XCircle className="h-4 w-4" />
      </button>

      <div className="w-6 h-px bg-white/[0.08] my-0.5" />

      {/* Layout toggle */}
      <button
        onClick={onToggleLayout}
        className={`${btn} ${isLayoutRunning ? 'text-violet-400 bg-violet-500/10' : ''}`}
        title={isLayoutRunning ? 'Stop Layout' : 'Run Layout'}
      >
        {isLayoutRunning ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </button>

      {/* Depth filter — visible when node is selected */}
      {hasSelection && (
        <>
          <div className="w-6 h-px bg-white/[0.08] my-0.5" />
          <div className="flex flex-col items-center gap-0.5 py-1">
            <span className="text-[9px] text-white/25 font-medium mb-0.5">HOPS</span>
            {[0, 1, 2, 3, 4, 5].map(d => (
              <button
                key={d}
                onClick={() => onDepthChange(d)}
                className={`w-7 h-5 flex items-center justify-center rounded text-[10px] font-mono transition-all ${
                  depthFilter === d
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-white/30 hover:text-white/60 hover:bg-white/[0.05]'
                }`}
                title={d === 0 ? 'Show all' : `${d} hop${d > 1 ? 's' : ''}`}
              >
                {d === 0 ? '\u221E' : d}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
