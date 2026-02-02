# Phase 3.2: Memory Quality Evolution Tracking

## Overview

Phase 3.2 implements comprehensive quality tracking for memories, including multi-factor quality scoring, quality trend analysis, and automatic tier promotion based on quality metrics.

**Research basis:** Modern memory systems track memory quality evolution over time to identify high-value memories for preservation and low-value memories for archival. Quality-based tier promotion ensures important knowledge progresses from episodic → semantic → procedural based on demonstrated utility.

**Key Goals:**
- Calculate quality scores using multiple factors (access frequency, user ratings, relationships, stability)
- Track quality evolution over time
- Automatically promote memories to higher tiers based on sustained quality
- Provide quality analytics and insights

---

## Architecture

### Components

**Quality Score Calculator** (`QualityScoreCalculator`):
- Calculates composite quality scores from 4 components
- Normalizes and weights each component appropriately
- Includes tier-based bonuses for promoted memories

**Quality Tracker** (`QualityTracker`):
- Batch updates quality scores for all active memories
- Tracks quality distribution across bins
- Provides quality statistics by tier and overall

**Tier Promotion Engine** (`TierPromotionEngine`):
- Evaluates memories for tier promotion eligibility
- Applies promotion thresholds and age requirements
- Executes batch promotions with validation

### Quality Score Formula

```python
quality_score = (
    access_frequency_normalized * 0.30 +    # How often accessed
    user_rating_normalized * 0.25 +         # User feedback (weighted by confidence)
    relationship_density * 0.25 +           # Graph connectivity
    stability * 0.20 +                      # Edit frequency (inverse)
    tier_bonus                              # Procedural: +0.05, Semantic: +0.02
)
```

**Component Details:**

1. **Access Frequency (30% weight)**:
   ```python
   if access_count <= 10:
       access_frequency = access_count / 20
   elif access_count <= 50:
       access_frequency = 0.5 + ((access_count - 10) / 100)
   else:
       access_frequency = min(0.8 + ((access_count - 50) / 200), 1.0)
   ```
   - Tiered normalization: 0-10 accesses = 0-0.5, 11-50 = 0.5-0.9, 50+ = 0.9-1.0
   - Logarithmic-like curve to prevent extreme outliers

2. **User Rating (25% weight)**:
   ```python
   confidence = min(user_rating_count / 5, 1.0)  # Full confidence at 5+ ratings
   user_rating_normalized = (user_rating / 5.0) * confidence
   ```
   - Confidence weighting: 1 rating = 20% confidence, 5+ ratings = 100%
   - Prevents single ratings from dominating score

3. **Relationship Density (25% weight)**:
   ```python
   max_relationships = 10  # Saturation point
   relationship_density = min(relationship_count / max_relationships, 1.0)
   ```
   - Linear up to 10 relationships, then saturates
   - Encourages connecting memories to knowledge graph

4. **Stability (20% weight)**:
   ```python
   stability = 1.0 / (1 + current_version - 1)
   ```
   - Inverse of edit count: v1 = 1.0, v2 = 0.5, v3 = 0.33, v10 = 0.11
   - Rewards stable, unchanging knowledge

5. **Tier Bonus**:
   - Procedural: +0.05 (already high-quality, permanent)
   - Semantic: +0.02 (consolidated, generalized)
   - Episodic: +0.00 (baseline)

---

## Tier Promotion Logic

### Promotion Thresholds

**Episodic → Semantic:**
- Quality score: ≥ 0.75
- Minimum age: 7 days
- Sustained quality: Quality must remain above threshold

**Semantic → Procedural:**
- Quality score: ≥ 0.9
- Minimum age: 30 days
- High stability: Fewer than 3 edits

**Rationale:**
- Episodic memories need time to prove utility before consolidation
- Procedural tier reserved for best practices and permanent knowledge
- Age requirements prevent premature promotion

### Promotion Process

```python
# 1. Identify candidates
candidates = evaluate_promotion_candidates(
    min_quality_threshold=0.75,
    min_age_days=7
)

# 2. Validate eligibility
for candidate in candidates:
    if candidate.tier == "episodic" and candidate.quality >= 0.75:
        promote_to_semantic()
    elif candidate.tier == "semantic" and candidate.quality >= 0.9:
        promote_to_procedural()

# 3. Update graph
update_neo4j_tier(memory_id, new_tier)
```

---

## API Endpoints

### GET `/quality/stats`

Get quality score distribution and statistics.

**Response:**
```json
{
  "distribution": {
    "excellent": 15,    // 0.8-1.0
    "good": 42,         // 0.6-0.8
    "moderate": 78,     // 0.4-0.6
    "low": 23,          // 0.2-0.4
    "poor": 5           // 0.0-0.2
  },
  "avg_quality_by_tier": {
    "episodic": 0.52,
    "semantic": 0.71,
    "procedural": 0.89
  },
  "tier_distribution": {
    "episodic": 120,
    "semantic": 35,
    "procedural": 8
  },
  "overall_avg_quality": 0.58
}
```

