# GxP.MD v3 — Implementer's Guide for Tool Builders

**Version 3.0.0** | **Audience**: Developers building ALM tools, verification engines, CI/CD integrations, or IDE plugins that consume or produce GxP.MD-compliant artifacts.

**Copyright 2026 James Gannon. Licensed under Apache 2.0.**

---

## 1. Introduction

This guide tells you everything you need to build tooling on top of the GxP.MD v3 specification. It covers the data model, parsing rules, graph construction, coverage algorithms, and output contracts. If you are building an ALM (Application Lifecycle Management) system, a static analysis tool, a CI/CD gate, a dashboard, or an IDE plugin that works with GxP.MD-annotated codebases — this is your reference.

The reference implementation is `tools/gxpmd-harden.py` in this repository — a zero-dependency Python script that implements every algorithm described here. Treat it as both documentation and test oracle.

### 1.1 What Your Tool Consumes

Your tool reads two things:

1. **A `GxP.MD` file** at the project root — YAML frontmatter containing configuration (risk matrix, required tags, enforcement mode) followed by markdown body containing behavioral directives.
2. **Source and test files** anywhere in the project tree — containing structured annotations (code comments with `@gxp-*` tags) that declare traceability relationships.

### 1.2 What Your Tool Produces

Depending on tool type, outputs typically include some subset of:

- **Traceability graph** (`.gxp/traceability-matrix.json`) — the DAG of relationships
- **Compliance status** (`.gxp/compliance-status.md`) — human-readable report
- **Gap analysis** (`.gxp/gap-analysis.json`) — validation issues
- **Artifact stubs** (`.gxp/requirements/REQ-NNN.md`, `.gxp/specs/SPEC-NNN.md`)
- **Evidence packages** (`.gxp/evidence/`)
- **Gate pass/fail signals** — for CI/CD integration

---

## 2. The Data Model

### 2.1 Node Types

The traceability graph is a directed acyclic graph (DAG) with six node types:

| Node Type | ID Format | Phase Label | Description |
|-----------|-----------|-------------|-------------|
| Requirement | `REQ-NNN` | `requirement` | What the system must do (regulatory/business need) |
| User Story | `US-NNN` | `user_story` | How users interact with the system to satisfy a requirement |
| Specification | `SPEC-NNN` | `specification` | How the system is implemented (technical design) |
| Source File | `FILE:{path}` | `code` | Implementation code |
| Test File | `FILE:{path}` | `test` | Verification code |
| Evidence | `{TIER}-{SPEC}-{TIMESTAMP}` | `evidence` | Formal proof of test execution |

**Critical: IDs are opaque.** `REQ-001`, `US-042`, `SPEC-137` — the numbers are monotonically increasing within each type but carry no hierarchical meaning. `SPEC-001` does NOT belong to `US-001` or `REQ-001`. All relationships are expressed via explicit edges.

### 2.2 Edge Types

Four edge types connect nodes:

| Edge Tag | Direction | Meaning | Valid Source → Target |
|----------|-----------|---------|---------------------|
| `@gxp-satisfies` | source → requirement | "This code/story satisfies this requirement" | `FILE:*` → `REQ-NNN`, `US-NNN` → `REQ-NNN` |
| `@gxp-implements` | source → spec/story | "This code implements this spec or user story" | `FILE:*` → `SPEC-NNN`, `FILE:*` → `US-NNN` |
| `@gxp-verifies` | test → spec | "This test verifies this specification" | `FILE:*` → `SPEC-NNN` |
| `@gxp-derives-from` | artifact → artifact | "This artifact is derived from another" | `US-NNN` → `REQ-NNN`, `SPEC-NNN` → `US-NNN` |

**Many-to-many is native.** A single `@gxp-satisfies REQ-001, REQ-003` annotation creates two edges from one source file to two requirements. A single test file can `@gxp-verifies SPEC-042, SPEC-043`.

### 2.3 Node Properties

Every node carries:

```json
{
  "id": "REQ-001",
  "phase": "requirement",
  "risk": "HIGH",
  "title": "User authentication",
  "files": ["src/auth/login.ts"],
  "tiers": ["OQ", "PQ"],
  "covered": true
}
```

- `id` — Unique identifier.
- `phase` — One of: `requirement`, `user_story`, `specification`, `code`, `test`, `evidence`.
- `risk` — `HIGH`, `MEDIUM`, `LOW`, or `UNKNOWN`. Propagated from the `@gxp-risk` tag on the annotated file. For abstract nodes (REQ, US, SPEC), risk is the highest risk declared by any file that references them.
- `title` — Human-readable description. Extracted from annotation description strings or formal artifact YAML.
- `files` — Source/test files associated with this node.
- `tiers` — Set of verification tiers (`IQ`, `OQ`, `PQ`) from `@test-type` tags on test files that verify this node.
- `covered` — Boolean, computed via graph reachability (Section 5).

