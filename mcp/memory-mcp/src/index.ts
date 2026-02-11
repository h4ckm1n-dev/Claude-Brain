#!/usr/bin/env node
/**
 * Claude Memory MCP Server v2.0
 *
 * Enhanced MCP layer with graph-aware search, consolidation,
 * and bulk operations. Calls the Dockerized memory service API.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFileSync } from "node:fs";

// Configuration
const MEMORY_SERVICE_URL = process.env.MEMORY_SERVICE_URL || "http://localhost:8100";

/**
 * Read session ID set by the SessionStart hook.
 * The MCP server process is spawned before hooks run, so process.env won't have it.
 * The hook writes the session ID to /tmp/.claude-memory-session-id.
 */
function getSessionId(): string | undefined {
  // Fast path: check process.env first
  if (process.env.MEMORY_SESSION_ID) return process.env.MEMORY_SESSION_ID;
  // Read from file written by session-start.sh hook
  try {
    const sid = readFileSync("/tmp/.claude-memory-session-id", "utf-8").trim();
    if (sid) return sid;
  } catch {
    // File doesn't exist yet — hook hasn't run
  }
  return undefined;
}

// Types
interface Memory {
  id: string;
  type: string;
  content: string;
  tags: string[];
  project?: string;
  source?: string;
  context?: string;
  created_at: string;
  updated_at: string;
  access_count: number;
  usefulness_score: number;
  resolved: boolean;
  error_message?: string;
  solution?: string;
  prevention?: string;
  decision?: string;
  rationale?: string;
  alternatives?: string[];
}

interface SearchResult {
  memory: Memory;
  score: number;
  composite_score?: number;
}

interface RelatedMemory {
  id: string;
  type: string;
  preview: string;
  distance: number;
  relationship_path: string[];
}

interface GraphStats {
  enabled: boolean;
  memory_nodes?: number;
  project_nodes?: number;
  tag_nodes?: number;
  relationships?: number;
}

interface ConsolidationResult {
  analyzed: number;
  consolidated: number;
  archived: number;
  kept: number;
  dry_run: boolean;
}

