# Quality Checker Skill

## Purpose
Provides a structured quality rubric for evaluating ebook chapter manuscripts, combining general quality criteria with domain-specific plugin criteria.

## Quality Rubric

### 1. Content Accuracy (Weight: Critical)
- Key claims are factually correct and source-backed
- Technical information is current and accurate
- Code examples produce expected results
- No misleading or ambiguous statements

### 2. Clarity & Accessibility (Weight: High)
- Language matches target audience level
- Complex concepts are explained before being used
- Technical jargon is defined on first use
- Examples effectively illustrate concepts

### 3. Completeness (Weight: High)
- All outline Key Content items are covered
- No topics are mentioned but left unexplained
- Code examples include necessary context (imports, setup)
- Sufficient depth for the reader to apply knowledge

### 4. Structure & Flow (Weight: Medium)
- Logical progression within each chapter
- Clear heading hierarchy (H1 → H2 → H3)
- Appropriate use of lists, code blocks, emphasis
- Smooth transitions between sections

### 5. Code Quality (Weight: High, for technical books)
- Syntactically valid code
- Follows language conventions and best practices
- Comments explain non-obvious logic
- Realistic examples (not contrived)

### 6. Cross-Chapter Consistency (Weight: Medium)
- Uniform terminology throughout the book
- Consistent tone and voice
- Accurate cross-references
- No contradictions between chapters

### 7. Domain Plugin Criteria (Weight: Variable)
If a domain plugin quality_criteria.md exists, apply its criteria in addition to the above. Common domain criteria:
- Domain-specific terminology standards
- Citation and reference format requirements
- Required disclaimers or warnings
- Prohibited language or claims

## Severity Classification

| Severity | Definition | Action |
|----------|-----------|--------|
| Blocking | Must fix before publication. Factual errors, broken code, missing critical content | Rewrite chapter |
| Non-blocking | Should fix but not a showstopper. Style issues, minor inconsistencies | Fix in editing |
| Note | Informational. Suggestions for improvement | Log only |

## When to Use
- Editor Agent during Step 4 (Editing/Validation)
- As a checklist for each chapter during review

## Output
Quality assessment results should be included in the edit report with severity classifications.