### GET `/quality/{memory_id}/trend`

Get quality score trend for a specific memory.

**Query Parameters:**
- `days_back` (optional, default: 30): Number of days to look back

**Response:**
```json
{
  "memory_id": "019c1234-...",
  "current_quality_score": 0.78,
  "quality_history": [
    {
      "timestamp": "2026-02-01T10:00:00Z",
      "quality_score": 0.65,
      "access_count": 5,
      "user_rating": 4.0
    },
    {
      "timestamp": "2026-02-02T10:00:00Z",
      "quality_score": 0.78,
      "access_count": 12,
      "user_rating": 4.5
    }
  ],
  "trend_direction": "increasing",  // "increasing", "stable", "decreasing"
  "quality_change": 0.13
}
```

### POST `/quality/update`

Manually trigger quality score update for all memories.

**Response:**
```json
{
  "total_processed": 163,
  "total_updated": 163,
  "failed": 0,
  "avg_quality": 0.58,
  "quality_distribution": {
    "excellent": 15,
    "good": 42,
    "moderate": 78,
    "low": 23,
    "poor": 5
  },
  "processing_time_seconds": 1.2
}
```

### GET `/quality/promotion-candidates`

Get list of memories eligible for tier promotion.

**Query Parameters:**
- `min_quality_threshold` (optional, default: 0.75): Minimum quality score
- `min_age_days` (optional, default: 7): Minimum age in days

**Response:**
```json
{
  "total_candidates": 8,
  "candidates": [
    {
      "id": "019c1234-...",
      "current_tier": "episodic",
      "target_tier": "semantic",
      "quality_score": 0.82,
      "age_days": 14,
      "access_count": 25,
      "user_rating": 4.5,
      "relationship_count": 3
    }
  ]
}
```

### POST `/quality/promote-batch`

Trigger automatic tier promotion for eligible memories.

**Query Parameters:**
- `dry_run` (optional, default: false): Preview promotions without applying

**Response:**
```json
{
  "promoted_count": 8,
  "episodic_to_semantic": 6,
  "semantic_to_procedural": 2,
  "promoted": [
    {
      "id": "019c1234-...",
      "old_tier": "episodic",
      "new_tier": "semantic",
      "quality_score": 0.82
    }
  ],
  "dry_run": false
}
```

### POST `/quality/{memory_id}/rate`

Add a user rating to a memory's quality score.

**Query Parameters:**
- `rating` (required): Rating from 0-5

**Response:**
```json
{
  "memory_id": "019c1234-...",
  "new_rating": 4.5,
  "rating_count": 2,
  "new_quality_score": 0.78,
  "updated_memory": { /* full memory object */ }
}
```

---

## Scheduler Integration

**Job:** `quality_score_update_job`
- **Frequency:** Daily (24 hours)
- **Function:** `run_quality_score_update()`
- **Actions:**
  1. Update quality scores for all active memories
  2. Run automatic tier promotion
  3. Log promotion statistics

**Execution:**
```python
def run_quality_score_update():
    # Update quality scores
    update_result = QualityTracker.update_quality_scores(
        client, collection_name, batch_size=100
    )

    # Run automatic tier promotion
    promotion_result = TierPromotionEngine.auto_promote_batch(
        client, collection_name, dry_run=False
    )

    logger.info(f"Updated {update_result['total_updated']} memories, "
                f"promoted {promotion_result['promoted_count']}")
```

---

## Usage Examples

### Track Quality Evolution

```bash
# Get quality statistics
curl http://localhost:8100/quality/stats

# Get quality trend for specific memory
curl "http://localhost:8100/quality/019c1234-.../trend?days_back=30"

# Manually update all quality scores
curl -X POST http://localhost:8100/quality/update
```

### User Feedback

```bash
# Rate a memory 5 stars
curl -X POST "http://localhost:8100/quality/019c1234-.../rate?rating=5.0"

# Rate another memory 3 stars
curl -X POST "http://localhost:8100/quality/019c5678-.../rate?rating=3.0"
```

### Tier Promotion

```bash
# Get promotion candidates
curl "http://localhost:8100/quality/promotion-candidates?min_quality_threshold=0.75&min_age_days=7"

# Dry-run promotion (preview)
curl -X POST "http://localhost:8100/quality/promote-batch?dry_run=true"

# Execute promotions
curl -X POST "http://localhost:8100/quality/promote-batch?dry_run=false"
```

### Monitoring Quality

```bash
# Check quality distribution
curl http://localhost:8100/quality/stats | jq '.distribution'

# Find high-quality memories
curl http://localhost:8100/quality/stats | jq '.distribution.excellent'

# Monitor average quality by tier
curl http://localhost:8100/quality/stats | jq '.avg_quality_by_tier'
```

---

## Testing

### Test Suite: `tests/test_phase_3_2_quality.sh`

**Coverage:**
1. Service health check
2. Create test dataset with varying quality characteristics
3. User rating system
4. Quality score updates
5. Quality distribution statistics
6. Quality trend tracking
7. Promotion candidate detection
8. Dry-run tier promotion
9. Quality score components verification
10. Relationship impact on quality
11. Cleanup