// API Helper
async function apiCall<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${MEMORY_SERVICE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error (${response.status}): ${error}`);
  }

  return response.json() as Promise<T>;
}

// Create MCP Server
const server = new Server(
  {
    name: "claude-memory",
    version: "2.0.0",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

// Tool Definitions
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      // === Core Memory Tools ===
      {
        name: "store_memory",
        description:
          "Store a new memory (error, documentation, decision, pattern, or learning). Automatically deduplicates similar memories.",
        inputSchema: {
          type: "object",
          properties: {
            type: {
              type: "string",
              enum: ["error", "docs", "decision", "pattern", "learning", "context"],
              description: "Type of memory to store",
            },
            content: {
              type: "string",
              description: "Main content of the memory",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Tags for categorization",
            },
            project: {
              type: "string",
              description: "Project name (optional)",
            },
            context: {
              type: "string",
              description: "Additional context",
            },
            error_message: {
              type: "string",
              description: "Error message (for error type)",
            },
            solution: {
              type: "string",
              description: "Solution that fixed the issue",
            },
            prevention: {
              type: "string",
              description: "How to prevent this in future",
            },
            decision: {
              type: "string",
              description: "Decision made (for decision type)",
            },
            rationale: {
              type: "string",
              description: "Rationale for the decision",
            },
            alternatives: {
              type: "array",
              items: { type: "string" },
              description: "Alternatives considered",
            },
          },
          required: ["type", "content"],
        },
      },
      {
        name: "search_memory",
        description: "Search memories using hybrid semantic + keyword search with cross-encoder reranking",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query (natural language)",
            },
            type: {
              type: "string",
              enum: ["error", "docs", "decision", "pattern", "learning", "context"],
              description: "Filter by memory type",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Filter by tags",
            },
            project: {
              type: "string",
              description: "Filter by project",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 10)",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "get_context",
        description: "Get relevant context memories for the current work",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Project name (optional, use '_all' for global)",
            },
            hours: {
              type: "number",
              description: "Hours to look back (default: 24)",
            },
            types: {
              type: "string",
              description: "Comma-separated memory types to include",
            },
          },
        },
      },
      {
        name: "mark_resolved",
        description: "Mark an error memory as resolved with a solution",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "ID of the memory to resolve",
            },
            solution: {
              type: "string",
              description: "Solution that fixed the error",
            },
          },
          required: ["memory_id", "solution"],
        },
      },
      {
        name: "link_memories",
        description: "Create a relationship between two memories (also updates knowledge graph)",
        inputSchema: {
          type: "object",
          properties: {
            source_id: {
              type: "string",
              description: "Source memory ID",
            },
            target_id: {
              type: "string",
              description: "Target memory ID",
            },
            relation: {
              type: "string",
              enum: ["causes", "fixes", "contradicts", "supports", "follows", "related", "supersedes", "similar_to"],
              description: "Type of relationship",
            },
          },
          required: ["source_id", "target_id", "relation"],
        },
      },
      {
        name: "memory_stats",
        description: "Get memory collection statistics including graph stats",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },

      // === New Phase 5 Tools ===
      {
        name: "find_related",
        description: "Find memories related to a given memory using knowledge graph traversal",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "Memory ID to find related memories for",
            },
            max_hops: {
              type: "number",
              description: "Maximum relationship hops (1-3, default: 2)",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 20)",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "memory_timeline",
        description: "Get memories ordered by time with their relationships",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Filter by project",
            },
            memory_type: {
              type: "string",
              description: "Filter by memory type",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 50)",
            },
          },
        },
      },
      {
        name: "consolidate_memories",
        description: "Run memory consolidation to merge similar old memories and archive low-value ones",
        inputSchema: {
          type: "object",
          properties: {
            older_than_days: {
              type: "number",
              description: "Process memories older than this (default: 7)",
            },
            dry_run: {
              type: "boolean",
              description: "If true, preview changes without applying (default: false)",
            },
          },
        },
      },
      {
        name: "bulk_store",
        description: "Store multiple memories in a single operation",
        inputSchema: {
          type: "object",
          properties: {
            memories: {
              type: "array",
              items: {
                type: "object",
                properties: {
                  type: { type: "string" },
                  content: { type: "string" },
                  tags: { type: "array", items: { type: "string" } },
                  project: { type: "string" },
                  context: { type: "string" },
                  error_message: { type: "string" },
                  solution: { type: "string" },
                  prevention: { type: "string" },
                  decision: { type: "string" },
                  rationale: { type: "string" },
                  alternatives: { type: "array", items: { type: "string" } },
                },
                required: ["type", "content"],
              },
              description: "Array of memories to store",
            },
          },
          required: ["memories"],
        },
      },
      {
        name: "forget_memory",
        description: "Delete a memory by ID (also removes from knowledge graph)",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "ID of the memory to delete",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "archive_memory",
        description: "Archive a memory (soft delete, keeps in database but excluded from search)",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "ID of the memory to archive",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "graph_stats",
        description: "Get knowledge graph statistics (nodes, relationships, projects)",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "suggest_memories",
        description:
          "Proactively get relevant memory suggestions based on current context. " +
          "Use at conversation start to surface potentially useful memories without explicit search.",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Current project name",
            },
            keywords: {
              type: "array",
              items: { type: "string" },
              description: "Keywords relevant to current task",
            },
            current_files: {
              type: "array",
              items: { type: "string" },
              description: "Recently accessed files",
            },
            git_branch: {
              type: "string",
              description: "Current git branch",
            },
            limit: {
              type: "number",
              description: "Maximum suggestions (default: 5)",
            },
          },
        },
      },

      // === Document Tools (Separate from Memories) ===
      {
        name: "search_documents",
        description:
          "Search indexed documents (files from your filesystem). " +
          "Use this for finding code, markdown, PDFs, and other file content. " +
          "For structured knowledge (errors, decisions, patterns), use search_memory instead.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query (natural language or keywords)",
            },
            file_type: {
              type: "string",
              description: "Filter by file extension (e.g., '.md', '.py', '.ts')",
            },
            folder: {
              type: "string",
              description: "Filter by folder path",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 10)",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "document_stats",
        description: "Get document indexing statistics (total chunks, collection status)",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },

      // === Memory Management Tools ===
      {
        name: "reinforce_memory",
        description:
          "Boost a useful memory's strength to prevent it from decaying. " +
          "Use when a memory proves particularly valuable during a session.",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "ID of the memory to reinforce",
            },
            boost_amount: {
              type: "number",
              description: "Amount to boost strength (0.0-0.5, default: 0.2)",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "pin_memory",
        description:
          "Pin a memory so it never decays. Use for critical decisions, patterns, or knowledge that must persist indefinitely.",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "ID of the memory to pin",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "unpin_memory",
        description: "Unpin a memory to allow it to decay normally again.",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "ID of the memory to unpin",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "get_weak_memories",
        description:
          "Get memories with low strength that are fading and may be archived soon. " +
          "Use to review what knowledge is being lost and decide whether to reinforce or let go.",
        inputSchema: {
          type: "object",
          properties: {
            strength_threshold: {
              type: "number",
              description: "Strength threshold (0.0-1.0, default: 0.3)",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 50)",
            },
          },
        },
      },
      {
        name: "export_memories",
        description: "Export memories as JSON, CSV, or Obsidian-compatible markdown for backup.",
        inputSchema: {
          type: "object",
          properties: {
            format: {
              type: "string",
              enum: ["json", "csv", "obsidian"],
              description: "Export format (default: json)",
            },
            type: {
              type: "string",
              description: "Filter by memory type",
            },
            project: {
              type: "string",
              description: "Filter by project",
            },
          },
        },
      },

      // === Brain Intelligence Tools ===
      {
        name: "brain_dream",
        description:
          "Trigger dream mode - rapid random memory replay to discover unexpected connections. " +
          "Simulates REM sleep consolidation.",
        inputSchema: {
          type: "object",
          properties: {
            duration: {
              type: "number",
              description: "Duration in seconds (10-300, default: 30)",
            },
          },
        },
      },
      {
        name: "brain_detect_conflicts",
        description:
          "Find contradicting memories and resolve conflicts via SUPERSEDES relationships. " +
          "Use to maintain knowledge consistency.",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Maximum memories to check (default: 50)",
            },
          },
        },
      },
      {
        name: "brain_replay",
        description:
          "Replay important memories to strengthen them. " +
          "Simulates how brains consolidate memories during rest.",
        inputSchema: {
          type: "object",
          properties: {
            count: {
              type: "number",
              description: "Number of memories to replay (default: 10)",
            },
            importance_threshold: {
              type: "number",
              description: "Only replay above this importance (0.0-1.0, default: 0.5)",
            },
          },
        },
      },
      {
        name: "run_inference",
        description:
          "Discover new relationships between memories automatically. " +
          "Runs temporal, semantic, causal, and error-solution inference.",
        inputSchema: {
          type: "object",
          properties: {
            inference_type: {
              type: "string",
              enum: ["all", "temporal", "semantic", "causal", "error-solution"],
              description: "Type of inference to run (default: all)",
            },
          },
        },
      },

      // === Temporal & Analytics Tools ===
      {
        name: "temporal_query",
        description:
          "Query what was known at a specific point in time. " +
          "Answers: 'What did I know about X on date Y?'",
        inputSchema: {
          type: "object",
          properties: {
            target_time: {
              type: "string",
              description: "ISO 8601 timestamp (e.g., 2024-01-15T12:00:00Z)",
            },
            project: {
              type: "string",
              description: "Filter by project",
            },
            limit: {
              type: "number",
              description: "Maximum results (default: 50)",
            },
          },
          required: ["target_time"],
        },
      },
      {
        name: "error_trends",
        description:
          "Analyze recurring error patterns, detect error spikes, and identify error clusters. " +
          "Use to find systematic issues.",
        inputSchema: {
          type: "object",
          properties: {
            time_window_days: {
              type: "number",
              description: "Time window in days (default: 30)",
            },
            min_cluster_size: {
              type: "number",
              description: "Minimum errors to form a cluster (default: 2)",
            },
          },
        },
      },
      {
        name: "knowledge_gaps",
        description:
          "Detect areas with thin knowledge: topics with errors but no patterns, " +
          "projects with low documentation, and expertise gaps.",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "query_enhance",
        description:
          "Improve a search query with synonym expansion and typo correction. " +
          "Use before search_memory for better results on vague or misspelled queries.",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Search query to enhance",
            },
            expand_synonyms: {
              type: "boolean",
              description: "Add synonyms for better recall (default: true)",
            },
            correct_typos: {
              type: "boolean",
              description: "Suggest typo corrections (default: true)",
            },
          },
          required: ["query"],
        },
      },

      // === Session Management Tools ===
      {
        name: "new_session",
        description:
          "Create a new conversation session context. " +
          "Use at the start of a focused work session to group related memories.",
        inputSchema: {
          type: "object",
          properties: {
            project: {
              type: "string",
              description: "Project name to associate with session",
            },
          },
        },
      },
      {
        name: "consolidate_session",
        description:
          "Consolidate all memories from a session into a summary. " +
          "Creates a summary memory and links all session memories together.",
        inputSchema: {
          type: "object",
          properties: {
            session_id: {
              type: "string",
              description: "Session ID to consolidate",
            },
          },
          required: ["session_id"],
        },
      },

      // === Graph Enhancement Tools ===
      {
        name: "graph_contradictions",
        description:
          "Find contradicting memory pairs in the knowledge graph. " +
          "Detects cycles like A supports B but B contradicts A.",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Maximum contradictions to find (default: 50)",
            },
          },
        },
      },
      {
        name: "graph_recommendations",
        description:
          "Get recommended memories based on shared graph relationship patterns. " +
          "Finds memories similar to the given one via collaborative filtering on the knowledge graph.",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "Memory ID to get recommendations for",
            },
            limit: {
              type: "number",
              description: "Maximum recommendations (default: 10)",
            },
          },
          required: ["memory_id"],
        },
      },
    ],
  };
});

// Tool Handlers
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    switch (name) {
      // === Core Memory Tools ===
      case "store_memory": {
        // Inject session_id from environment (set by SessionStart hook)
        const storeArgs = { ...args as Record<string, unknown> };
        const sessionId = getSessionId();
        if (sessionId && !storeArgs.session_id) {
          storeArgs.session_id = sessionId;
        }
        const memory = await apiCall<Memory>("/memories", {
          method: "POST",
          body: JSON.stringify(storeArgs),
        });
        return {
          content: [
            {
              type: "text",
              text: `Stored memory ${memory.id} (type: ${memory.type})\n\nContent: ${memory.content}`,
            },
          ],
        };
      }

      case "search_memory": {
        const results = await apiCall<SearchResult[]>("/memories/search", {
          method: "POST",
          body: JSON.stringify(args),
        });

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No memories found matching your query.",
              },
            ],
          };
        }

        const formatted = results
          .map(
            (r, i) =>
              `${i + 1}. [${r.memory.type}] (score: ${r.score.toFixed(2)})\n` +
              `   ID: ${r.memory.id}\n` +
              `   ${r.memory.content}\n` +
              (r.memory.solution ? `   Solution: ${r.memory.solution}\n` : "") +
              (r.memory.tags.length > 0 ? `   Tags: ${r.memory.tags.join(", ")}` : "")
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Found ${results.length} memories:\n\n${formatted}`,
            },
          ],
        };
      }

      case "get_context": {
        const project = (args as Record<string, unknown>).project as string || "_all";
        const hours = (args as Record<string, unknown>).hours as number || 24;
        const types = (args as Record<string, unknown>).types as string || "";

        const params = new URLSearchParams({ hours: String(hours) });
        if (types) params.append("types", types);

        const context = await apiCall<{
          memories: Memory[];
          documents: Array<{
            file_path: string;
            content: string;
            score: number;
            file_type?: string;
          }>;
          combined_count: number;
          has_documents: boolean;
        }>(`/context/${project}?${params.toString()}`);

        if (context.combined_count === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No recent context found.",
              },
            ],
          };
        }

        let formatted = `📚 Context (last ${hours}h): ${context.combined_count} items\n\n`;

        // Format memories
        if (context.memories.length > 0) {
          formatted += `=== MEMORIES (${context.memories.length}) ===\n\n`;
          formatted += context.memories
            .map(
              (m) =>
                `[${m.type}] ${m.content}` +
                (m.solution ? `\n  → Solution: ${m.solution}` : "") +
                (m.resolved === false && m.type === "error" ? " (UNRESOLVED)" : "")
            )
            .join("\n\n");
        }

        // Format documents
        if (context.documents.length > 0) {
          formatted += `\n\n=== RELEVANT DOCUMENTS (${context.documents.length}) ===\n\n`;
          formatted += context.documents
            .map(
              (d) =>
                `📄 ${d.file_path}${d.file_type ? ` (${d.file_type})` : ""}\n` +
                `   ${d.content.substring(0, 200)}...` +
                `\n   Score: ${d.score.toFixed(3)}`
            )
            .join("\n\n");
        }

        return {
          content: [
            {
              type: "text",
              text: formatted,
            },
          ],
        };
      }

      case "mark_resolved": {
        const { memory_id, solution } = args as { memory_id: string; solution: string };
        const memory = await apiCall<Memory>(
          `/memories/${memory_id}/resolve?solution=${encodeURIComponent(solution)}`,
          { method: "POST" }
        );
        return {
          content: [
            {
              type: "text",
              text: `Marked memory ${memory.id} as resolved.\n\nSolution: ${solution}`,
            },
          ],
        };
      }

      case "link_memories": {
        const { source_id, target_id, relation } = args as {
          source_id: string;
          target_id: string;
          relation: string;
        };
        await apiCall("/memories/link", {
          method: "POST",
          body: JSON.stringify({
            source_id,
            target_id,
            relation_type: relation,
          }),
        });
        return {
          content: [
            {
              type: "text",
              text: `Linked ${source_id} → [${relation}] → ${target_id}`,
            },
          ],
        };
      }

      case "memory_stats": {
        const stats = await apiCall<{
          total_memories: number;
          active_memories: number;
          archived_memories: number;
          by_type: Record<string, number>;
          unresolved_errors: number;
        }>("/stats");

        const graphStats = await apiCall<GraphStats>("/graph/stats").catch((): GraphStats => ({
          enabled: false,
          memory_nodes: 0,
          project_nodes: 0,
          tag_nodes: 0,
          relationships: 0,
        }));

        const typeBreakdown = Object.entries(stats.by_type)
          .map(([type, count]) => `  ${type}: ${count}`)
          .join("\n");

        let graphInfo = "";
        if (graphStats.enabled) {
          graphInfo = `\n\nKnowledge Graph:\n  Memory nodes: ${graphStats.memory_nodes}\n  Projects: ${graphStats.project_nodes}\n  Tags: ${graphStats.tag_nodes}\n  Relationships: ${graphStats.relationships}`;
        }

        return {
          content: [
            {
              type: "text",
              text:
                `Memory Statistics:\n\n` +
                `Total memories: ${stats.total_memories}\n` +
                `Active: ${stats.active_memories}\n` +
                `Archived: ${stats.archived_memories}\n` +
                `Unresolved errors: ${stats.unresolved_errors}\n\n` +
                `By type:\n${typeBreakdown}` +
                graphInfo,
            },
          ],
        };
      }

      // === New Phase 5 Tools ===
      case "find_related": {
        const { memory_id, max_hops = 2, limit = 20 } = args as {
          memory_id: string;
          max_hops?: number;
          limit?: number;
        };

        const result = await apiCall<{
          memory_id: string;
          related: RelatedMemory[];
          count: number;
        }>(`/graph/related/${memory_id}?max_hops=${max_hops}&limit=${limit}`);

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No related memories found for ${memory_id}`,
              },
            ],
          };
        }

        const formatted = result.related
          .map(
            (r, i) =>
              `${i + 1}. [${r.type}] (distance: ${r.distance})\n` +
              `   ID: ${r.id}\n` +
              `   ${r.preview}\n` +
              `   Path: ${r.relationship_path.join(" → ")}`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Found ${result.count} related memories:\n\n${formatted}`,
            },
          ],
        };
      }

      case "memory_timeline": {
        const { project, memory_type, limit = 50 } = args as {
          project?: string;
          memory_type?: string;
          limit?: number;
        };

        const params = new URLSearchParams({ limit: String(limit) });
        if (project) params.append("project", project);
        if (memory_type) params.append("memory_type", memory_type);

        const result = await apiCall<{
          timeline: Array<{
            id: string;
            type: string;
            preview: string;
            created_at: unknown;
            relationships: Array<{ type: string; target_id: string }>;
          }>;
          count: number;
        }>(`/graph/timeline?${params.toString()}`);

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No memories found in timeline.",
              },
            ],
          };
        }

        const formatted = result.timeline
          .map(
            (m, i) =>
              `${i + 1}. [${m.type}] ${m.preview}` +
              (m.relationships.length > 0
                ? `\n   Relations: ${m.relationships.map((r) => `→[${r.type}]`).join(", ")}`
                : "")
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Timeline (${result.count} memories):\n\n${formatted}`,
            },
          ],
        };
      }

      case "consolidate_memories": {
        const { older_than_days = 7, dry_run = false } = args as {
          older_than_days?: number;
          dry_run?: boolean;
        };

        const result = await apiCall<ConsolidationResult>(
          `/consolidate?older_than_days=${older_than_days}&dry_run=${dry_run}`,
          { method: "POST" }
        );

        const mode = dry_run ? "Preview" : "Completed";
        return {
          content: [
            {
              type: "text",
              text:
                `Consolidation ${mode}:\n\n` +
                `Analyzed: ${result.analyzed} memories\n` +
                `Consolidated: ${result.consolidated} clusters\n` +
                `Archived: ${result.archived} low-value memories\n` +
                `Kept: ${result.kept} memories`,
            },
          ],
        };
      }

      case "bulk_store": {
        const { memories } = args as {
          memories: Array<{
            type: string;
            content: string;
            tags?: string[];
            project?: string;
            context?: string;
            error_message?: string;
            solution?: string;
            prevention?: string;
            decision?: string;
            rationale?: string;
            alternatives?: string[];
            session_id?: string;
          }>;
        };

        // Inject session_id from environment into each memory (set by SessionStart hook)
        const bulkSessionId = getSessionId();
        const enrichedMemories = bulkSessionId
          ? memories.map((m) => m.session_id ? m : { ...m, session_id: bulkSessionId })
          : memories;

        const bulkResult = await apiCall<{
          stored: number;
          failed: number;
          results: Array<{ index: number; id: string; status: string; duplicate_warning?: string }>;
          errors: Array<{ index: number; error: string | object }>;
        }>("/memories/bulk", {
          method: "POST",
          body: JSON.stringify(enrichedMemories),
        });

        const lines: string[] = [];
        lines.push(`Stored ${bulkResult.stored} memories:\n`);
        for (const r of bulkResult.results) {
          let line = `- ${r.id} (${memories[r.index]?.type || "unknown"})`;
          if (r.duplicate_warning) line += ` [duplicate warning]`;
          lines.push(line);
        }
        if (bulkResult.failed > 0) {
          lines.push(`\nFailed ${bulkResult.failed}:\n`);
          for (const e of bulkResult.errors) {
            const errMsg = typeof e.error === "string" ? e.error : JSON.stringify(e.error);
            lines.push(`- index ${e.index}: ${errMsg}`);
          }
        }

        return {
          content: [
            {
              type: "text",
              text: lines.join("\n"),
            },
          ],
        };
      }

      case "forget_memory": {
        const { memory_id } = args as { memory_id: string };

        await apiCall(`/memories/${memory_id}`, { method: "DELETE" });

        return {
          content: [
            {
              type: "text",
              text: `Deleted memory ${memory_id}`,
            },
          ],
        };
      }

      case "archive_memory": {
        const { memory_id } = args as { memory_id: string };

        await apiCall(`/memories/${memory_id}/archive`, { method: "POST" });

        return {
          content: [
            {
              type: "text",
              text: `Archived memory ${memory_id}`,
            },
          ],
        };
      }

      case "graph_stats": {
        const stats = await apiCall<GraphStats>("/graph/stats");

        if (!stats.enabled) {
          return {
            content: [
              {
                type: "text",
                text: "Knowledge graph is not available (Neo4j not connected)",
              },
            ],
          };
        }

        return {
          content: [
            {
              type: "text",
              text:
                `Knowledge Graph Statistics:\n\n` +
                `Memory nodes: ${stats.memory_nodes}\n` +
                `Project nodes: ${stats.project_nodes}\n` +
                `Tag nodes: ${stats.tag_nodes}\n` +
                `Total relationships: ${stats.relationships}`,
            },
          ],
        };
      }

      case "suggest_memories": {
        const { project, keywords, current_files, git_branch, limit = 5 } =
          args as {
            project?: string;
            keywords?: string[];
            current_files?: string[];
            git_branch?: string;
            limit?: number;
          };

        const result = await apiCall<{
          suggestions: Array<{
            id: string;
            type: string;
            content: string;
            tags: string[];
            project: string | null;
            relevance_score: number;
            decay_score: number;
            combined_score: number;
            reason: string;
            access_count: number;
            created_at: string;
          }>;
          count: number;
        }>("/memories/suggest", {
          method: "POST",
          body: JSON.stringify({
            project,
            keywords,
            current_files,
            git_branch,
            limit,
          }),
        });

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No relevant memories found for the current context.",
              },
            ],
          };
        }

        const suggestions = result.suggestions
          .map(
            (s, i) =>
              `${i + 1}. ${s.reason}\n` +
              `   ID: ${s.id}\n` +
              `   Content: ${s.content}\n` +
              `   Tags: ${s.tags.join(", ") || "none"}\n` +
              `   Score: ${s.combined_score} (relevance: ${s.relevance_score}, decay: ${s.decay_score})\n` +
              `   Accessed: ${s.access_count}x`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text:
                `🧠 Memory Suggestions (${result.count}):\n\n${suggestions}\n\n` +
                `These memories were selected based on semantic relevance, importance decay, and access patterns.`,
            },
          ],
        };
      }

      // === Document Tools ===
      case "search_documents": {
        const { query, file_type, folder, limit = 10 } = args as {
          query: string;
          file_type?: string;
          folder?: string;
          limit?: number;
        };

        const params = new URLSearchParams({ query, limit: String(limit) });
        if (file_type) params.append("file_type", file_type);
        if (folder) params.append("folder", folder);

        const result = await apiCall<{
          query: string;
          results: Array<{
            id: string;
            score: number;
            file_path: string;
            file_type: string;
            folder: string;
            content: string;
            chunk_index: number;
            total_chunks: number;
            modified_at: string;
          }>;
          count: number;
        }>(`/documents/search?${params}`);

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No documents found for query: "${query}"${
                  file_type ? ` (file type: ${file_type})` : ""
                }${folder ? ` (folder: ${folder})` : ""}`,
              },
            ],
          };
        }

        const documents = result.results
          .map(
            (doc) =>
              `📄 ${doc.file_path} (score: ${doc.score.toFixed(2)})\n` +
              `   Type: ${doc.file_type} | Chunk: ${doc.chunk_index + 1}/${doc.total_chunks}\n` +
              `   ${doc.content.substring(0, 200)}${doc.content.length > 200 ? "..." : ""}`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text:
                `📚 Document Search Results (${result.count}):\n\n${documents}\n\n` +
                `These are filesystem documents indexed for retrieval.`,
            },
          ],
        };
      }

      case "document_stats": {
        const result = await apiCall<{
          collection: string;
          total_chunks: number;
          status: string;
        }>("/documents/stats");

        return {
          content: [
            {
              type: "text",
              text:
                `📊 Document Statistics:\n\n` +
                `Collection: ${result.collection}\n` +
                `Total Chunks: ${result.total_chunks}\n` +
                `Status: ${result.status}`,
            },
          ],
        };
      }

      // === Memory Management Tools ===
      case "reinforce_memory": {
        const { memory_id, boost_amount = 0.2 } = args as {
          memory_id: string;
          boost_amount?: number;
        };

        const result = await apiCall<{
          status: string;
          id: string;
          new_strength: number;
          boost_amount: number;
        }>(`/memories/${memory_id}/reinforce?boost_amount=${boost_amount}`, {
          method: "POST",
        });

        return {
          content: [
            {
              type: "text",
              text: `Reinforced memory ${result.id}\nNew strength: ${result.new_strength.toFixed(3)}\nBoost: +${result.boost_amount}`,
            },
          ],
        };
      }

      case "pin_memory": {
        const { memory_id } = args as { memory_id: string };
        await apiCall(`/memories/${memory_id}/pin`, { method: "POST" });
        return {
          content: [
            {
              type: "text",
              text: `Pinned memory ${memory_id} - it will never decay.`,
            },
          ],
        };
      }

      case "unpin_memory": {
        const { memory_id } = args as { memory_id: string };
        await apiCall(`/memories/${memory_id}/unpin`, { method: "POST" });
        return {
          content: [
            {
              type: "text",
              text: `Unpinned memory ${memory_id} - normal decay resumed.`,
            },
          ],
        };
      }

      case "get_weak_memories": {
        const { strength_threshold = 0.3, limit = 50 } = args as {
          strength_threshold?: number;
          limit?: number;
        };

        const result = await apiCall<
          Array<{
            id: string;
            content: string;
            type: string;
            memory_strength: number;
            access_count: number;
            created_at: string;
          }>
        >(
          `/forgetting/weak?strength_threshold=${strength_threshold}&limit=${limit}`
        );

        if (result.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No weak memories found - all memories are strong.",
              },
            ],
          };
        }

        const formatted = result
          .map(
            (m, i) =>
              `${i + 1}. [${m.type}] strength: ${(m.memory_strength ?? 0).toFixed(3)}\n` +
              `   ID: ${m.id}\n` +
              `   ${m.content.substring(0, 150)}${m.content.length > 150 ? "..." : ""}\n` +
              `   Accessed: ${m.access_count}x`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Weak memories (${result.length}, threshold: ${strength_threshold}):\n\n${formatted}`,
            },
          ],
        };
      }

      case "export_memories": {
        const { format = "json", type: memType, project } = args as {
          format?: string;
          type?: string;
          project?: string;
        };

        const params = new URLSearchParams({ format });
        if (memType) params.append("type", memType);
        if (project) params.append("project", project);

        const result = await apiCall<unknown>(
          `/export/memories?${params.toString()}`
        );

        const exportStr =
          typeof result === "string"
            ? result
            : JSON.stringify(result, null, 2).substring(0, 5000);

        return {
          content: [
            {
              type: "text",
              text: `Export (${format}):\n\n${exportStr}${
                exportStr.length >= 5000 ? "\n\n... (truncated)" : ""
              }`,
            },
          ],
        };
      }

      // === Brain Intelligence Tools ===
      case "brain_dream": {
        const { duration = 30 } = args as { duration?: number };

        const result = await apiCall<{
          replayed: number;
          connections_found: number;
          duration_seconds: number;
        }>(`/brain/dream?duration=${duration}`, { method: "POST" });

        return {
          content: [
            {
              type: "text",
              text:
                `Dream mode complete:\n\n` +
                `Memories replayed: ${result.replayed}\n` +
                `Connections found: ${result.connections_found}\n` +
                `Duration: ${result.duration_seconds}s`,
            },
          ],
        };
      }

      case "brain_detect_conflicts": {
        const { limit = 50 } = args as { limit?: number };

        const result = await apiCall<{
          success: boolean;
          conflicts_detected: number;
          conflicts_resolved: number;
        }>(`/brain/detect-conflicts?limit=${limit}`, { method: "POST" });

        return {
          content: [
            {
              type: "text",
              text:
                `Conflict detection complete:\n\n` +
                `Conflicts detected: ${result.conflicts_detected}\n` +
                `Conflicts resolved: ${result.conflicts_resolved}`,
            },
          ],
        };
      }

      case "brain_replay": {
        const { count = 10, importance_threshold = 0.5 } = args as {
          count?: number;
          importance_threshold?: number;
        };

        const result = await apiCall<{
          replayed: number;
          strengthened: number;
        }>(
          `/brain/replay?count=${count}&importance_threshold=${importance_threshold}`,
          { method: "POST" }
        );

        return {
          content: [
            {
              type: "text",
              text:
                `Memory replay complete:\n\n` +
                `Replayed: ${result.replayed}\n` +
                `Strengthened: ${result.strengthened ?? result.replayed}`,
            },
          ],
        };
      }

      case "run_inference": {
        const { inference_type = "all" } = args as {
          inference_type?: string;
        };

        const result = await apiCall<Record<string, unknown>>(
          `/inference/run?inference_type=${inference_type}`,
          { method: "POST" }
        );

        const summary = Object.entries(result)
          .filter(([k]) => k !== "inference_type")
          .map(([k, v]) => `  ${k}: ${JSON.stringify(v)}`)
          .join("\n");

        return {
          content: [
            {
              type: "text",
              text: `Relationship inference (${inference_type}):\n\n${summary}`,
            },
          ],
        };
      }

      // === Temporal & Analytics Tools ===
      case "temporal_query": {
        const { target_time, project, limit = 50 } = args as {
          target_time: string;
          project?: string;
          limit?: number;
        };

        const params = new URLSearchParams({
          target_time,
          limit: String(limit),
        });
        if (project) params.append("project", project);

        const result = await apiCall<{
          target_time: string;
          memories: Array<{
            id: string;
            type: string;
            content: string;
            created_at: string;
          }>;
          count: number;
        }>(`/temporal/valid-at?${params.toString()}`);

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No memories were valid at ${target_time}`,
              },
            ],
          };
        }

        const formatted = result.memories
          .map(
            (m, i) =>
              `${i + 1}. [${m.type}] ${m.content.substring(0, 200)}`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Memories valid at ${target_time} (${result.count}):\n\n${formatted}`,
            },
          ],
        };
      }

      case "error_trends": {
        const { time_window_days = 30, min_cluster_size = 2 } = args as {
          time_window_days?: number;
          min_cluster_size?: number;
        };

        const result = await apiCall<{
          clusters: Array<{ tags: string[]; count: number }>;
          spikes: Array<{ date: string; count: number }>;
          recurring: Array<{
            error_message: string;
            occurrences: number;
          }>;
          time_window_days: number;
        }>(
          `/analytics/error-trends?time_window_days=${time_window_days}&min_cluster_size=${min_cluster_size}`
        );

        let text = `Error Trends (last ${result.time_window_days} days):\n\n`;

        if (result.clusters?.length > 0) {
          text += `Clusters:\n`;
          text += result.clusters
            .map((c) => `  [${c.tags.join(", ")}]: ${c.count} errors`)
            .join("\n");
          text += "\n\n";
        }

        if (result.recurring?.length > 0) {
          text += `Recurring:\n`;
          text += result.recurring
            .map(
              (r) => `  "${r.error_message}" (${r.occurrences}x)`
            )
            .join("\n");
          text += "\n\n";
        }

        if (result.spikes?.length > 0) {
          text += `Spikes:\n`;
          text += result.spikes
            .map((s) => `  ${s.date}: ${s.count} errors`)
            .join("\n");
        }

        return {
          content: [{ type: "text", text }],
        };
      }

      case "knowledge_gaps": {
        const result = await apiCall<{
          errors_without_patterns: unknown[];
          low_documentation_projects: unknown[];
        }>("/analytics/knowledge-gaps");

        let text = `Knowledge Gap Analysis:\n\n`;

        const errGaps = result.errors_without_patterns || [];
        text += `Errors without patterns: ${errGaps.length}\n`;
        if (errGaps.length > 0) {
          text += errGaps
            .slice(0, 10)
            .map((e: unknown) => `  - ${JSON.stringify(e).substring(0, 120)}`)
            .join("\n");
          text += "\n\n";
        }

        const lowDocs = result.low_documentation_projects || [];
        text += `Low documentation projects: ${lowDocs.length}\n`;
        if (lowDocs.length > 0) {
          text += lowDocs
            .slice(0, 10)
            .map((p: unknown) => `  - ${JSON.stringify(p).substring(0, 120)}`)
            .join("\n");
        }

        return {
          content: [{ type: "text", text }],
        };
      }

      case "query_enhance": {
        const {
          query,
          expand_synonyms = true,
          correct_typos = true,
        } = args as {
          query: string;
          expand_synonyms?: boolean;
          correct_typos?: boolean;
        };

        const result = await apiCall<{
          original_query: string;
          enhanced_query: string;
          corrections: Array<{ original: string; suggestion: string }>;
          expansions: string[];
        }>(
          `/query/enhance?query=${encodeURIComponent(query)}&expand_synonyms=${expand_synonyms}&correct_typos=${correct_typos}`,
          { method: "POST" }
        );

        let text = `Query Enhancement:\n\n`;
        text += `Original: "${result.original_query}"\n`;
        text += `Enhanced: "${result.enhanced_query}"\n`;

        if (result.corrections?.length > 0) {
          text += `\nCorrections:\n`;
          text += result.corrections
            .map((c) => `  "${c.original}" → "${c.suggestion}"`)
            .join("\n");
        }

        if (result.expansions?.length > 0) {
          text += `\nExpansions: ${result.expansions.join(", ")}`;
        }

        return {
          content: [{ type: "text", text }],
        };
      }

      // === Session Management Tools ===
      case "new_session": {
        const { project } = args as { project?: string };

        const params = project ? `?project=${encodeURIComponent(project)}` : "";
        const result = await apiCall<{
          session_id: string;
          project: string | null;
          created_at: string;
        }>(`/sessions/new${params}`, { method: "POST" });

        return {
          content: [
            {
              type: "text",
              text:
                `New session created:\n\n` +
                `Session ID: ${result.session_id}\n` +
                `Project: ${result.project || "none"}\n` +
                `Created: ${result.created_at}`,
            },
          ],
        };
      }

      case "consolidate_session": {
        const { session_id } = args as { session_id: string };

        const result = await apiCall<{
          session_id: string;
          summary_memory_id: string;
          links_created: number;
        }>(`/sessions/${session_id}/consolidate`, { method: "POST" });

        return {
          content: [
            {
              type: "text",
              text:
                `Session consolidated:\n\n` +
                `Session: ${result.session_id}\n` +
                `Summary memory: ${result.summary_memory_id}\n` +
                `Links created: ${result.links_created}`,
            },
          ],
        };
      }

      // === Graph Enhancement Tools ===
      case "graph_contradictions": {
        const { limit = 50 } = args as { limit?: number };

        const result = await apiCall<{
          contradictions: Array<{
            memory_a_id: string;
            memory_a_preview: string;
            memory_b_id: string;
            memory_b_preview: string;
            pattern: string;
          }>;
          count: number;
        }>(`/graph/contradictions?limit=${limit}`);

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No contradictions found in the knowledge graph.",
              },
            ],
          };
        }

        const formatted = result.contradictions
          .map(
            (c, i) =>
              `${i + 1}. ${c.pattern}\n` +
              `   A: [${c.memory_a_id}] ${c.memory_a_preview}\n` +
              `   B: [${c.memory_b_id}] ${c.memory_b_preview}`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Contradictions found (${result.count}):\n\n${formatted}`,
            },
          ],
        };
      }

      case "graph_recommendations": {
        const { memory_id, limit = 10 } = args as {
          memory_id: string;
          limit?: number;
        };

        const result = await apiCall<{
          memory_id: string;
          recommendations: Array<{
            id: string;
            type: string;
            preview: string;
            shared_connections: number;
            reasoning: string[];
          }>;
          count: number;
        }>(`/graph/recommendations/${memory_id}?limit=${limit}`);

        if (result.count === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No recommendations found for memory ${memory_id}`,
              },
            ],
          };
        }

        const formatted = result.recommendations
          .map(
            (r, i) =>
              `${i + 1}. [${r.type}] ${r.preview}\n` +
              `   ID: ${r.id}\n` +
              `   Shared connections: ${r.shared_connections}\n` +
              `   Via: ${r.reasoning.join(", ")}`
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Recommendations for ${memory_id} (${result.count}):\n\n${formatted}`,
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      content: [
        {
          type: "text",
          text: `Error: ${message}`,
        },
      ],
      isError: true,
    };
  }
});