### 2.4 Edge Properties

Every edge carries:

```json
{
  "from": "FILE:src/auth/login.ts",
  "to": "REQ-001",
  "type": "satisfies",
  "source_file": "src/auth/login.ts"
}
```

- `from` — The node originating the edge (the thing that satisfies/implements/verifies).
- `to` — The target node (what is being satisfied/implemented/verified).
- `type` — One of: `satisfies`, `implements`, `verifies`, `derives_from`.
- `source_file` — The file where the edge tag was found (important for tracing edge provenance).

---

## 3. Parsing the GxP.MD Configuration

### 3.1 Frontmatter Extraction

The `GxP.MD` file uses YAML frontmatter delimited by `---` on its own line:

```
---
gxpmd_version: "3.0.0"
project:
  name: "MyApp"
  ...
---

# Markdown body starts here
```

**Parser requirements:**

1. Find the first `---` at the start of the file.
2. Find the next `\n---` after the first delimiter.
3. Extract the YAML block between them.
4. Parse the YAML. If you have a YAML library (PyYAML, js-yaml, serde_yaml), use it. The reference implementation parses without PyYAML using regex, but this is a compromise for zero-dependency operation.

**Key config fields your tool MUST read:**

| Path | Type | Default | Purpose |
|------|------|---------|---------|
| `gxpmd_version` | string | — | Spec version. Your tool SHOULD validate this is `"3.0.0"` or compatible. |
| `risk.matrix.{HIGH,MEDIUM,LOW}.coverage_threshold` | int | 95/80/60 | Minimum test coverage percentage per risk level |
| `risk.matrix.{HIGH,MEDIUM,LOW}.required_tiers` | list | varies | Which IQ/OQ/PQ tiers must have tests |
| `annotations.schema_version` | string | `"2.0"` | `"2.0"` = v3 edge tags, `"1.0"` = v2 legacy tags |
| `annotations.required_tags.source` | list | — | Tags required in source files |
| `annotations.required_tags.test` | list | — | Tags required in test files |
| `annotations.edge_tags` | list | — | All edge tags the project uses |
| `artifacts.directory` | string | `.gxp` | Where outputs are written |
| `artifacts.traceability_enforcement` | string | `strict` | `strict`, `warn`, or `off` |
| `agent.mode` | string | `risk_proportionate` | `strict`, `risk_proportionate`, or `advisory` |

### 3.2 Handling Missing Config

Tools MUST have sane defaults for every config value. The reference implementation defines `DEFAULT_CONFIG`:

```python
DEFAULT_CONFIG = {
    'risk_matrix': {
        'HIGH': {'coverage_threshold': 95, 'required_tiers': ['IQ', 'OQ', 'PQ']},
        'MEDIUM': {'coverage_threshold': 80, 'required_tiers': ['OQ', 'PQ']},
        'LOW': {'coverage_threshold': 60, 'required_tiers': ['OQ']},
    },
    'artifacts_dir': '.gxp',
    'required_source_tags': ['@gxp-satisfies', '@gxp-implements', '@gxp-risk'],
    'required_test_tags': ['@gxp-verifies', '@test-type', '@gxp-risk'],
}
```

If frontmatter is missing or malformed, fall back to these defaults rather than failing.

---

## 4. Parsing Annotations

### 4.1 Tag Syntax (Regular Expressions)

Your tool MUST parse these v3 edge tags:

```
@gxp-satisfies   REQ-NNN[, REQ-NNN, ...]
@gxp-implements  US-NNN|SPEC-NNN[, US-NNN|SPEC-NNN, ...]
@gxp-verifies    SPEC-NNN[, SPEC-NNN, ...]
@gxp-derives-from REQ-NNN|US-NNN|SPEC-NNN[, ...]
```

And these common tags:

```
@gxp-risk        HIGH|MEDIUM|LOW
@gxp-risk-concern "description string"
@test-type       IQ|OQ|PQ
```

Reference regex patterns (Python `re` syntax):

