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

// Configuration
const MEMORY_SERVICE_URL = process.env.MEMORY_SERVICE_URL || "http://localhost:8100";

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
        const memory = await apiCall<Memory>("/memories", {
          method: "POST",
          body: JSON.stringify(args),
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

        const memories = await apiCall<Memory[]>(
          `/context/${project}?${params.toString()}`
        );

        if (memories.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No recent context memories found.",
              },
            ],
          };
        }

        const formatted = memories
          .map(
            (m) =>
              `[${m.type}] ${m.content}` +
              (m.solution ? `\n  → Solution: ${m.solution}` : "") +
              (m.resolved === false && m.type === "error" ? " (UNRESOLVED)" : "")
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Recent context (last ${hours}h):\n\n${formatted}`,
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
          }>;
        };

        const results = await Promise.all(
          memories.map((m) =>
            apiCall<Memory>("/memories", {
              method: "POST",
              body: JSON.stringify(m),
            })
          )
        );

        return {
          content: [
            {
              type: "text",
              text: `Stored ${results.length} memories:\n\n${results
                .map((m) => `- ${m.id} (${m.type})`)
                .join("\n")}`,
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
