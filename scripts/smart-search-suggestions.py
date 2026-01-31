#!/usr/bin/env python3
"""
Smart Search Suggestions
Analyzes user queries and suggests better search terms based on memory content
Learns from successful searches to improve future suggestions
"""

import requests
import json
from typing import List, Dict, Set
import sys
from collections import Counter
import re

MEMORY_API = "http://localhost:8100"

def extract_keywords(text: str) -> List[str]:
    """Extract meaningful keywords from text."""
    # Remove common stop words
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
        "be", "have", "has", "had", "do", "does", "did", "will", "would", "should",
        "could", "can", "may", "might", "must", "this", "that", "these", "those",
        "i", "you", "he", "she", "it", "we", "they", "what", "which", "who",
        "when", "where", "why", "how"
    }

    # Tokenize and clean
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]

    return keywords

def get_all_tags() -> Set[str]:
    """Get all unique tags from the memory system."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 500
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        all_tags = set()
        for mem in memories:
            all_tags.update(mem.get("tags", []))

        return all_tags
    except Exception as e:
        return set()

def get_common_terms() -> Dict[str, int]:
    """Get most common terms from memory content."""
    try:
        response = requests.get(f"{MEMORY_API}/memories/timeline", params={
            "limit": 500
        })
        response.raise_for_status()
        memories = response.json().get("memories", [])

        # Extract all keywords from content
        all_keywords = []
        for mem in memories:
            content = mem.get("content", "")
            all_keywords.extend(extract_keywords(content))

        # Count frequencies
        term_counts = Counter(all_keywords)

        return dict(term_counts.most_common(100))
    except Exception as e:
        return {}

def suggest_tags(query: str, existing_tags: Set[str]) -> List[str]:
    """Suggest relevant tags based on query."""
    query_lower = query.lower()
    query_words = set(extract_keywords(query))

    # Find tags that match query words
    matching_tags = []
    for tag in existing_tags:
        tag_words = set(tag.split("-"))
        # Tag matches if any word overlaps with query
        if query_words & tag_words:
            matching_tags.append(tag)
        # Or if tag is substring of query or vice versa
        elif tag in query_lower or query_lower in tag:
            matching_tags.append(tag)

    return matching_tags[:5]  # Top 5 suggestions

def suggest_synonyms(query: str, common_terms: Dict[str, int]) -> List[str]:
    """Suggest related terms that might improve search."""
    # Common technical synonyms
    synonym_map = {
        "bug": ["error", "issue", "problem", "defect"],
        "fix": ["solution", "resolve", "patch", "repair"],
        "api": ["endpoint", "rest", "graphql", "service"],
        "database": ["db", "sql", "postgres", "mysql", "mongo"],
        "frontend": ["ui", "react", "vue", "angular", "component"],
        "backend": ["server", "api", "service", "microservice"],
        "auth": ["authentication", "login", "oauth", "jwt", "session"],
        "test": ["testing", "spec", "e2e", "unit", "integration"],
        "deploy": ["deployment", "ci-cd", "docker", "kubernetes"],
        "optimize": ["performance", "speed", "cache", "bottleneck"]
    }

    suggestions = []
    query_words = extract_keywords(query)

    for word in query_words:
        if word in synonym_map:
            # Suggest synonyms that exist in memory content
            for syn in synonym_map[word]:
                if syn in common_terms:
                    suggestions.append(syn)

    return list(set(suggestions))[:5]

def suggest_query_improvements(query: str) -> Dict:
    """Generate improved query suggestions."""
    # Get existing tags and common terms
    existing_tags = get_all_tags()
    common_terms = get_common_terms()

    # Extract keywords from query
    keywords = extract_keywords(query)

    # Generate suggestions
    suggestions = {
        "original_query": query,
        "extracted_keywords": keywords,
        "suggested_tags": suggest_tags(query, existing_tags),
        "related_terms": suggest_synonyms(query, common_terms),
        "improved_queries": []
    }

    # Generate improved query variations
    improved = []

    # 1. Query + suggested tags
    if suggestions["suggested_tags"]:
        tag_query = query + " " + " ".join(suggestions["suggested_tags"])
        improved.append({
            "query": tag_query,
            "reason": "Added relevant tags from memory system"
        })

    # 2. Query + related terms
    if suggestions["related_terms"]:
        term_query = query + " " + " ".join(suggestions["related_terms"])
        improved.append({
            "query": term_query,
            "reason": "Added related technical terms"
        })

    # 3. Expanded keyword query
    if len(keywords) > 0:
        expanded = " ".join(keywords + suggestions.get("related_terms", [])[:2])
        improved.append({
            "query": expanded,
            "reason": "Expanded with related concepts"
        })

    # 4. Tag-only query
    if suggestions["suggested_tags"]:
        tag_only = " ".join(suggestions["suggested_tags"])
        improved.append({
            "query": tag_only,
            "reason": "Tag-based search for precise results"
        })

    suggestions["improved_queries"] = improved

    return suggestions

def test_query_suggestions(original_query: str, suggestions: Dict) -> Dict:
    """Test suggested queries and compare results."""
    results = {
        "original": None,
        "improved": []
    }

    # Test original query
    try:
        response = requests.post(f"{MEMORY_API}/memories/search", json={
            "query": original_query,
            "limit": 5
        })
        response.raise_for_status()
        original_results = response.json().get("results", [])
        results["original"] = {
            "count": len(original_results),
            "top_score": original_results[0].get("score", 0) if original_results else 0
        }
    except:
        pass

    # Test improved queries
    for improved in suggestions.get("improved_queries", []):
        try:
            response = requests.post(f"{MEMORY_API}/memories/search", json={
                "query": improved["query"],
                "limit": 5
            })
            response.raise_for_status()
            improved_results = response.json().get("results", [])

            results["improved"].append({
                "query": improved["query"],
                "reason": improved["reason"],
                "count": len(improved_results),
                "top_score": improved_results[0].get("score", 0) if improved_results else 0,
                "improvement": len(improved_results) > results["original"]["count"] if results["original"] else False
            })
        except:
            pass

    return results

def main():
    """Main smart suggestion workflow."""
    print("🔍 Smart Search Suggestions")
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
        print("Usage: python3 smart-search-suggestions.py <search-query>")
        print("\nExample:")
        print("  python3 smart-search-suggestions.py 'authentication bug'")
        sys.exit(0)

    query = " ".join(sys.argv[1:])
    print(f"📝 Original Query: \"{query}\"\n")

    # Generate suggestions
    print("🤖 Analyzing query and generating suggestions...")
    suggestions = suggest_query_improvements(query)

    # Display suggestions
    print("\n" + "─" * 60)
    print("📊 ANALYSIS")
    print("─" * 60)

    print(f"\nExtracted Keywords:")
    print(f"  {', '.join(suggestions['extracted_keywords']) if suggestions['extracted_keywords'] else 'None'}")

    print(f"\nSuggested Tags:")
    print(f"  {', '.join(suggestions['suggested_tags']) if suggestions['suggested_tags'] else 'None found'}")

    print(f"\nRelated Terms:")
    print(f"  {', '.join(suggestions['related_terms']) if suggestions['related_terms'] else 'None found'}")

    # Display improved queries
    print("\n" + "─" * 60)
    print("💡 IMPROVED QUERY SUGGESTIONS")
    print("─" * 60)

    if suggestions["improved_queries"]:
        for i, improved in enumerate(suggestions["improved_queries"], 1):
            print(f"\n{i}. \"{improved['query']}\"")
            print(f"   Reason: {improved['reason']}")
    else:
        print("\nNo improvements suggested - original query is good!")

    # Test queries and compare results
    print("\n" + "─" * 60)
    print("🧪 TESTING QUERY PERFORMANCE")
    print("─" * 60)

    test_results = test_query_suggestions(query, suggestions)

    if test_results["original"]:
        print(f"\nOriginal Query Results:")
        print(f"  Memories found: {test_results['original']['count']}")
        print(f"  Top score: {test_results['original']['top_score']:.3f}")

    if test_results["improved"]:
        print(f"\nImproved Query Results:")
        for result in test_results["improved"]:
            status = "✅ BETTER" if result["improvement"] else "⚠️  SIMILAR"
            print(f"\n  {status} \"{result['query'][:50]}...\"")
            print(f"    Memories: {result['count']} | Top score: {result['top_score']:.3f}")
            print(f"    {result['reason']}")

    print("\n" + "═" * 60)
    print("💡 Tip: Try the improved queries with search_memory()")
    print("═" * 60)

if __name__ == "__main__":
    main()