```python
# v3 Edge tags
RE_SATISFIES    = re.compile(r'@gxp-satisfies\s+((?:REQ-\d{3})(?:\s*,\s*REQ-\d{3})*)')
RE_IMPLEMENTS   = re.compile(r'@gxp-implements\s+((?:(?:US|SPEC)-\d{3})(?:\s*,\s*(?:US|SPEC)-\d{3})*)')
RE_VERIFIES     = re.compile(r'@gxp-verifies\s+((?:SPEC-\d{3})(?:\s*,\s*SPEC-\d{3})*)')
RE_DERIVES_FROM = re.compile(r'@gxp-derives-from\s+((?:(?:REQ|US|SPEC)-\d{3})(?:\s*,\s*(?:REQ|US|SPEC)-\d{3})*)')

# Common tags
RE_RISK         = re.compile(r'@gxp-risk\s+(HIGH|MEDIUM|LOW)')
RE_RISK_CONCERN = re.compile(r'@gxp-risk-concern\s+"([^"]*)"')
RE_TEST_TYPE    = re.compile(r'@test-type\s+(IQ|OQ|PQ)')
```

### 4.2 Multi-ID Parsing

Edge tags accept comma-separated ID lists. Parse the matched group:

```python
def parse_id_list(match_str: str) -> list[str]:
    return [id.strip() for id in match_str.split(',') if id.strip()]
```

Example: `@gxp-satisfies REQ-001, REQ-003` yields `['REQ-001', 'REQ-003']`.

### 4.3 Legacy v2 Backward Compatibility

During the migration period, your tool SHOULD also recognize v2 tags:

```
@gxp-req   REQ-NNN ["description"]     →  treat as @gxp-satisfies REQ-NNN
@gxp-spec  SPEC-NNN-NNN ["description"] → treat as @gxp-implements SPEC-NNN-NNN (source) or @gxp-verifies SPEC-NNN-NNN (test)
@trace     US-NNN-NNN                   →  treat as @gxp-verifies US-NNN-NNN
```

When v2 tags are detected, emit a WARNING recommending migration to v3 edge tags. Do NOT emit an ERROR — v2 projects upgrading incrementally need runway.

Note that v2 IDs use hierarchical encoding (`SPEC-001-002`, `US-001-003`). Your tool SHOULD accept these as opaque strings. Do NOT parse the embedded parent relationship — that was the v2 failure mode.

### 4.4 File Classification

A file is a test file if:

- Its path contains `/tests/`, `/test/`, `/__tests__/`, `/iq/`, `/oq/`, or `/pq/`
- Its filename stem ends with `.test`, `.spec`, `_test`, or `_spec`

Everything else with GxP annotations is a source file.

### 4.5 Supported Languages

Scan any file with these extensions:

```
.ts .tsx .js .jsx .mjs .cjs       (TypeScript/JavaScript)
.py .pyw                           (Python)
.java .kt .kts                    (Java/Kotlin)
.cs                                (C#)
.go                                (Go)
.rs                                (Rust)
.rb                                (Ruby)
.swift                             (Swift)
.c .cpp .h .hpp                    (C/C++)
```

### 4.6 Excluded Directories

Always skip:

```
node_modules  dist  build  .git  .gxp
__pycache__  .venv  venv  .tox  target
vendor  coverage  .next  .nuxt
```

### 4.7 Annotation Placement

Tags appear in block comments (`/* */`, `/** */`, `# ... `, `// ...`). They can be at file top or immediately preceding a function/class/describe block. Your parser does NOT need to understand the comment syntax — a simple full-text regex search over the file content is sufficient, because the tag names are distinctive enough to avoid false positives.

---

## 5. Building the Traceability DAG

This is the core algorithm. It takes parsed annotations and produces the graph.

### 5.1 Algorithm Overview

```
Input:  List of parsed annotation records (one per annotated file)
Output: { nodes: {id → properties}, edges: [{from, to, type, source_file}], coverage: {req_id → coverage_info} }

For each annotated file:
  1. Create a FILE node for the file itself (phase = 'code' or 'test')
  2. For each @gxp-satisfies target:
     - Ensure REQ node exists
     - Add edge: FILE:path → REQ-NNN (type: satisfies)
  3. For each @gxp-implements target:
     - Ensure US/SPEC node exists
     - Add edge: FILE:path → US/SPEC-NNN (type: implements)
  4. For each @gxp-verifies target:
     - Ensure SPEC node exists
     - Add edge: FILE:path → SPEC-NNN (type: verifies)
     - Record test tiers (@test-type) on the FILE node
  5. For each @gxp-derives-from target:
     - Add edge between referenced artifacts (type: derives_from)

After all files processed:
  6. Run coverage calculation (Section 5.3)
```

### 5.2 Node ID Generation

For source/test files, generate deterministic node IDs:

```
FILE:src/auth/login.ts
FILE:tests/oq/auth/login.test.ts
```

The `FILE:` prefix distinguishes file nodes from artifact nodes (`REQ-*`, `US-*`, `SPEC-*`).

