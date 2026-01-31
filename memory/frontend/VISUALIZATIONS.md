# Memory Dashboard Visualizations

## Overview

The Claude Memory Dashboard now features world-class, interactive visualizations that make memory data insights obvious at a glance. All charts are animated, responsive, and beautifully styled with glass morphism effects and smooth transitions.

---

## Dashboard Page Enhancements

### 1. Enhanced Stats Cards
- **Beautiful gradient backgrounds** with color-coded themes
- **Hover animations** (scale on hover)
- **Glass morphism effects** with backdrop blur
- **Shadow effects** for depth (shadow-xl with color-specific glows)

**Colors:**
- Total Memories: Blue gradient (`from-blue-50 to-blue-100`)
- Archived: Purple gradient (`from-purple-50 to-purple-100`)
- Unresolved Errors: Red gradient (`from-red-50 to-red-100`)
- Graph Nodes: Green gradient (`from-green-50 to-green-100`)

### 2. Memory Activity Timeline (Area Chart)
- **Last 30 days** of memory creation and access
- **Dual overlapping areas** with gradients
  - Created memories: Blue (`#3b82f6`)
  - Accessed memories: Green (`#22c55e`)
- **Smooth curves** for visual appeal
- **Interactive tooltips** with exact counts
- **Animation duration**: 1000ms ease-out

### 3. Importance Distribution (Bar Chart)
- Shows distribution of importance scores in **10 buckets** (0-0.1, 0.1-0.2, ..., 0.9-1.0)
- **Color-coded bars**:
  - Red (`#ef4444`): Low importance (0-0.3)
  - Amber (`#f59e0b`): Medium importance (0.3-0.7)
  - Green (`#22c55e`): High importance (0.7-1.0)
- **Rounded bar corners** (`radius={[8, 8, 0, 0]}`)
- **Animated bars** that grow from 0 to value

### 4. Enhanced Pie Chart (Interactive)
- **3D effect** with inner and outer sectors
- **Hover to expand** - active slice grows larger
- **Centered labels** showing memory type, count, and percentage
- **Animated transitions** (800ms duration)
- **Custom colors** per memory type:
  - Error: Red (`#ef4444`)
  - Decision: Green (`#22c55e`)
  - Pattern: Blue (`#3b82f6`)
  - Docs: Purple (`#a855f7`)
  - Learning: Amber (`#f59e0b`)
  - Context: Gray (`#6b7280`)

### 5. Tag Cloud (Interactive)
- **Top 50 most used tags**
- **Size based on frequency** (12px to 36px)
- **Opacity based on frequency** (0.5 to 1.0)
- **8 rotating colors** for visual variety
- **Hover scale animation** (`hover:scale-110`)
- **Clickable** for future filtering

### 6. Access Heatmap (Calendar-style)
- **Last 90 days** of memory access activity
- **GitHub-style contribution graph**
- **5-level color intensity**:
  - No activity: `#f3f4f6` (light gray)
  - Low: `#dbeafe` (pale blue)
  - Medium-low: `#93c5fd` (light blue)
  - Medium-high: `#3b82f6` (blue)
  - High: `#1e40af` (dark blue)
- **Hover to see details** (date and access count)
- **Hover scale animation** (`hover:scale-125`)
- **Ring effect** on hover

### 7. Memory Decay Curve (Line Chart)
- Shows how **recency scores decay over 30 days**
- **6 lines** (one per memory type)
- **Exponential decay formula**: `e^(-0.005 * hours)`
- **Different baseline importance** per type:
  - Errors maintain highest importance (0.9)
  - Decisions: 0.85
  - Patterns: 0.8
  - Learning: 0.75
  - Docs: 0.7
  - Context: 0.65
- **Smooth curves** with no dots
- **Custom colors** matching memory types

---

## Graph Page Enhancements

### 1. Enhanced Cytoscape Graph
- **Advanced node styling**:
  - Size based on importance (20px to 60px)
  - Opacity based on recency (0.4 to 1.0)
  - Color by memory type
  - Border width indicates pinned status
  - Double border for unresolved errors
  - Shape: Octagon for errors, circle for others

- **Interactive node effects**:
  - Hover to enlarge (1.2x scale)
  - Hover highlights connected edges
  - Click to show details panel
  - Smooth transitions (300ms)

