#!/usr/bin/env python3
"""
Knowledge Graph Visualization
Generates visual representations of memory relationships
Outputs ASCII graph, DOT file for Graphviz, or HTML interactive graph
"""

import requests
import json
from typing import Dict, List, Set
import sys
from collections import defaultdict

MEMORY_API = "http://localhost:8100"

def get_memory_by_id(memory_id: str) -> Dict:
    """Fetch a specific memory by ID."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": memory_id,
            "limit": 1
        })
        response.raise_for_status()
        results = response.json().get("results", [])
        if results and results[0].get("id") == memory_id:
            return results[0]
        return {}
    except Exception as e:
        return {}

def get_related_memories(memory_id: str, max_hops: int = 2) -> Dict:
    """Get memories related to a given memory via graph traversal."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/{memory_id}/related", params={
            "max_hops": max_hops,
            "limit": 50
        })
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"memories": [], "relationships": []}

def get_project_graph(project: str) -> Dict:
    """Get all memories and relationships for a specific project."""
    try:
        # Get memories for project
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": project,
            "project": project,
            "limit": 100
        })
        response.raise_for_status()
        memories = response.json().get("results", [])

        # For each memory, get its relationships
        all_relationships = []
        memory_ids = {m["id"] for m in memories}

        for mem in memories:
            related_data = get_related_memories(mem["id"], max_hops=1)
            for rel in related_data.get("relationships", []):
                # Only include relationships between memories in this project
                if rel["source"] in memory_ids and rel["target"] in memory_ids:
                    all_relationships.append(rel)

        return {
            "memories": memories,
            "relationships": all_relationships
        }
    except Exception as e:
        return {"memories": [], "relationships": []}

def generate_ascii_graph(data: Dict, max_nodes: int = 20) -> str:
    """Generate a simple ASCII representation of the graph."""
    memories = data.get("memories", [])[:max_nodes]
    relationships = data.get("relationships", [])

    if not memories:
        return "No memories to visualize"

    # Build adjacency list
    adj_list = defaultdict(list)
    for rel in relationships:
        source = rel.get("source")
        target = rel.get("target")
        rel_type = rel.get("relation", "related")
        if source and target:
            adj_list[source].append((target, rel_type))

    # Create memory lookup
    mem_lookup = {m["id"]: m for m in memories}

    output = []
    output.append("┌" + "─" * 58 + "┐")
    output.append("│  Knowledge Graph (ASCII View)                             │")
    output.append("└" + "─" * 58 + "┘")
    output.append("")

    for mem in memories[:10]:  # Show first 10 nodes
        mem_id = mem["id"]
        mem_type = mem.get("type", "unknown")
        mem_content = mem.get("content", "")[:40]

        output.append(f"[{mem_id[:8]}] ({mem_type})")
        output.append(f"  {mem_content}...")

        # Show outgoing relationships
        if mem_id in adj_list:
            for target_id, rel_type in adj_list[mem_id][:3]:  # Max 3 relationships per node
                target = mem_lookup.get(target_id, {})
                target_content = target.get("content", "")[:30]
                output.append(f"    └─ {rel_type:12} → [{target_id[:8]}] {target_content}...")

        output.append("")

    return "\n".join(output)

def generate_dot_graph(data: Dict, output_file: str = None) -> str:
    """Generate a DOT file for Graphviz visualization."""
    memories = data.get("memories", [])
    relationships = data.get("relationships", [])

    dot_lines = []
    dot_lines.append("digraph MemoryGraph {")
    dot_lines.append("  rankdir=LR;")
    dot_lines.append("  node [shape=box, style=rounded];")
    dot_lines.append("")

    # Color scheme by type
    type_colors = {
        "error": "#ff6b6b",
        "docs": "#4ecdc4",
        "decision": "#ffe66d",
        "pattern": "#95e1d3",
        "learning": "#c7ceea",
        "context": "#ffa07a"
    }

    # Add nodes
    for mem in memories:
        mem_id = mem["id"]
        mem_type = mem.get("type", "unknown")
        mem_content = mem.get("content", "")[:40].replace('"', '\\"')
        color = type_colors.get(mem_type, "#cccccc")

        label = f"{mem_type}\\n{mem_content}..."
        dot_lines.append(f'  "{mem_id[:8]}" [label="{label}", fillcolor="{color}", style=filled];')

    dot_lines.append("")

    # Add edges with relationship types
    rel_styles = {
        "causes": "dashed",
        "fixes": "bold",
        "contradicts": "dotted",
        "supports": "solid",
        "follows": "solid",
        "related": "solid",
        "supersedes": "bold"
    }

    for rel in relationships:
        source = rel.get("source", "")[:8]
        target = rel.get("target", "")[:8]
        rel_type = rel.get("relation", "related")
        style = rel_styles.get(rel_type, "solid")

        dot_lines.append(f'  "{source}" -> "{target}" [label="{rel_type}", style={style}];')

    dot_lines.append("}")

    dot_content = "\n".join(dot_lines)

    if output_file:
        with open(output_file, "w") as f:
            f.write(dot_content)
        print(f"✅ DOT file saved: {output_file}")
        print(f"   Generate PNG: dot -Tpng {output_file} -o graph.png")
        print(f"   Generate SVG: dot -Tsvg {output_file} -o graph.svg")

    return dot_content