For artifact nodes, the ID comes directly from the annotation: `REQ-001`, `US-042`, `SPEC-137`.

### 5.3 Coverage via Graph Reachability

A requirement `REQ-NNN` is **covered** if there exists at least one path between any test node and `REQ-NNN` through the edge graph.

**Edge direction recap:** Edges point from the thing-that-satisfies TO the thing-being-satisfied. A test `@gxp-verifies SPEC-042` creates an edge `FILE:test.ts → SPEC-042`. A source file `@gxp-satisfies REQ-001` creates an edge `FILE:src.ts → REQ-001`. A source file `@gxp-implements SPEC-042` creates an edge `FILE:src.ts → SPEC-042`.

**The challenge:** A typical multi-hop path looks like: `FILE:test.ts → SPEC-042 ← FILE:src.ts → REQ-001`. Traversing only reverse edges (target→source) from `REQ-001` reaches `FILE:src.ts` but dead-ends there — the test node points at `SPEC-042`, not at `FILE:src.ts`. To find tests, we must traverse edges in **both directions** (undirected/bidirectional).

Algorithm (BFS from each requirement, traversing edges as undirected):

```
function is_covered(req_id, nodes, edges):
    // Build undirected adjacency: node → [neighbors]
    adj = build_undirected_adjacency(edges)

    // BFS from req_id via undirected edges
    visited = {req_id}
    queue = [req_id]

    while queue not empty:
        current = queue.pop_front()
        for each neighbor in adj[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                if nodes[neighbor].phase == 'test':
                    return true  // Found a test connected to this requirement

    return false  // No test is connected to this requirement
```

**Why undirected traversal?** In a typical multi-hop traceability path, edges alternate direction: a test file points at a SPEC (`FILE:test → SPEC`), and a source file also points at that SPEC (`FILE:src → SPEC`) as well as at a REQ (`FILE:src → REQ`). The SPEC node acts as a shared hub connecting tests to source files. Traversing only one edge direction from the requirement would dead-end at file nodes without discovering the test nodes connected through intermediate SPEC/US nodes. Undirected traversal allows the BFS to cross these hubs and find all connected test nodes regardless of edge direction.

**Tier coverage** is calculated similarly: collect all `@test-type` values from test nodes reachable from a requirement. Compare against `required_tiers` from the risk matrix.

### 5.4 Cycle Detection

The graph MUST be acyclic. If you detect a cycle, emit an ERROR. Simple DFS cycle detection suffices:

```
function detect_cycles(nodes, edges):
    adj = build_adjacency(edges)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {id: WHITE for id in nodes}

    for node_id in nodes:
        if color[node_id] == WHITE:
            if dfs_has_cycle(node_id, adj, color):
                return true
    return false
```

In practice, cycles are extremely rare because the edge semantics naturally flow in one direction (tests verify specs, specs implement stories, stories satisfy requirements).

### 5.5 Risk Propagation

Artifact nodes (REQ, US, SPEC) may not have a direct `@gxp-risk` tag — they are abstract. Propagate risk from connected file nodes:

- For each artifact node, its risk is the **highest** risk declared by any file node that points to it.
- `HIGH > MEDIUM > LOW > UNKNOWN`

---

## 6. Validation Rules

### 6.1 Annotation Completeness

**Source files** (non-test):

| Condition | Severity | Message |
|-----------|----------|---------|
| No edge tags AND no legacy tags AND risk != LOW | ERROR | Source file has no traceability edge tags |
| No `@gxp-risk` | ERROR | Source file missing @gxp-risk annotation |
| Has legacy v2 tags but no v3 tags | WARNING | Migrate to v3 edge tags |
| Multiple different `@gxp-risk` values in one file | WARNING | Mixed risk levels |

**Test files**:

| Condition | Severity | Message |
|-----------|----------|---------|
| No `@gxp-verifies` AND no legacy `@gxp-spec` | ERROR | Test file missing @gxp-verifies |
| No `@test-type` | ERROR | Test file missing @test-type |
| No `@gxp-risk` | ERROR | Test file missing @gxp-risk |

### 6.2 Orphan Detection

After building the graph, check for disconnected nodes:

| Condition | Severity | Message |
|-----------|----------|---------|
| Node with zero incoming AND zero outgoing edges | ERROR (if HIGH risk), WARNING otherwise | Completely disconnected from graph |
| Requirement with zero incoming edges | WARNING | No code or specs satisfying it |
| Specification with zero incoming edges | WARNING | No tests verifying it |

**Critical difference from v2**: In v2, orphan detection parsed IDs to infer phantom parents and then complained they were missing. In v3, orphan detection only looks at actual edges. A `SPEC-042` with no REQ is perfectly valid for LOW risk — it just means the spec has a shorter traceability path.