// Resource Definitions
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  return {
    resources: [
      {
        uri: "memory://recent",
        name: "Recent Memories",
        description: "Memories from the last 24 hours",
        mimeType: "text/plain",
      },
      {
        uri: "memory://errors/unresolved",
        name: "Unresolved Errors",
        description: "Error memories that haven't been resolved",
        mimeType: "text/plain",
      },
      {
        uri: "memory://graph/overview",
        name: "Knowledge Graph Overview",
        description: "Overview of the knowledge graph structure",
        mimeType: "text/plain",
      },
    ],
  };
});

// Resource Handlers
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const { uri } = request.params;

  try {
    if (uri === "memory://recent") {
      const memories = await apiCall<Memory[]>("/context/_all?hours=24");
      const formatted = memories
        .map((m) => `[${m.type}] ${m.content}`)
        .join("\n\n");
      return {
        contents: [
          {
            uri,
            mimeType: "text/plain",
            text: formatted || "No recent memories.",
          },
        ],
      };
    }

    if (uri === "memory://errors/unresolved") {
      const results = await apiCall<SearchResult[]>("/memories/search", {
        method: "POST",
        body: JSON.stringify({
          query: "error",
          type: "error",
          limit: 50,
        }),
      });
      const unresolved = results.filter((r) => !r.memory.resolved);
      const formatted = unresolved
        .map(
          (r) =>
            `[${r.memory.id}] ${r.memory.error_message || r.memory.content}`
        )
        .join("\n\n");
      return {
        contents: [
          {
            uri,
            mimeType: "text/plain",
            text: formatted || "No unresolved errors.",
          },
        ],
      };
    }

    if (uri === "memory://graph/overview") {
      const stats = await apiCall<GraphStats>("/graph/stats");
      const memStats = await apiCall<{
        total_memories: number;
        by_type: Record<string, number>;
      }>("/stats");

      let text = `Memory System Overview\n${"=".repeat(40)}\n\n`;
      text += `Total Memories: ${memStats.total_memories}\n`;
      text += `By Type: ${Object.entries(memStats.by_type)
        .map(([t, c]) => `${t}(${c})`)
        .join(", ")}\n\n`;

      if (stats.enabled) {
        text += `Knowledge Graph\n${"-".repeat(20)}\n`;
        text += `Memory Nodes: ${stats.memory_nodes}\n`;
        text += `Projects: ${stats.project_nodes}\n`;
        text += `Tags: ${stats.tag_nodes}\n`;
        text += `Relationships: ${stats.relationships}\n`;
      } else {
        text += `Knowledge Graph: Not available\n`;
      }

      return {
        contents: [
          {
            uri,
            mimeType: "text/plain",
            text,
          },
        ],
      };
    }

    throw new Error(`Unknown resource: ${uri}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to read resource: ${message}`);
  }
});

// Start Server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Claude Memory MCP Server v2.0 running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
