#!/usr/bin/env python3
"""
Multi-Query Search
Executes multiple search strategies in parallel and merges results
Improves recall by trying different approaches simultaneously
"""

import requests
import json
from typing import List, Dict, Set
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

MEMORY_API = "http://localhost:8100"

def search_semantic(query: str, limit: int = 10) -> List[Dict]:
    """Semantic search using vector similarity."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": query,
            "limit": limit
        })
        response.raise_for_status()
        results = response.json().get("results", [])
        # Tag results with search strategy
        for r in results:
            r["_strategy"] = "semantic"
        return results
    except Exception as e:
        print(f"⚠️  Semantic search failed: {e}")
        return []

def search_by_type(query: str, mem_type: str, limit: int = 10) -> List[Dict]:
    """Search within a specific memory type."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": query,
            "type": mem_type,
            "limit": limit
        })
        response.raise_for_status()
        results = response.json().get("results", [])
        for r in results:
            r["_strategy"] = f"type:{mem_type}"
        return results
    except Exception as e:
        print(f"⚠️  Type search ({mem_type}) failed: {e}")
        return []

def search_by_tags(tags: List[str], limit: int = 10) -> List[Dict]:
    """Search by tags."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": " ".join(tags),
            "tags": tags,
            "limit": limit
        })
        response.raise_for_status()
        results = response.json().get("results", [])
        for r in results:
            r["_strategy"] = "tags"
        return results
    except Exception as e:
        print(f"⚠️  Tag search failed: {e}")
        return []

def search_by_project(query: str, project: str, limit: int = 10) -> List[Dict]:
    """Search within a specific project."""
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": query,
            "project": project,
            "limit": limit
        })
        response.raise_for_status()
        results = response.json().get("results", [])
        for r in results:
            r["_strategy"] = f"project:{project}"
        return results
    except Exception as e:
        print(f"⚠️  Project search failed: {e}")
        return []

def search_expanded_query(query: str, limit: int = 10) -> List[Dict]:
    """Search with expanded synonyms and related terms."""
    # Expand query with common synonyms
    expansions = {
        "bug": "bug error issue problem defect",
        "fix": "fix solution resolve patch repair",
        "api": "api endpoint rest graphql service",
        "auth": "auth authentication login oauth jwt",
        "test": "test testing spec e2e unit integration",
        "deploy": "deploy deployment ci-cd docker kubernetes"
    }

    expanded_query = query
    for key, expansion in expansions.items():
        if key in query.lower():
            expanded_query += " " + expansion

    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": expanded_query,
            "limit": limit
        })
        response.raise_for_status()
        results = response.json().get("results", [])
        for r in results:
            r["_strategy"] = "expanded"
        return results
    except Exception as e:
        print(f"⚠️  Expanded search failed: {e}")
        return []

def merge_and_deduplicate(results_list: List[List[Dict]]) -> List[Dict]:
    """Merge results from multiple searches and remove duplicates."""
    seen_ids = set()
    merged = []

    # Flatten all results
    all_results = []
    for results in results_list:
        all_results.extend(results)

    # Sort by score (descending)
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Deduplicate while preserving order
    for result in all_results:
        mem_id = result.get("id")
        if mem_id and mem_id not in seen_ids:
            seen_ids.add(mem_id)
            merged.append(result)

    return merged

def multi_query_search(query: str, strategies: List[str] = None, limit: int = 10) -> Dict:
    """Execute multiple search strategies in parallel."""
    if strategies is None:
        strategies = ["semantic", "type:error", "type:decision", "type:pattern", "expanded"]

    print(f"🔍 Executing {len(strategies)} search strategies in parallel...")

    # Execute searches in parallel
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}

        for strategy in strategies:
            if strategy == "semantic":
                future = executor.submit(search_semantic, query, limit)
                futures[future] = strategy

            elif strategy.startswith("type:"):
                mem_type = strategy.split(":")[1]
                future = executor.submit(search_by_type, query, mem_type, limit)
                futures[future] = strategy

            elif strategy == "expanded":
                future = executor.submit(search_expanded_query, query, limit)
                futures[future] = strategy

            elif strategy.startswith("project:"):
                project = strategy.split(":")[1]
                future = executor.submit(search_by_project, query, project, limit)
                futures[future] = strategy

            elif strategy.startswith("tags:"):
                tags = strategy.split(":")[1].split(",")
                future = executor.submit(search_by_tags, tags, limit)
                futures[future] = strategy

        # Collect results
        results_by_strategy = {}
        for future in as_completed(futures):
            strategy_name = futures[future]
            try:
                results = future.result()
                results_by_strategy[strategy_name] = results
                print(f"  ✅ {strategy_name}: {len(results)} results")
            except Exception as e:
                print(f"  ❌ {strategy_name}: failed ({e})")
                results_by_strategy[strategy_name] = []

    # Merge and deduplicate
    all_results = list(results_by_strategy.values())
    merged_results = merge_and_deduplicate(all_results)

    # Calculate strategy coverage
    strategy_hits = {}
    for mem in merged_results:
        strat = mem.get("_strategy", "unknown")
        strategy_hits[strat] = strategy_hits.get(strat, 0) + 1

    return {
        "query": query,
        "strategies_used": strategies,
        "results_by_strategy": {k: len(v) for k, v in results_by_strategy.items()},
        "merged_results": merged_results,
        "total_unique": len(merged_results),
        "strategy_hits": strategy_hits
    }

def display_results(search_results: Dict, max_display: int = 10):
    """Display search results in a readable format."""
    print("\n" + "═" * 60)
    print(f"📊 MULTI-QUERY SEARCH RESULTS")
    print("═" * 60)

    print(f"\nQuery: \"{search_results['query']}\"")
    print(f"Strategies: {len(search_results['strategies_used'])}")
    print(f"Total unique results: {search_results['total_unique']}")

    print("\n" + "─" * 60)
    print("📈 RESULTS BY STRATEGY")
    print("─" * 60)

    for strategy, count in search_results["results_by_strategy"].items():
        print(f"  {strategy:20} {count:3} results")

    print("\n" + "─" * 60)
    print("🎯 STRATEGY EFFECTIVENESS")
    print("─" * 60)

    for strategy, count in sorted(search_results["strategy_hits"].items(), key=lambda x: x[1], reverse=True):
        print(f"  {strategy:20} contributed {count} unique results")

    print("\n" + "─" * 60)
    print(f"🔝 TOP {min(max_display, len(search_results['merged_results']))} RESULTS")
    print("─" * 60)

    for i, mem in enumerate(search_results["merged_results"][:max_display], 1):
        mem_id = mem.get("id", "")[:8]
        mem_type = mem.get("type", "unknown")
        score = mem.get("score", 0)
        strategy = mem.get("_strategy", "unknown")
        content = mem.get("content", "")[:60]

        print(f"\n{i}. [{mem_id}] ({mem_type}) - Score: {score:.3f}")
        print(f"   Strategy: {strategy}")
        print(f"   {content}...")

        # Show tags
        tags = mem.get("tags", [])
        if tags:
            print(f"   Tags: {', '.join(tags[:5])}")

def main():
    """Main multi-query search workflow."""
    print("🔍 Multi-Query Search")
    print("═" * 60)

    # Check service
    try:
        response = requests.get(f"{MEMORY_API}/health")
        response.raise_for_status()
        print("✅ Memory service is running\n")
    except Exception as e:
        print(f"❌ Memory service not available: {e}")
        sys.exit(1)

    # Get query from arguments
    if len(sys.argv) < 2:
        print("Usage: python3 multi-query-search.py <query> [strategies...]")
        print("\nStrategies (optional):")
        print("  semantic         - Vector similarity search (default)")
        print("  type:error       - Search errors only")
        print("  type:decision    - Search decisions only")
        print("  type:pattern     - Search patterns only")
        print("  type:docs        - Search docs only")
        print("  expanded         - Expanded with synonyms")
        print("  project:<name>   - Search specific project")
        print("  tags:<tag1,tag2> - Search by tags")
        print("\nExamples:")
        print("  python3 multi-query-search.py 'authentication bug'")
        print("  python3 multi-query-search.py 'api design' semantic type:decision expanded")
        print("  python3 multi-query-search.py 'database' project:myapp")
        sys.exit(0)

    query = sys.argv[1]
    strategies = sys.argv[2:] if len(sys.argv) > 2 else None

    print(f"📝 Query: \"{query}\"")
    if strategies:
        print(f"🎯 Strategies: {', '.join(strategies)}")
    else:
        print(f"🎯 Strategies: default (semantic + type searches + expanded)")

    print("")

    # Execute multi-query search
    results = multi_query_search(query, strategies)

    # Display results
    display_results(results)

    print("\n" + "═" * 60)
    print("💡 Tip: Narrow results with specific strategies")
    print("   Example: multi-query-search.py 'query' type:error project:myapp")
    print("═" * 60)

if __name__ == "__main__":
    main()