### 6.3 Coverage Validation

For each requirement node:

| Condition | Severity | Message |
|-----------|----------|---------|
| Not reachable from any test node | ERROR | Requirement has no test coverage |
| Missing required tiers (per risk matrix) | ERROR | Missing IQ/OQ/PQ tier for risk level |
| Risk level is UNKNOWN | WARNING | No risk level assigned |

---

## 7. Output Contracts

### 7.1 Traceability Matrix JSON

File: `.gxp/traceability-matrix.json`

This is the primary machine-readable output. Tools consuming GxP.MD outputs SHOULD parse this file.

```json
{
  "gxpmd_version": "3.0.0",
  "generated_at": "2026-02-09T14:30:00Z",
  "project_root": "/path/to/project",
  "summary": {
    "total_nodes": 42,
    "total_edges": 67,
    "total_requirements": 7,
    "covered_requirements": 7,
    "coverage_by_risk": {
      "HIGH": {"total": 3, "covered": 3, "percentage": 100.0},
      "MEDIUM": {"total": 2, "covered": 2, "percentage": 100.0},
      "LOW": {"total": 2, "covered": 2, "percentage": 100.0}
    }
  },
  "nodes": {
    "REQ-001": {
      "phase": "requirement",
      "risk": "HIGH",
      "title": "User authentication",
      "files": [],
      "tiers": []
    },
    "SPEC-042": {
      "phase": "specification",
      "risk": "HIGH",
      "title": "OAuth2 PKCE flow",
      "files": ["src/auth/login.ts"],
      "tiers": []
    },
    "FILE:src/auth/login.ts": {
      "phase": "code",
      "risk": "HIGH",
      "title": null,
      "files": ["src/auth/login.ts"],
      "tiers": []
    },
    "FILE:tests/oq/auth/login.test.ts": {
      "phase": "test",
      "risk": "HIGH",
      "title": null,
      "files": ["tests/oq/auth/login.test.ts"],
      "tiers": ["OQ"]
    }
  },
  "edges": [
    {"from": "FILE:src/auth/login.ts", "to": "REQ-001", "type": "satisfies", "source_file": "src/auth/login.ts"},
    {"from": "FILE:src/auth/login.ts", "to": "SPEC-042", "type": "implements", "source_file": "src/auth/login.ts"},
    {"from": "FILE:tests/oq/auth/login.test.ts", "to": "SPEC-042", "type": "verifies", "source_file": "tests/oq/auth/login.test.ts"}
  ],
  "coverage": {
    "REQ-001": {
      "risk": "HIGH",
      "covered": true,
      "test_nodes": ["FILE:tests/oq/auth/login.test.ts"],
      "reachable_nodes": 4
    }
  }
}
```

**Interoperability note**: The `tiers` field on nodes is an array of strings (not a set). Deduplicate when parsing.

### 7.2 Compliance Status Report

File: `.gxp/compliance-status.md`

Human-readable markdown. Format:

```markdown
# Compliance Status Report

Generated: 2026-02-09 14:30:00 UTC
GxP.MD Version: 3.0.0

---

## Summary

| Metric | Value |
|--------|-------|
| Total requirements | 7 |
| Covered requirements | 7/7 |
| Total nodes | 42 |
| Total edges | 67 |
| Annotated source files | 15 |
| Annotated test files | 22 |
| Errors | 0 |
| Warnings | 2 |

## Errors
[list of error-severity issues]

## Warnings
[list of warning-severity issues]

## Traceability Graph Summary
[per-requirement coverage status]

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| QA Lead | _____ | _____ | _____ |
| Project Owner | _____ | _____ | _____ |

*Sign-off is completed by humans, not agents or tools.*
```

**Tools MUST NOT fill in the sign-off section.** Generate it empty.

### 7.3 Gap Analysis JSON

File: `.gxp/gap-analysis.json`

```json
{
  "generated_at": "2026-02-09T14:30:00Z",
  "gxpmd_version": "3.0.0",
  "total_issues": 3,
  "errors": 1,
  "warnings": 2,
  "validation_issues": [...],
  "orphan_issues": [...],
  "coverage_issues": [...]
}
```

Each issue has `file` or `node` or `requirement`, `severity` (ERROR/WARNING), and `message`.

### 7.4 Artifact Stubs

For each requirement/specification found in annotations that lacks a corresponding `.gxp/requirements/REQ-NNN.md` or `.gxp/specs/SPEC-NNN.md`:

