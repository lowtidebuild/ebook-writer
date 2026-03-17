# Web Research Skill

## Purpose
Provides structured web search and information collection strategies for comprehensive topic research.

## Capabilities
1. Multi-query web search with varied phrasing
2. Source credibility assessment
3. Finding deduplication across queries
4. Bilingual search (Korean + English)

## Search Strategy

### Query Formulation
For each research question, generate 2-3 search queries:
- **Exact match**: Use the question as-is
- **Technical variant**: Rephrase with specific technical terminology
- **Korean variant**: Translate the question to Korean for Korean-language sources

### Source Credibility Hierarchy
1. **Official documentation** — Primary source (highest credibility)
2. **Peer-reviewed / established publications** — Academic and industry publications
3. **Expert blog posts** — Technical blog posts from recognized domain experts
4. **Community resources** — Stack Overflow, GitHub discussions, forums
5. **News articles** — Recent developments and announcements
6. **Social media** — Lowest credibility, use only for trending topics

### Deduplication
When multiple sources report the same finding:
- Keep the most authoritative source
- Note corroboration: "Confirmed by N sources"
- Remove redundant entries

## When to Use
- Researcher Agent, Step 1 of the pipeline
- When decomposing topic into research questions and collecting findings

## Failure Handling
- If WebSearch returns no results: rephrase the query and retry (max 2 retries)
- If WebFetch fails on a URL: skip that source, note as "inaccessible"
- If an entire topic area yields no results: flag in the Coverage Assessment section