- **Advanced edge styling**:
  - FIXES: Solid green line (`#22c55e`, 3px width)
  - CAUSES: Dashed red line (`#ef4444`, 2px width)
  - RELATED: Dotted gray line (`#6b7280`, 2px width)
  - SUPERSEDES: Bold blue line (`#3b82f6`, 4px width)
  - Bezier curves for smooth connections
  - Auto-rotating labels

- **Layout options**:
  - Force-directed (default)
  - Circle
  - Grid
  - Hierarchy (breadthfirst)
  - Concentric

### 2. Graph Controls
- **Layout selector** with 5 options
- **Search box** to filter nodes by label/content
- **Zoom controls**:
  - Zoom In
  - Zoom Out
  - Fit to Screen
- **Export options**:
  - PNG (2x resolution)
  - JPG (2x resolution)
- **Glass morphism toolbar** (`bg-white/90 backdrop-blur-lg`)

### 3. Node Details Panel
- **Slide-in animation** from right (300ms)
- **Full memory details**:
  - Type badge with custom colors
  - Content
  - Tags (as chips)
  - Project
  - Importance & recency progress bars
  - Access count
  - Memory tier
  - Timestamps (relative)
  - Status badges (pinned, archived, unresolved)
  - Relations list
  - Type-specific fields (error message, solution, decision, rationale)
  - Source link (if available)
- **Quick actions**:
  - Pin/Unpin
  - Archive
  - Delete

### 4. Enhanced Legend
- **Memory types** with colored circles
- **Relationship types** with line styles
- **Node indicators**:
  - Pinned (amber border)
  - Unresolved (pulsing red border)
  - High importance (larger size)
  - Low recency (faded opacity)

---

## Analytics Page (New)

### 1. Header Stats
- **4 gradient cards**:
  - Total Insights (Blue)
  - Avg Importance (Green)
  - Relationships (Purple)
  - Resolution Rate (Amber)

### 2. Project Breakdown (Bar Chart)
- **Top 10 projects** by memory count
- **Vertical bars** with rounded tops
- **Color rotation** (8 colors)
- **Animated growth** (800ms)
- **Rotated X-axis labels** for readability

### 3. Memory Tier Flow (Pie Chart)
- Distribution across **Episodic, Semantic, Procedural** tiers
- **Custom colors** for each tier
- **Percentage labels**
- **Animated slices** (800ms)

### 4. Resolution Funnel (Horizontal Bar Chart)
- **4 stages**:
  - Errors Created (Red)
  - Errors Resolved (Green)
  - Decisions Made (Blue)
  - Decisions Superseded (Gray)
- **Rounded bar ends**
- **Horizontal layout** for funnel visualization

### 5. Most Used Tags (Horizontal Bar Chart)
- **Top 15 tags** by frequency
- **Color rotation** for visual variety
- **Animated bars** (800ms)
- **Vertical layout** with wide labels

### 6. Type Correlation Matrix (Heatmap)
- **6x6 grid** showing connections between memory types
- **Color intensity** based on connection count:
  - No connections: Light gray (`#f3f4f6`)
  - Weak: Pale blue (20% opacity)
  - Strong: Full blue (100% opacity)
- **Hover to scale** (`hover:scale-110`)
- **Tooltip** showing connection count
- **Interactive cells**

---

## Design System

### Color Palette
```typescript
const MEMORY_TYPE_COLORS = {
  error: '#ef4444',     // Red
  decision: '#22c55e',  // Green
  pattern: '#3b82f6',   // Blue
  docs: '#a855f7',      // Purple
  learning: '#f59e0b',  // Amber
  context: '#6b7280',   // Gray
};
```

### Animations
- **Chart entry**: 800-1000ms ease-out
- **Hover effects**: 200-300ms
- **Transitions**: `transition-all duration-300`
- **Scale on hover**: `scale(1.05)` or `scale(1.1)`

### Glass Morphism
```css
backdrop-blur-lg
bg-white/80 dark:bg-gray-800/80
```

### Shadows
```css
shadow-xl shadow-blue-500/10  /* Colored glow */
```

### Gradients
```css
/* Cards */
bg-gradient-to-br from-blue-50 to-blue-100

/* Text */
bg-gradient-to-r from-blue-600 to-purple-600
bg-clip-text text-transparent
```