- Generate a stub with YAML frontmatter containing the ID, title (from annotation description), risk level, and `validation_status: draft`.
- Never overwrite existing formal artifact files.
- Mark stubs clearly as auto-generated.

---

## 8. CI/CD Integration Patterns

### 8.1 Pre-Commit Hook

Minimal check: parse annotations in staged files, validate syntax.

```bash
#!/bin/bash
# .git/hooks/pre-commit
python3 tools/gxpmd-harden.py --root . --validate-only --files $(git diff --cached --name-only)
```

Your tool SHOULD support a `--validate-only` or `--quick` flag that skips graph construction and only checks annotation syntax.

### 8.2 Pre-Merge / PR Check

Full validation: build graph, check orphans, validate coverage.

```yaml
# GitHub Actions example
- name: GxP.MD Compliance Check
  run: |
    python3 tools/gxpmd-harden.py --root . --coverage coverage/coverage-summary.json
    exit_code=$?
    if [ $exit_code -ne 0 ]; then
      echo "::error::GxP.MD compliance check failed"
      exit 1
    fi
```

### 8.3 Per-Release / Harden

Full sweep with evidence formalization:

```yaml
- name: GxP.MD Harden
  run: |
    python3 tools/gxpmd-harden.py --root . --coverage coverage/coverage-summary.json --json
    git add .gxp/
    git commit -m "chore: harden sweep $(date +%Y-%m-%dT%H:%M:%S)"
```

### 8.4 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | All checks pass, no errors |
| 1 | One or more ERROR-severity issues found |
| 2 | Configuration error (missing GxP.MD, invalid frontmatter) |

Warnings do NOT cause non-zero exit.

---

## 9. Working with Formal Artifact Files

### 9.1 YAML Frontmatter Schema

Formal artifact files in `.gxp/requirements/`, `.gxp/user_stories/`, and `.gxp/specs/` use YAML frontmatter with edge relationships:

**Requirements** (`.gxp/requirements/REQ-NNN.md`):

```yaml
---
gxp_id: REQ-001
title: "User authentication"
satisfies: []              # Parent/derived requirements (empty for top-level)
risk_level: HIGH
acceptance_criteria:
  - "Testable condition 1"
  - "Testable condition 2"
validation_status: DRAFT   # DRAFT | APPROVED | IMPLEMENTED | VALIDATED | DEPRECATED
---
```

**User Stories** (`.gxp/user_stories/US-NNN.md`):

```yaml
---
gxp_id: US-001
title: "As a QM, I want to view audit logs"
satisfies: [REQ-001]       # Which requirements this story satisfies (many-to-many)
verification_tier: OQ
validation_status: DRAFT
---
```

**Specifications** (`.gxp/specs/SPEC-NNN.md`):

```yaml
---
gxp_id: SPEC-001
title: "Audit log table component"
implements: [US-001]        # Which user stories this spec implements
satisfies: [REQ-001]        # Direct requirement satisfaction (optional)
source_files:
  - "src/components/AuditLogTable.tsx"
test_files:
  - "tests/oq/auditLog.test.ts"
verification_tier: OQ
validation_status: DRAFT
---
```

### 9.2 Merging Artifact Edges into the Graph

When building the traceability graph, your tool SHOULD also parse formal artifact files and add their edges:

1. Scan `.gxp/requirements/`, `.gxp/user_stories/`, `.gxp/specs/`
2. Parse YAML frontmatter
3. For each `satisfies`, `implements`, or `derives_from` field, add edges to the graph
4. These edges supplement (not replace) edges from code annotations

This means the graph has two edge sources: code annotations and artifact file frontmatter. Both contribute to the same DAG.

---

## 10. Evidence Package Integration

### 10.1 Package Structure

```
.gxp/evidence/{TIER}-{SPEC_ID}-{TIMESTAMP}/
├── metadata.json
├── environment.json
├── test-output.log
├── manifest.json
└── signature.jws        (optional)
```

### 10.2 Metadata Contract

`metadata.json` MUST contain:

```json
{
  "spec_id": "SPEC-042",
  "tier": "OQ",
  "gxp_risk": "HIGH",
  "timestamp": "2026-02-09T14:30:00Z",
  "duration_ms": 4523,
  "result": "pass",
  "test_count": 12,
  "pass_count": 12,
  "fail_count": 0,
  "skip_count": 0,
  "coverage": {"lines": 97.2, "branches": 94.8, "functions": 98.1},
  "system_state_hash": "sha256:a1b2c3..."
}
```

### 10.3 Integrity Rules

- Evidence packages are immutable after creation.
- Failed test runs MUST be preserved (ALCOA+ Complete principle).
- `test-output.log` must be complete and unedited.
- `system_state_hash` must be computed from the `/src` tree at test execution time using SHA-256.
- `manifest.json` contains SHA-256 hashes of all other files in the package.