**Run Tests:**
```bash
cd /Users/h4ckm1n/.claude/memory
chmod +x tests/test_phase_3_2_quality.sh
BASE_URL=http://localhost:8100 ./tests/test_phase_3_2_quality.sh
```

**Expected Output:**
```
✓ Service is healthy
✓ Created high-quality memory: 019c1234-...
✓ Accessed high-quality memory 10 times
✓ Quality scores updated: 163 memories
✓ High-quality memory has good score (>0.5)
✓ Quality statistics retrieved
✓ Promotion candidates retrieved: 8 candidates
✓ Dry-run promotion complete: would promote 8 memories
```

---

## Performance Considerations

### Batch Processing

Quality updates process memories in batches of 100 to prevent:
- Memory exhaustion from loading all memories at once
- Qdrant timeouts from large scroll operations
- Neo4j connection pool exhaustion

### Caching Strategy

Quality scores are cached in Qdrant payloads:
- No need to recalculate on every access
- Daily updates keep scores fresh
- User ratings trigger immediate recalculation

### Query Optimization

Quality distribution uses aggregation:
```python
# Instead of loading all memories:
# Scroll memories in batches
# Count in bins during iteration
# Return aggregated statistics
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Quality Score Accuracy** | Correlation > 0.8 with manual ratings | Compare calculated scores vs. user ratings |
| **Promotion Accuracy** | >90% promoted memories accessed in next 30 days | Track post-promotion access rates |
| **Average Quality** | Overall avg quality > 0.6 | Monitor `/quality/stats` avg_quality |
| **Tier Distribution** | 70% episodic, 25% semantic, 5% procedural | Check tier_distribution |
| **Update Performance** | <2 seconds for 200 memories | Monitor processing_time_seconds |

---

## Integration with Other Phases

### Phase 1.1 (Adaptive Forgetting)

Quality score influences decay rate:
```python
# High-quality memories decay slower
decay_rate = base_decay_rate * (1.0 - quality_score * 0.5)
```

### Phase 1.2 (Relationship Inference)

Relationship count directly impacts quality:
- More relationships → higher relationship_density component
- Incentivizes building knowledge graph

### Phase 3.1 (Pattern Detection)

Quality tracking enables:
- Identifying low-quality pattern clusters
- Recommending high-quality patterns for errors
- Filtering recommendations by quality threshold

### Phase 4.1 (State Machine) - Next Phase

Quality-based state transitions:
- EPISODIC → STAGING: quality < 0.4 for 7 days
- SEMANTIC → PROCEDURAL: quality ≥ 0.9 for 30 days
- ANY → ARCHIVED: quality < 0.2 for 30 days

---

## Research Sources

1. **Mem0 Production-Ready Agents**: Quality tracking improves retention by 26% by focusing on high-value memories
2. **Graphiti Knowledge Graph**: Relationship density as quality indicator
3. **Spaced Repetition Research**: Quality-based promotion mirrors SM-2 algorithm tier progression
4. **User Feedback Integration**: Confidence-weighted ratings prevent single-user bias

---

## Future Enhancements

### Quality Prediction

Predict future quality based on early signals:
```python
# After 3 days, predict 30-day quality
early_quality = quality_at_3_days
predicted_30d = early_quality * growth_factor
```

### Quality-based Recommendation

Boost high-quality memories in search results:
```python
final_score = relevance_score * (1.0 + quality_score * 0.3)
```

### Quality Decay Over Time

Quality should decay if memory not accessed:
```python
# Quality reduces by 10% every 90 days without access
quality_decay = 0.9 ** (days_since_access / 90)
```

---

## Troubleshooting

### Quality Scores Too Low

**Symptom:** All memories have quality < 0.4

**Solution:**
- Check if memories are being accessed (access_count > 0)
- Verify relationships are being created (relationship_count > 0)
- Add user ratings to boost scores

### No Promotions Happening

**Symptom:** `promote-batch` returns 0 promoted

**Solution:**
- Check age requirements (7 days for semantic, 30 for procedural)
- Lower quality threshold temporarily for testing
- Verify memories have sufficient access counts

### Quality Update Job Failing

**Symptom:** Scheduler job errors in logs

**Solution:**
- Check Qdrant connectivity
- Verify collection exists and has memories
- Check for large batch sizes causing timeouts

---

## Conclusion

Phase 3.2 provides comprehensive quality tracking with:
- ✅ Multi-factor quality scoring (4 components)
- ✅ Quality evolution tracking over time
- ✅ Automatic tier promotion based on quality
- ✅ User feedback integration with confidence weighting
- ✅ Quality analytics and distribution statistics

This enables the memory system to:
- Identify and preserve high-value knowledge
- Automatically promote important memories to higher tiers
- Archive or purge low-quality memories (Phase 4)
- Provide quality-based recommendations and search ranking

**Next Phase:** 4.1 - Memory State Machine with quality-based state transitions.