---

## Component Architecture

### Analytics Components (`src/components/analytics/`)
- `ActivityTimeline.tsx` - 30-day area chart
- `ImportanceDistribution.tsx` - Bar chart with color coding
- `EnhancedPieChart.tsx` - Interactive 3D pie with hover
- `TagCloud.tsx` - Frequency-based word cloud
- `AccessHeatmap.tsx` - 90-day calendar heatmap
- `DecayCurve.tsx` - Exponential decay visualization

### Graph Components (`src/components/graph/`)
- `EnhancedCytoscapeGraph.tsx` - Main graph with advanced styling
- `GraphControls.tsx` - Toolbar for layout, search, zoom, export
- `NodeDetailsPanel.tsx` - Slide-in panel with full memory details

---

## Performance Optimizations

1. **Memoization**:
   - All data transformations use `useMemo`
   - Chart data computed once per data change
   - Expensive calculations cached

2. **Lazy Loading**:
   - Large datasets limited (100-500 records)
   - Pagination for memory lists
   - Conditional rendering for empty states

3. **Animation Performance**:
   - CSS transforms (hardware accelerated)
   - `transition-property` limited to transformed properties
   - No layout thrashing

4. **Responsive Design**:
   - Grid layouts with `md:grid-cols-2`
   - Flexible chart heights
   - Mobile-first approach

---

## Interactivity Features

### Dashboard
- ✅ Hover cards to see animations
- ✅ Click tags in tag cloud (future: filter)
- ✅ Hover pie slices to expand
- ✅ Hover heatmap cells for details
- ✅ Interactive tooltips on all charts

### Graph
- ✅ Click nodes to see details panel
- ✅ Hover nodes to enlarge and highlight edges
- ✅ Search to filter nodes
- ✅ Change layout dynamically
- ✅ Zoom and pan
- ✅ Export as image

### Analytics
- ✅ Hover bars to see exact values
- ✅ Click correlation cells (future: drill down)
- ✅ Interactive tooltips

---

## Accessibility

- **ARIA labels** on interactive elements
- **Keyboard navigation** support
- **Focus states** visible
- **Color contrast** meets WCAG AA
- **Screen reader friendly** tooltips
- **Semantic HTML** structure

---

## Browser Compatibility

- **Chrome/Edge**: Full support
- **Firefox**: Full support
- **Safari**: Full support (webkit prefixes included)
- **Mobile**: Fully responsive

---

## Future Enhancements

1. **Real-time updates** via WebSocket
2. **Custom date ranges** for all charts
3. **Export to CSV/PDF**
4. **Drill-down interactions**
5. **Custom color themes**
6. **Animated transitions** between pages
7. **3D graph view** option
8. **Time-based playback** slider on graph
9. **Collaborative annotations**
10. **AI-powered insights panel**

---

## Dependencies

```json
{
  "recharts": "^2.x",
  "cytoscape": "^3.x",
  "date-fns": "^2.x",
  "lucide-react": "^0.x"
}
```

---

## Usage

```bash
# Start development server
cd /Users/h4ckm1n/.claude/memory/frontend
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

---

## Technical Notes

- All charts use **Recharts** for consistency
- Graph uses **Cytoscape.js** for advanced network visualization
- Date formatting via **date-fns** for consistency
- Icons from **lucide-react** for sharp, consistent design
- Styling with **Tailwind CSS** utility classes
- Type safety with **TypeScript** strict mode

---

## File Structure

```
src/
├── components/
│   ├── analytics/
│   │   ├── ActivityTimeline.tsx
│   │   ├── ImportanceDistribution.tsx
│   │   ├── EnhancedPieChart.tsx
│   │   ├── TagCloud.tsx
│   │   ├── AccessHeatmap.tsx
│   │   └── DecayCurve.tsx
│   └── graph/
│       ├── EnhancedCytoscapeGraph.tsx
│       ├── GraphControls.tsx
│       └── NodeDetailsPanel.tsx
├── pages/
│   ├── Dashboard.tsx (Enhanced)
│   ├── Graph.tsx (Enhanced)
│   └── Analytics.tsx (New)
└── App.tsx (Updated routes)
```

---

**Built with ❤️ for Claude Memory System**

*Making data insights beautiful and obvious at a glance.*