---

## 11. Regulatory Profile Awareness

### 11.1 Built-in Profiles

Profiles in `spec/profiles/*.yml` customize enforcement for different regulatory contexts:

| Profile | Key Differences |
|---------|----------------|
| `pharma-standard` | 21 CFR Part 11, EU Annex 11, GAMP 5, HIGH/MEDIUM/LOW thresholds 95/80/60 |
| `medical-device` | IEC 62304, 21 CFR 820, EU MDR, software safety classification |
| `clinical-trial` | ICH E6(R2), GCP, 21 CFR Part 11 |
| `laboratory` | 21 CFR Part 58 (GLP), ISO 17025 |

Your tool SHOULD read the `regulatory.profile` field from frontmatter and adjust behavior accordingly. The profile primarily affects which frameworks are listed in reports and which coverage thresholds apply.

### 11.2 Custom Profiles

Projects may define custom enforcement rules in the "Project-Specific Rules" section of the GxP.MD file. These are human-readable directives. Your tool does not need to parse them, but SHOULD pass them through to reports.

---

## 12. Common Implementation Mistakes

### 12.1 DO NOT Infer Relationships from IDs

This was the v2 failure mode. Never do this:

```python
# WRONG — this is the v2 bug
def spec_to_req(spec_id):
    m = re.match(r'SPEC-(\d{3})-\d{3}', spec_id)
    return f'REQ-{m.group(1)}'
```

In v3, `SPEC-042` has no implied relationship to any requirement. All relationships come from explicit edge tags.

### 12.2 DO NOT Reject Skipped Phases

A valid v3 traceability path for a LOW risk component:

```
SPEC-042 ← implements ← FILE:src/util.ts ← verifies ← FILE:tests/oq/util.test.ts
```

No `REQ-*` or `US-*` in the chain. This is legal. The spec is implemented and tested. Coverage is satisfied.

Your tool MUST NOT require every SPEC to have a REQ. That was v2's false-orphan problem.

### 12.3 DO NOT Hard-Code the Harden Output Path

Read `artifacts.directory` from the frontmatter. It defaults to `.gxp` but could be anything.

### 12.4 DO Handle Many-to-Many Gracefully

A source file satisfying three requirements creates three edges, not three copies of the node. Count edges, not nodes, when computing graph metrics.

### 12.5 DO Preserve Failing Evidence

ALCOA+ requires completeness. If a test suite fails and is re-run, both the failure and success evidence packages MUST be retained. Tools MUST NOT offer "clean up failed evidence" features.

---

## 13. Testing Your Implementation

### 13.1 Minimal Test Case

Create a tiny project with v3 annotations and verify your tool produces correct output:

```python
# src/auth.py
# @gxp-satisfies REQ-001, REQ-003
# @gxp-implements SPEC-042
# @gxp-risk HIGH
def authenticate(user, password):
    return True
```

```python
# tests/oq/test_auth.py
# @gxp-verifies SPEC-042
# @test-type OQ
# @gxp-risk HIGH
def test_authenticate():
    assert True
```

Expected graph:

- 3 artifact nodes: REQ-001, REQ-003, SPEC-042
- 2 file nodes: FILE:src/auth.py, FILE:tests/oq/test_auth.py
- 4 edges:
  - FILE:src/auth.py → REQ-001 (satisfies)
  - FILE:src/auth.py → REQ-003 (satisfies)
  - FILE:src/auth.py → SPEC-042 (implements)
  - FILE:tests/oq/test_auth.py → SPEC-042 (verifies)
- Coverage: REQ-001 covered (path: REQ-001 ← src/auth.py ← SPEC-042 ← test_auth.py), REQ-003 covered

### 13.2 Edge Cases to Test

1. **Many-to-many**: Single file satisfying 3 REQs and implementing 2 SPECs
2. **Skipped phases**: SPEC → CODE → TEST with no REQ or US
3. **Cross-cutting**: Two source files both satisfying the same REQ
4. **Mixed v2/v3**: Files with `@gxp-req` (v2) alongside files with `@gxp-satisfies` (v3)
5. **Empty project**: No annotations found (should warn, not crash)
6. **Single annotation**: File with only `@gxp-risk` and no edge tags (warning for non-LOW)

### 13.3 Conformance with Reference Implementation

Run the reference implementation (`tools/gxpmd-harden.py`) against your test project and compare the traceability matrix JSON output with your tool's output. They should produce equivalent graphs (node and edge counts match, coverage results match).

---