def generate_html_graph(data: Dict, output_file: str = None) -> str:
    """Generate an interactive HTML visualization using vis.js."""
    memories = data.get("memories", [])
    relationships = data.get("relationships", [])

    # Build nodes and edges for vis.js
    nodes = []
    for mem in memories:
        mem_id = mem["id"]
        mem_type = mem.get("type", "unknown")
        mem_content = mem.get("content", "")[:50]

        type_colors = {
            "error": "#ff6b6b",
            "docs": "#4ecdc4",
            "decision": "#ffe66d",
            "pattern": "#95e1d3",
            "learning": "#c7ceea",
            "context": "#ffa07a"
        }

        nodes.append({
            "id": mem_id[:8],
            "label": f"{mem_type}\\n{mem_content}...",
            "color": type_colors.get(mem_type, "#cccccc"),
            "title": mem_content  # Tooltip
        })

    edges = []
    for rel in relationships:
        edges.append({
            "from": rel.get("source", "")[:8],
            "to": rel.get("target", "")[:8],
            "label": rel.get("relation", "related"),
            "arrows": "to"
        })

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Memory Knowledge Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }}
        #graph {{
            width: 100%;
            height: 800px;
            border: 1px solid #ddd;
            background: white;
        }}
        h1 {{
            color: #333;
        }}
        .stats {{
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <h1>🧠 Memory Knowledge Graph</h1>
    <div class="stats">
        <strong>Nodes:</strong> {len(nodes)} |
        <strong>Edges:</strong> {len(edges)} |
        <strong>Avg Connections:</strong> {(len(edges) * 2 / len(nodes)):.2f} if len(nodes) > 0 else 0
    </div>
    <div id="graph"></div>

    <script type="text/javascript">
        var nodes = new vis.DataSet({json.dumps(nodes)});
        var edges = new vis.DataSet({json.dumps(edges)});

        var container = document.getElementById('graph');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                shape: 'box',
                margin: 10,
                widthConstraint: {{
                    maximum: 200
                }}
            }},
            edges: {{
                smooth: {{
                    type: 'continuous'
                }}
            }},
            physics: {{
                enabled: true,
                barnesHut: {{
                    gravitationalConstant: -2000,
                    springConstant: 0.001,
                    springLength: 200
                }}
            }}
        }};

        var network = new vis.Network(container, data, options);
    </script>
</body>
</html>"""

    if output_file:
        with open(output_file, "w") as f:
            f.write(html_content)
        print(f"✅ HTML file saved: {output_file}")
        print(f"   Open in browser: open {output_file}")

    return html_content

def main():
    """Main visualization workflow."""
    print("🕸️  Knowledge Graph Visualization")
    print("═" * 60)

    # Check service
    try:
        response = requests.get(f"{MEMORY_API}/health")
        response.raise_for_status()
        print("✅ Memory service is running\n")
    except Exception as e:
        print(f"❌ Memory service not available: {e}")
        sys.exit(1)

    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 knowledge-graph-viz.py <project-name> [format]")
        print("  python3 knowledge-graph-viz.py <memory-id> [format]")
        print("")
        print("Formats: ascii, dot, html (default: ascii)")
        sys.exit(0)

    target = sys.argv[1]
    output_format = sys.argv[2] if len(sys.argv) > 2 else "ascii"

    # Determine if target is project or memory ID
    print(f"🔍 Fetching graph data for: {target}")

    # Try as project first
    data = get_project_graph(target)

    if not data.get("memories"):
        # Try as memory ID
        print(f"   Not found as project, trying as memory ID...")
        data = get_related_memories(target)

    if not data.get("memories"):
        print(f"❌ No memories found for: {target}")
        sys.exit(1)

    print(f"   Found {len(data['memories'])} memories")
    print(f"   Found {len(data['relationships'])} relationships\n")

    # Generate visualization
    if output_format == "ascii":
        print(generate_ascii_graph(data))

    elif output_format == "dot":
        output_file = f"/tmp/claude/memory-graph-{target}.dot"
        generate_dot_graph(data, output_file)

    elif output_format == "html":
        output_file = f"/tmp/claude/memory-graph-{target}.html"
        generate_html_graph(data, output_file)

    else:
        print(f"❌ Unknown format: {output_format}")
        print("   Supported: ascii, dot, html")
        sys.exit(1)

if __name__ == "__main__":
    main()
