"""Query understanding and routing pipeline.

Analyzes queries to determine optimal search strategy:
- Temporal queries → time-based filtering
- Relationship queries → graph traversal
- Exact match → sparse-only search
- Conceptual → semantic search with reranking
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class QueryIntent(Enum):
    """Query intent types for routing."""
    TEMPORAL = "temporal"          # Time-based queries
    RELATIONSHIP = "relationship"  # Graph relationship queries
    EXACT_MATCH = "exact_match"    # Exact string/code matching
    CONCEPTUAL = "conceptual"      # Semantic understanding needed
    COMPOSITE = "composite"        # Multiple intents


class TimeRange:
    """Represents a time range for temporal queries."""
    def __init__(self, start: Optional[datetime] = None, end: Optional[datetime] = None):
        self.start = start
        self.end = end

    def to_filter(self) -> Dict:
        """Convert to Qdrant filter format."""
        conditions = []
        if self.start:
            conditions.append({
                "key": "created_at",
                "range": {"gte": self.start.isoformat()}
            })
        if self.end:
            conditions.append({
                "key": "created_at",
                "range": {"lte": self.end.isoformat()}
            })
        return {"must": conditions} if conditions else {}


class QueryUnderstanding:
    """Analyzes queries and determines optimal search strategy."""

    # Temporal keywords
    TEMPORAL_KEYWORDS = {
        "recent", "last", "yesterday", "today", "week", "month",
        "latest", "newest", "oldest", "past", "ago", "since"
    }

    # Relationship keywords
    RELATIONSHIP_KEYWORDS = {
        "related to", "caused by", "fixes", "fixed by", "similar to",
        "connected to", "depends on", "blocks", "linked to"
    }

    # Exact match indicators
    EXACT_INDICATORS = {
        "quoted": r'"([^"]+)"',
        "code": r'`([^`]+)`',
        "uppercase": r'\b[A-Z_]{3,}\b',
        "error_code": r'\b(E[A-Z]+|[A-Z][a-z]+Error|\d{3,4})\b'
    }

    def __init__(self):
        self.intent_scores = {}

    def analyze(self, query: str) -> Tuple[QueryIntent, Dict]:
        """
        Analyze query and determine intent with context.

        Args:
            query: Search query text

        Returns:
            Tuple of (primary intent, context dict with routing hints)
        """
        query_lower = query.lower()
        context = {}

        # Detect temporal intent
        temporal_score = self._score_temporal(query_lower)
        time_range = self._extract_time_range(query_lower)
        if time_range:
            context["time_range"] = time_range

        # Detect relationship intent
        relationship_score = self._score_relationship(query_lower)
        if relationship_score > 0:
            context["entities"] = self._extract_entities(query)

        # Detect exact match intent
        exact_score = self._score_exact_match(query)
        if exact_score > 0:
            context["exact_terms"] = self._extract_exact_terms(query)

        # Detect conceptual intent
        conceptual_score = self._score_conceptual(query_lower)

        # Store scores for debugging
        self.intent_scores = {
            "temporal": temporal_score,
            "relationship": relationship_score,
            "exact_match": exact_score,
            "conceptual": conceptual_score
        }

        # Determine primary intent
        intent = self._determine_primary_intent()
        context["scores"] = self.intent_scores

        logger.debug(
            f"Query intent: {intent.value} | "
            f"Scores: T={temporal_score:.2f} R={relationship_score:.2f} "
            f"E={exact_score:.2f} C={conceptual_score:.2f}"
        )

        return intent, context

    def _score_temporal(self, query: str) -> float:
        """Score temporal intent (0-1)."""
        score = 0.0

        # Check for temporal keywords
        for keyword in self.TEMPORAL_KEYWORDS:
            if keyword in query:
                score += 0.3

        # Check for time expressions
        time_patterns = [
            r'\b\d+\s+(day|week|month|year)s?\s+ago\b',
            r'\blast\s+(day|week|month|year)\b',
            r'\bpast\s+\d+\s+(day|week|month|year)s?\b'
        ]
        for pattern in time_patterns:
            if re.search(pattern, query):
                score += 0.5

        return min(score, 1.0)

    def _score_relationship(self, query: str) -> float:
        """Score relationship intent (0-1)."""
        score = 0.0

        for keyword in self.RELATIONSHIP_KEYWORDS:
            if keyword in query:
                score += 0.5

        return min(score, 1.0)

    def _score_exact_match(self, query: str) -> float:
        """Score exact match intent (0-1)."""
        score = 0.0

        for indicator_name, pattern in self.EXACT_INDICATORS.items():
            if re.search(pattern, query):
                score += 0.4

        # Short queries without question words
        if len(query.split()) <= 2 and not any(
            word in query.lower() for word in ["how", "why", "what", "when"]
        ):
            score += 0.3

        return min(score, 1.0)

    def _score_conceptual(self, query: str) -> float:
        """Score conceptual intent (0-1)."""
        score = 0.0

        # Question words indicate conceptual
        question_words = ["how", "why", "what", "when", "where", "explain", "describe"]
        if any(word in query for word in question_words):
            score += 0.5

        # Long queries
        if len(query.split()) >= 6:
            score += 0.3

        # Analytical language
        analytical_patterns = [
            r'\b(optimize|improve|better|best|difference|compare)\b',
            r'\b(pattern|approach|strategy|design|architecture)\b'
        ]
        for pattern in analytical_patterns:
            if re.search(pattern, query):
                score += 0.3

        return min(score, 1.0)

    def _determine_primary_intent(self) -> QueryIntent:
        """Determine primary intent from scores."""
        scores = self.intent_scores

        # High exact match score dominates
        if scores["exact_match"] > 0.7:
            return QueryIntent.EXACT_MATCH

        # High relationship score
        if scores["relationship"] > 0.6:
            return QueryIntent.RELATIONSHIP

        # High temporal score
        if scores["temporal"] > 0.6:
            return QueryIntent.TEMPORAL

        # Multiple high scores = composite
        high_scores = sum(1 for s in scores.values() if s > 0.5)
        if high_scores >= 2:
            return QueryIntent.COMPOSITE

        # Default to conceptual
        return QueryIntent.CONCEPTUAL

    def _extract_time_range(self, query: str) -> Optional[TimeRange]:
        """Extract time range from temporal queries."""
        now = datetime.now()

        # "last week", "past 7 days", etc.
        patterns = [
            (r'last\s+(\d+)\s+days?', lambda m: timedelta(days=int(m.group(1)))),
            (r'last\s+(\d+)\s+weeks?', lambda m: timedelta(weeks=int(m.group(1)))),
            (r'last\s+(\d+)\s+months?', lambda m: timedelta(days=int(m.group(1)) * 30)),
            (r'last\s+week', lambda m: timedelta(weeks=1)),
            (r'last\s+month', lambda m: timedelta(days=30)),
            (r'yesterday', lambda m: timedelta(days=1)),
            (r'today', lambda m: timedelta(days=0)),
        ]

        for pattern, delta_fn in patterns:
            match = re.search(pattern, query)
            if match:
                delta = delta_fn(match)
                return TimeRange(start=now - delta, end=now)

        return None

    def _extract_entities(self, query: str) -> List[str]:
        """Extract entity references for relationship queries."""
        # Simple extraction - look for quoted strings or capitalized terms
        entities = []

        # Quoted entities
        quoted = re.findall(r'"([^"]+)"', query)
        entities.extend(quoted)

        # Capitalized terms (potential entities)
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', query)
        entities.extend(capitalized)

        return list(set(entities))

    def _extract_exact_terms(self, query: str) -> List[str]:
        """Extract exact match terms."""
        terms = []

        # Quoted strings
        quoted = re.findall(r'"([^"]+)"', query)
        terms.extend(quoted)

        # Code backticks
        code = re.findall(r'`([^`]+)`', query)
        terms.extend(code)

        # Error codes and constants
        error_codes = re.findall(r'\b([A-Z_]{3,}|E[A-Z]+|[A-Z][a-z]+Error)\b', query)
        terms.extend(error_codes)

        return list(set(terms))


def route_query(query: str) -> Dict:
    """
    Determine optimal search strategy for a query.

    Args:
        query: Search query text

    Returns:
        Dict with routing instructions:
        - strategy: "sparse_only", "hybrid", "graph_expansion", "semantic"
        - rerank: bool
        - filters: dict of additional filters
        - boost_recent: bool
    """
    understanding = QueryUnderstanding()
    intent, context = understanding.analyze(query)

    routing = {
        "strategy": "hybrid",
        "rerank": True,
        "filters": {},
        "boost_recent": False
    }

    # Route based on intent
    if intent == QueryIntent.EXACT_MATCH:
        routing["strategy"] = "sparse_only"
        routing["rerank"] = False
        if "exact_terms" in context:
            logger.debug(f"Exact match terms: {context['exact_terms']}")

    elif intent == QueryIntent.TEMPORAL:
        routing["strategy"] = "hybrid"
        routing["rerank"] = True
        routing["boost_recent"] = True
        if "time_range" in context:
            routing["filters"] = context["time_range"].to_filter()

    elif intent == QueryIntent.RELATIONSHIP:
        routing["strategy"] = "graph_expansion"
        routing["rerank"] = True
        if "entities" in context:
            logger.debug(f"Relationship entities: {context['entities']}")

    elif intent == QueryIntent.CONCEPTUAL:
        routing["strategy"] = "semantic"
        routing["rerank"] = True

    elif intent == QueryIntent.COMPOSITE:
        routing["strategy"] = "hybrid"
        routing["rerank"] = True
        routing["boost_recent"] = context.get("time_range") is not None

    logger.info(
        f"Routing query '{query[:50]}...' → "
        f"{routing['strategy']} (intent: {intent.value})"
    )

    return routing


# Synonym map for query expansion
SYNONYM_MAP = {
    # Programming concepts
    "error": ["bug", "issue", "problem", "exception", "failure", "crash"],
    "fix": ["solve", "resolve", "repair", "correct", "patch"],
    "code": ["script", "program", "implementation", "source"],
    "function": ["method", "procedure", "routine", "subroutine"],
    "variable": ["var", "parameter", "argument", "field"],

    # Technologies - Containers & Infrastructure
    "docker": ["container", "image", "compose", "dockerfile", "containerization"],
    "kubernetes": ["k8s", "cluster", "pod", "deployment", "orchestration"],
    "container": ["docker", "image", "pod", "runtime"],

    # Technologies - Databases
    "database": ["db", "sql", "postgres", "mongodb", "mysql", "datastore"],
    "qdrant": ["vector-db", "vector-database", "similarity-search"],
    "neo4j": ["graph-db", "graph-database", "cypher"],
    "postgresql": ["postgres", "pg", "psql"],
    "mongodb": ["mongo", "nosql", "document-db"],

    # Technologies - APIs & Web
    "api": ["endpoint", "route", "service", "rest", "webservice"],
    "endpoint": ["api", "route", "url", "path"],
    "request": ["call", "invocation", "query"],
    "response": ["reply", "result", "return", "output"],

    # Technologies - Frontend
    "frontend": ["ui", "interface", "client", "browser"],
    "react": ["jsx", "component", "react-component"],
    "vue": ["vue-component", "template"],
    "angular": ["ng", "angular-component"],

    # Technologies - Backend
    "backend": ["server", "api", "service", "backend-service"],
    "server": ["backend", "host", "instance"],

    # Technologies - Cloud & DevOps
    "aws": ["amazon", "ec2", "s3", "lambda", "cloud"],
    "gcp": ["google-cloud", "bigquery", "cloud-run"],
    "azure": ["microsoft-cloud", "azurecloud"],
    "ci-cd": ["pipeline", "automation", "deployment", "continuous-integration"],

    # Technologies - AI/ML
    "ai": ["artificial-intelligence", "ml", "machine-learning", "neural-network"],
    "ml": ["machine-learning", "ai", "model", "training"],
    "llm": ["large-language-model", "gpt", "language-model"],

    # Operations
    "deploy": ["deployment", "release", "rollout", "push"],
    "test": ["testing", "unittest", "integration-test", "e2e"],
    "build": ["compile", "bundle", "package", "assemble"],
    "run": ["execute", "start", "launch", "invoke"],

    # Status & Quality
    "slow": ["sluggish", "performance", "latency", "delay"],
    "fast": ["quick", "performant", "optimized", "efficient"],
    "broken": ["failing", "error", "issue", "problem"],
    "working": ["functional", "operational", "running", "active"],
}


def expand_query_with_synonyms(query: str, max_synonyms: int = 2) -> str:
    """
    Expand query by adding synonyms for better recall.

    Args:
        query: Original search query
        max_synonyms: Maximum synonyms to add per word (default: 2)

    Returns:
        Expanded query with synonyms

    Example:
        >>> expand_query_with_synonyms("docker error")
        "docker error container bug exception"
    """
    words = query.lower().split()
    expanded = []

    for word in words:
        # Always include original word
        expanded.append(word)

        # Add synonyms if available
        if word in SYNONYM_MAP:
            synonyms = SYNONYM_MAP[word][:max_synonyms]
            expanded.extend(synonyms)

    expanded_query = " ".join(expanded)

    if expanded_query != query:
        logger.debug(f"Query expansion: '{query}' → '{expanded_query}'")

    return expanded_query


def estimate_typo_corrections(query: str, known_terms: Optional[List[str]] = None) -> List[Dict]:
    """
    Suggest corrections for potential typos using Levenshtein distance.

    Args:
        query: Search query to check for typos
        known_terms: List of known correct terms (default: use SYNONYM_MAP keys)

    Returns:
        List of correction suggestions: [{"original": str, "suggestion": str, "confidence": float}]

    Example:
        >>> estimate_typo_corrections("dcoker erro")
        [{"original": "dcoker", "suggestion": "docker", "confidence": 0.83},
         {"original": "erro", "suggestion": "error", "confidence": 0.75}]
    """
    from difflib import get_close_matches

    if known_terms is None:
        # Use SYNONYM_MAP keys and all synonym values as known terms
        known_terms = list(SYNONYM_MAP.keys())
        for synonyms in SYNONYM_MAP.values():
            known_terms.extend(synonyms)
        known_terms = list(set(known_terms))

    words = query.lower().split()
    corrections = []

    for word in words:
        # Skip very short words and known correct terms
        if len(word) <= 3 or word in known_terms:
            continue

        # Find close matches (cutoff=0.6 allows for reasonable typos)
        matches = get_close_matches(word, known_terms, n=1, cutoff=0.6)

        if matches and matches[0] != word:
            # Calculate simple confidence (inverse of edit distance)
            suggestion = matches[0]

            # Levenshtein distance approximation
            from difflib import SequenceMatcher
            confidence = SequenceMatcher(None, word, suggestion).ratio()

            corrections.append({
                "original": word,
                "suggestion": suggestion,
                "confidence": round(confidence, 2)
            })

    if corrections:
        logger.debug(f"Typo corrections: {corrections}")

    return corrections


def decompose_query(query: str) -> list[str]:
    """Split complex queries into sub-queries using conjunction-based heuristics.

    Only decomposes if:
    - Query has 8+ words
    - Contains a conjunction ("and", "also", "as well as", "plus")
    - Each sub-query has 3+ words (avoid splitting into fragments)

    Returns list of 1-3 sub-queries (returns [query] unchanged if no split).
    """
    words = query.split()
    if len(words) < 8:
        return [query]

    # Split on conjunctions between clauses
    parts = re.split(
        r'\b(?:and also|and then|and|also|as well as|plus)\b',
        query, flags=re.IGNORECASE
    )
    parts = [p.strip() for p in parts if len(p.strip().split()) >= 3]

    if len(parts) <= 1:
        return [query]
    return parts[:3]  # Cap at 3 sub-queries


def apply_query_intelligence(query: str, expand_synonyms: bool = True, correct_typos: bool = True) -> Dict:
    """
    Apply all query intelligence enhancements.

    Args:
        query: Original search query
        expand_synonyms: Whether to expand with synonyms
        correct_typos: Whether to suggest typo corrections

    Returns:
        Dict with:
        - enhanced_query: Improved query string
        - original_query: Original query
        - expansions: List of added synonym terms
        - corrections: List of typo corrections
        - routing: Query routing information
    """
    result = {
        "original_query": query,
        "enhanced_query": query,
        "expansions": [],
        "corrections": [],
        "routing": {}
    }

    # Apply typo corrections first
    if correct_typos:
        corrections = estimate_typo_corrections(query)
        if corrections:
            result["corrections"] = corrections

            # Apply corrections to query
            corrected_query = query
            for correction in corrections:
                corrected_query = corrected_query.replace(
                    correction["original"],
                    correction["suggestion"]
                )
            result["enhanced_query"] = corrected_query

    # Apply synonym expansion
    if expand_synonyms:
        expanded = expand_query_with_synonyms(result["enhanced_query"])

        # Track what was added
        original_words = set(result["enhanced_query"].lower().split())
        expanded_words = set(expanded.lower().split())
        added_words = list(expanded_words - original_words)

        if added_words:
            result["expansions"] = added_words
            result["enhanced_query"] = expanded

    # Get routing information
    result["routing"] = route_query(result["enhanced_query"])

    logger.info(
        f"Query intelligence: '{query}' → '{result['enhanced_query']}' | "
        f"Corrections: {len(result['corrections'])} | "
        f"Expansions: {len(result['expansions'])}"
    )

    return result