## 14. API Surface for IDE Plugins

If you are building an IDE plugin (VS Code, IntelliJ, etc.), consider these user-facing features:

### 14.1 Inline Diagnostics

Show ERROR/WARNING squiggles on annotation lines that fail validation:

- Missing `@gxp-risk` on a file with other GxP annotations
- `@gxp-verifies` referencing a SPEC ID that doesn't exist in any source file
- Mixed risk levels in one file

### 14.2 Go-to-Definition for IDs

When a user clicks `SPEC-042` in a `@gxp-verifies` tag, navigate to the source file containing `@gxp-implements SPEC-042`. This requires building a reverse index: ID → list of files.

### 14.3 Traceability Lens

Show a CodeLens above each annotated function:

```
REQ-001 → SPEC-042 → 3 tests (OQ: 2, PQ: 1) | coverage: 97.2% | risk: HIGH
```

This requires building the full graph and caching it per workspace.

### 14.4 Auto-Complete IDs

When typing `@gxp-satisfies REQ-`, offer existing REQ IDs. When typing `@gxp-verifies SPEC-`, offer existing SPEC IDs. Build the ID list by scanning annotations at workspace open time.

---

## 15. Versioning and Forward Compatibility

### 15.1 Version Negotiation

Always read `gxpmd_version` from frontmatter. If the major version is higher than what your tool supports, emit a WARNING and proceed with best effort. If the annotation `schema_version` is higher, emit an ERROR — you may miss new tag types.

### 15.2 Extensibility Points

The v3 spec is designed for extension:

- **New edge tags**: Additional `@gxp-*` tags can be defined in future versions. Tools SHOULD ignore unrecognized tags rather than erroring.
- **New node phases**: The `phase` field on nodes is a string, not an enum. Future versions may add phases beyond the current six.
- **Custom directives**: The "Project-Specific Rules" section of GxP.MD can contain custom rules. These are human-readable and do not affect tooling unless you choose to parse them.

### 15.3 Semantic Versioning

GxP.MD follows semver. Breaking changes (new required tags, changed ID formats, removed features) bump the major version. New optional features bump the minor version. Bug fixes bump the patch version.

---

## Appendix A: Complete Data Flow

```
┌─────────────────────┐
│  GxP.MD (config)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐     ┌────────────────────┐
│  Parse Frontmatter  │     │  Scan Source Files  │
│  (risk matrix,      │     │  (walk tree, filter │
│   tags, config)     │     │   extensions, skip  │
└────────┬────────────┘     │   excluded dirs)    │
         │                   └────────┬───────────┘
         │                            │
         │                            ▼
         │                   ┌────────────────────┐
         │                   │  Parse Annotations │
         │                   │  (regex, per file) │
         │                   └────────┬───────────┘
         │                            │
         ▼                            ▼
┌──────────────────────────────────────────────┐
│              Build Traceability DAG           │
│  - Create FILE nodes for each annotated file │
│  - Create artifact nodes (REQ, US, SPEC)     │
│  - Add edges from edge tags                  │
│  - Merge artifact file edges (if present)    │
│  - Calculate coverage via BFS reachability   │
└──────────────────────┬───────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
┌───────────────┐ ┌──────────┐ ┌──────────────┐
│  Validate     │ │  Find    │ │  Analyze     │
│  Annotations  │ │  Orphans │ │  Coverage    │
│  (syntax,     │ │  (graph  │ │  (thresholds,│
│   completeness│ │   conn.) │ │   tiers)     │
└───────┬───────┘ └────┬─────┘ └──────┬───────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                       ▼
         ┌─────────────────────────┐
         │    Generate Outputs     │
         │  - traceability-matrix  │
         │  - compliance-status    │
         │  - gap-analysis         │
         │  - artifact stubs       │
         │  - exit code            │
         └─────────────────────────┘
```

---

## Appendix B: Glossary

| Term | Definition |
|------|-----------|
| **DAG** | Directed Acyclic Graph — the traceability model in v3 |
| **Edge tag** | Annotation tag that declares a relationship: `@gxp-satisfies`, `@gxp-implements`, `@gxp-verifies`, `@gxp-derives-from` |
| **Opaque ID** | An identifier whose numeric component carries no hierarchical meaning |
| **Reachability** | Whether a path exists between two nodes in the graph |
| **Harden** | The compliance formalization sweep that runs per sprint |
| **Evidence package** | Self-contained folder with test results, environment snapshot, and integrity manifests |
| **ALCOA+** | Data integrity framework: Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available |
| **Gate** | A checkpoint (pre-commit, pre-merge, per-release) where compliance conditions are validated |

---

*End of Implementer's Guide*
