---
rfc_id: RFC-002
title: "Graph-Based Traceability Model for GxP.MD v3"
status: DRAFT
author: James Gannon
date_created: 2026-02-09
category: Architecture
---

## Executive Summary

This RFC proposes a transition from GxP.MD v2.1.0's hierarchical ID-scheme traceability model to a directed acyclic graph (DAG)-based model in v3. The v2 approach encodes parent-child relationships in alphanumeric IDs (e.g., `SPEC-001-002` → `US-001-002` → `REQ-001`), which creates three critical failure modes:

1. **Impossible many-to-many relationships**: Components cannot satisfy multiple requirements without duplication
2. **False orphan detection**: Skipped phases (explicitly allowed per Section 5.4) are flagged as missing requirements
3. **Ambiguous cross-cutting coverage**: Shared components are triple-counted with unclear ownership

The DAG model replaces ID-encoded parentage with explicit edge tags (`@gxp-satisfies`, `@gxp-implements`, `@gxp-verifies`), making IDs opaque and relationships declarative. Coverage becomes reachability analysis rather than chain traversal.

---

## 1. Problem Statement

### 1.1 Current State: Hierarchical ID Scheme (v2.1.0)

In GxP.MD v2.1.0, traceability is encoded in the ID itself:

```text
REQ-001          (Regulatory Requirement)
  ├── US-001-001 (User Story)
  │   └── SPEC-001-001 (Specification)
  └── US-001-002 (User Story)
      └── SPEC-001-002 (Specification)
```

The harden tool infers this hierarchy via functions like `_spec_to_req()`:

```python
def _spec_to_req(spec_id: str) -> str:
    # "SPEC-001-002" → extract first 3 digits → "REQ-001"
    return f"REQ-{spec_id.split('-')[1]}"
```

This approach works for tree structures but breaks in practice.

### 1.2 Failure Mode #1: Impossible Many-to-Many Relationships

**Problem**: Real-world components satisfy multiple requirements, but the ID scheme forces a single parent.

**Concrete Example**:

An audit trail logging service in a pharma system must satisfy:
- REQ-001: System shall maintain immutable audit records
- REQ-002: System shall log all critical operations
- REQ-003: System shall provide forensic analysis capabilities

In v2, we must create three separate specifications:
- `SPEC-001-003`: Implements audit trail for REQ-001
- `SPEC-002-005`: Implements audit trail for REQ-002
- `SPEC-003-004`: Implements audit trail for REQ-003

Each is separate in the traceability matrix, obscuring that they're the same component. Code review, testing, and maintenance become fragmented.

**Impact**: Violates DRY principle; audit matrix becomes misleading about actual system composition.

### 1.3 Failure Mode #2: False Orphans from Skipped Phases

**Problem**: GxP.MD Section 5.4 explicitly permits LOW-risk components to skip `@gxp-req` annotation. The v2 orphan-detection tool creates phantom requirements.

**Concrete Example**:

A utility library for timestamp formatting is LOW-risk. Per section 5.4, it skips `@gxp-req`:

```python
# utility/timestamps.py
# @gxp-phase: IMPLEMENTATION
def format_iso8601(timestamp):
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
```

The `find_orphans()` function cannot parse an ID from the code because none exists. It infers a phantom `REQ-???` (unknown), then reports:

```text
ERROR: Orphan SPEC-001 has no parent REQ
Missing requirement: REQ-001
```

Even though:
1. The component skipped `@gxp-req` by design (allowed)
2. No actual requirement is missing
3. The tool created a false error

**Impact**: Audit teams disable orphan detection, losing real coverage gaps.

### 1.4 Failure Mode #3: Ambiguous Cross-Cutting Coverage

**Problem**: Shared components appear in multiple requirement chains with unclear ownership.

**Concrete Example**:

A cryptographic verification module satisfies REQ-001, REQ-002, and REQ-003. In v2:

| REQ Chain | Coverage |
|-----------|----------|
| REQ-001 chain | ✓ SPEC-001-010 (crypto module) |
| REQ-002 chain | ✓ SPEC-002-015 (same crypto module) |
| REQ-003 chain | ✓ SPEC-003-008 (same crypto module) |

Questions arise:
- Is the crypto module tested three times (wasteful)?
- Who owns the test case? (REQ-001 team? REQ-002 team?)
- If a bug is found, which requirements does it affect?
- How do we avoid triple-counting in metrics?

**Impact**: Compliance teams cannot answer ownership questions; metrics become misleading.

---

## 2. Proposed Solution: Directed Acyclic Graph Model (v3)

### 2.1 Core Principles

**IDs become opaque**:
```text
REQ-001, US-042, SPEC-137, TEST-056
```

These are identifiers, not encoded hierarchies. No structural information is derivable from the ID itself.

**Relationships are explicit**:
```text
@gxp-satisfies REQ-001, REQ-005
@gxp-implements US-042
@gxp-verifies SPEC-137
```

**Edges replace ID inference**:
Instead of parsing IDs to infer parent-child relationships, annotations define them declaratively.

### 2.2 Annotation Syntax (v3)

#### `@gxp-satisfies` (Many-to-Many)

A node satisfies one or more requirements:

```python
# service/audit.py
# @gxp-phase: IMPLEMENTATION
# @gxp-satisfies REQ-001, REQ-002, REQ-003
class AuditTrail:
    """Immutable audit log for all critical operations."""
    def log(self, event):
        pass
```

Single annotation, multiple targets. The graph explicitly shows that `AuditTrail` satisfies all three requirements.

#### `@gxp-implements` (Traceability to User Story)

A specification implements a user story:

```python
# spec/payment_processing.md
# @gxp-id: SPEC-137
# @gxp-implements US-042
# @gxp-satisfies REQ-001
```

#### `@gxp-verifies` (Test to Specification)

A test case verifies a specification:

```python
# test/payment_test.py
# @gxp-id: TEST-056
# @gxp-phase: TEST
# @gxp-verifies SPEC-137
def test_payment_deduction():
    pass
```

#### Optional `@gxp-depends-on` (Explicit Dependencies)

For non-hierarchical edges:

```python
# @gxp-id: SPEC-200
# @gxp-depends-on SPEC-137
```

### 2.3 Graph Structure

The traceability graph is a DAG with node types and edges:

```text
Nodes:
  - REQ (Regulatory Requirement)
  - US (User Story)
  - SPEC (Specification)
  - IMPL (Implementation)
  - TEST (Test Case)
  - (other phases as needed)

Edges:
  US --satisfies--> REQ
  SPEC --satisfies--> REQ
  IMPL --satisfies--> REQ
  SPEC --implements--> US
  TEST --verifies--> SPEC
  SPEC --depends-on--> SPEC
  (multi-target allowed)
```

**Example DAG: Audit Trail System**

```text
┌────────────────────────┐
│ TEST-001, TEST-002     │
│ (Unit + Integration)   │
└──────┬─────────────────┘
       │ verifies
       ↓
┌─────────────────────┐
│   IMPL-005          │ (AuditTrail class)
│   (Implementation)  │
└──────┬──────────────┘
       │ satisfies
       ↓
┌──────────────┐
│   REQ-001    │ (Immutable audit records)
│   REQ-002    │ (Log critical ops)
│   REQ-003    │ (Forensic analysis)
└──────────────┘
```

The same IMPL node has incoming edges from all three requirements. No duplication, no ambiguity.

### 2.4 Coverage Definition: Graph Reachability

**v2 Definition**: A requirement is covered if there exists a chain `REQ → US → SPEC → TEST` with all passing tests.

**v3 Definition**: A requirement is covered if there exists a path in the DAG:
```text
covered(REQ-001) = ∃ undirected_path(REQ-001 ↔ node)
  where node.phase ∈ {TEST, VALIDATION}
  ∧ node.result = PASS
```

**Why this works**:
- Paths can flow through any node type
- Many-to-many edges are natural
- Skipped phases = shorter paths (valid, not errors)
- Shared components appear once with clear ownership

### 2.5 Handling Skipped Phases (Section 5.4)

In v3, a LOW-risk component that skips `@gxp-req` is simply a node without incoming requirement edges:

```python
# utility/timestamps.py
# @gxp-id: UTIL-001
# @gxp-phase: IMPLEMENTATION
# (no @gxp-satisfies annotation)
def format_iso8601(timestamp):
    return timestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
```

The orphan detection algorithm:

```python
def find_orphans_v3(graph: DAG) -> List[Node]:
    """Find nodes with no incoming edges from REQ."""
    orphans = []
    for node in graph.nodes:
        if node.phase in {IMPLEMENTATION, TEST}:
            # Check for path from any REQ
            if not has_path_from_req(node):
                # Only flag if EXPECTED to have one (per risk level)
                if node.risk_level >= MEDIUM:
                    orphans.append(node)
    return orphans
```

**Result**: LOW-risk utility components are not flagged as errors. MEDIUM/HIGH components without requirement tracing are still caught.

---

## 3. Migration Path: v2.1.0 → v3

### 3.1 Automated Conversion Script

```python
def migrate_v2_to_v3(v2_annotations: Dict) -> Dict:
    """Convert v2 ID-based scheme to v3 explicit edges."""
    v3_annotations = {}

    for entity_id, metadata in v2_annotations.items():
        v3_annotations[entity_id] = {
            'id': entity_id,  # opaque, no structural info
            'phase': metadata['phase'],
            'edges': []
        }

        # Parse v2 ID to infer v3 edges
        if entity_id.startswith('SPEC-'):
            # SPEC-001-002 → infer REQ-001
            req_id = f"REQ-{entity_id.split('-')[1]}"
            v3_annotations[entity_id]['edges'].append({
                'type': 'satisfies',
                'source': entity_id,
                'target': req_id
            })

        # (Similar logic for US, etc.)

    return v3_annotations
```

**Step 1**: Scan all GxP annotations in codebase
**Step 2**: Extract implicit relationships via ID parsing
**Step 3**: Generate explicit `@gxp-satisfies`, `@gxp-implements` tags
**Step 4**: Manual review and disambiguation (handle many-to-many cases)
**Step 5**: Remove ID-encoding assumptions from harden tool

### 3.2 Rollout Timeline

- **Week 1-2**: Develop and test automated converter
- **Week 3**: Run on pilot project; manual review
- **Week 4**: Gather feedback; update harden tool to support v3 edges
- **Week 5**: Full rollout; maintain v2 backward compatibility layer
- **Week 6+**: Monitor; deprecate v2-specific code paths

### 3.3 Backward Compatibility Layer

During transition, the harden tool can support both:

```python
class TraceabilityParser:
    def __init__(self, strict_v3=False):
        self.strict_v3 = strict_v3

    def parse_edges(self, node) -> List[Edge]:
        edges = []

        # Parse v3 explicit edges (preferred)
        if '@gxp-satisfies' in node.annotations:
            edges.extend(self._parse_gxp_satisfies(node))

        # Fall back to v2 ID inference (if not strict_v3)
        if not self.strict_v3 and not edges:
            edges.extend(self._infer_v2_edges(node))

        return edges
```

**Policy**:
- v3 annotations take precedence
- v2 inference is a fallback (logs warnings)
- In strict mode, v2 inference is forbidden (enforces migration)

---

## 4. Technical Specification

### 4.1 Graph Representation

```python
@dataclass
class Node:
    id: str           # Opaque: REQ-001, SPEC-137, etc.
    phase: str        # REQUIREMENT, SPEC, IMPLEMENTATION, TEST, VALIDATION
    risk_level: str   # LOW, MEDIUM, HIGH
    status: str       # DRAFT, APPROVED, IMPLEMENTED, TESTED, VERIFIED
    result: Optional[str]  # PASS, FAIL, SKIPPED (for TEST/VALIDATION)

@dataclass
class Edge:
    source: Node
    target: Node
    relation: str     # 'satisfies', 'implements', 'verifies', 'depends-on'

class TraceabilityDAG:
    nodes: Dict[str, Node]
    edges: List[Edge]

    def add_node(self, node: Node):
        self.nodes[node.id] = node

    def add_edge(self, source_id: str, target_id: str, relation: str):
        self.edges.append(Edge(
            source=self.nodes[source_id],
            target=self.nodes[target_id],
            relation=relation
        ))

    def is_covered(self, req_id: str, phases: List[str] = ['TEST']) -> bool:
        """Check if REQ is reachable to PASS node in given phases."""
        req_node = self.nodes.get(req_id)
        if not req_node:
            return False

        visited = set()
        return self._dfs_reachable(req_node, phases, visited)

    def _dfs_reachable(self, node: Node, target_phases: List[str],
                       visited: set) -> bool:
        if node.id in visited:
            return False
        visited.add(node.id)

        # Found a passing test/validation
        if node.phase in target_phases and node.result == 'PASS':
            return True

        # Continue traversal
        for edge in self.edges:
            if edge.source.id == node.id:
                if self._dfs_reachable(edge.target, target_phases, visited):
                    return True

        return False

    def find_orphans_v3(self, min_risk: str = 'MEDIUM') -> List[Node]:
        """Find nodes with no incoming REQ edges (for MEDIUM+ risk)."""
        RISK_ORDER = {'LOW': 0, 'MEDIUM': 1, 'HIGH': 2}
        min_level = RISK_ORDER[min_risk]
        orphans = []

        for node in self.nodes.values():
            if RISK_ORDER.get(node.risk_level, 0) < min_level:
                continue  # Skip LOW-risk (allowed to be orphans)

            has_req_parent = any(
                edge.target.id == node.id and
                'REQ-' in edge.source.id
                for edge in self.edges
            )

            if not has_req_parent:
                orphans.append(node)

        return orphans
```

### 4.2 Annotation Parsing

```python
import re

def parse_gxp_annotations(source_code: str) -> Dict[str, List[str]]:
    """Extract @gxp-* tags from source code."""
    annotations = {}

    # Match @gxp-satisfies REQ-001, REQ-002, REQ-003
    satisfies_match = re.search(
        r'@gxp-satisfies\s+(.+)',
        source_code
    )
    if satisfies_match:
        targets = [t.strip() for t in satisfies_match.group(1).split(',')]
        annotations['gxp-satisfies'] = targets

    # Match @gxp-phase: IMPLEMENTATION
    phase_match = re.search(r'@gxp-phase:\s+(\w+)', source_code)
    if phase_match:
        annotations['gxp-phase'] = phase_match.group(1)

    # Match @gxp-id: SPEC-137
    id_match = re.search(r'@gxp-id:\s+(\S+)', source_code)
    if id_match:
        annotations['gxp-id'] = id_match.group(1)

    return annotations
```

### 4.3 Coverage Report Generation

```python
def generate_coverage_report(dag: TraceabilityDAG) -> str:
    """Generate human-readable coverage matrix."""
    report = "# Traceability Coverage Report (v3 DAG)\n\n"

    req_nodes = [n for n in dag.nodes.values() if n.id.startswith('REQ-')]

    for req in sorted(req_nodes, key=lambda n: n.id):
        is_covered = dag.is_covered(req.id)
        status = "✓ COVERED" if is_covered else "✗ NOT COVERED"

        report += f"## {req.id}: {status}\n"

        # Find all paths from REQ to TEST (requires find_paths implementation)
        # find_paths returns a list of lists of Nodes representing each path
        paths = dag.find_paths(req.id, target_phases=['TEST'])
        for path in paths:
            path_str = " → ".join([n.id for n in path])
            report += f"  Path: {path_str}\n"

        report += "\n"

    return report
```

---

## 5. Example Migration

### 5.1 Before (v2.1.0)

**Requirement**:
```yaml
id: REQ-001
title: Immutable Audit Trail
```

**Specification**:
```python
# @gxp-id: SPEC-001-001
# @gxp-phase: SPEC
class AuditLog:
    pass
```

**Implementation** (also for REQ-002, REQ-003):
```python
# @gxp-id: SPEC-001-001  (reused)
# @gxp-phase: IMPLEMENTATION
class AuditLog:
    def log(self, event): pass
```

**Test**:
```python
# @gxp-id: SPEC-001-001  (reused)
# @gxp-phase: TEST
def test_audit_log(): pass
```

**Problems**:
- ID reuse is confusing
- Ambiguous ownership (whose test? whose implementation?)
- Triple-counted in coverage reports

### 5.2 After (v3)

**Requirement** (unchanged):
```yaml
id: REQ-001
id: REQ-002
id: REQ-003
```

**Specification**:
```python
# @gxp-id: SPEC-010
# @gxp-phase: SPEC
# @gxp-satisfies REQ-001, REQ-002, REQ-003
class AuditLogSpec:
    """Specification for immutable audit trail."""
    pass
```

**Implementation**:
```python
# @gxp-id: IMPL-010
# @gxp-phase: IMPLEMENTATION
# @gxp-satisfies REQ-001, REQ-002, REQ-003
class AuditLog:
    def log(self, event): pass
```

**Test**:
```python
# @gxp-id: TEST-010
# @gxp-phase: TEST
# @gxp-verifies SPEC-010
def test_audit_log(): pass
```

**Graph**:
```text
REQ-001 ──┐
REQ-002 ──┼──> SPEC-010 ──> IMPL-010 ──> TEST-010 (PASS)
REQ-003 ──┘
```

**Advantages**:
- Clear many-to-many relationship
- Single node per component
- Explicit edge relationships
- Unambiguous coverage

---

## 6. Backward Compatibility & Deprecation

### 6.1 Transition Support

The harden tool (v3.0) will include:

```python
# harden/traceability.py

class LegacyV2Adapter:
    """Support v2 ID-based schemes during migration."""

    def convert_to_v3(self, v2_node) -> Dict:
        """Convert v2 implicit edges to v3 explicit edges."""
        edges = self._infer_edges_from_id(v2_node.id)
        return {
            'id': v2_node.id,
            'edges': edges,
            'legacy_warning': True
        }

class StrictV3Enforcer:
    """Reject v2 patterns once migration is complete."""

    def validate(self, node):
        if self._has_encoded_hierarchy(node.id):
            raise ValueError(
                f"{node.id} uses v2 ID encoding. "
                "Use explicit @gxp-satisfies, @gxp-implements tags instead."
            )
```

### 6.2 Feature Flags

```yaml
# config/gxp.yaml
traceability:
  schema_version: "v3"
  strict_mode: false  # Set true in week 6 to enforce v3
  legacy_adapter: true  # Fallback to v2 inference if annotation missing
```

### 6.3 Deprecation Timeline

| Phase | Timeline | Action |
|-------|----------|--------|
| Phase 1 (Weeks 1-4) | Now | v3 support added; v2 still works |
| Phase 2 (Weeks 5-8) | +4 weeks | v2 inference logs warnings |
| Phase 3 (Week 9) | +8 weeks | v2 inference disabled by default |
| Phase 4 (Week 10+) | +9 weeks | v2 inference removed entirely |

---

## 7. Risk Assessment

### 7.1 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Migration tool misses relationships | Medium | High | Manual audit + test coverage checks |
| Performance degradation (graph traversal) | Low | Medium | Cache reachability results; profile before deploy |
| Ambiguity in edge semantics | Low | Medium | Document edge types; review in PRs |
| Incomplete adoption (mixed v2/v3) | High | Medium | Strict mode; automated checking in CI |

### 7.2 Testing Strategy

1. **Unit Tests**: Parse v3 annotations; validate DAG structure
2. **Migration Tests**: Run converter on pilot project; verify coverage unchanged
3. **Performance Tests**: Measure graph traversal time for large projects
4. **Audit Tests**: Spot-check coverage reports against manual review

---

## 8. Future Enhancements

### 8.1 Potential v3.1+ Features

- **Weighted edges**: Different confidence levels for relationships
- **Conditional coverage**: "Covered if X dependency is included"
- **Dynamic risk assessment**: Risk level updated based on test coverage
- **Change impact analysis**: Trace which requirements are affected by code changes

### 8.2 Integration Points

- CI/CD: Block PRs if requirements become uncovered
- Compliance dashboards: Real-time traceability visualizations
- Audit export: Generate compliance matrices for regulators

---

## 9. References & Related RFCs

- **RFC-001**: Initial GxP.MD Specification (Section 5.4 on risk-based skipping)
- **GxP.MD Spec v2.1.0**: Hierarchical traceability model (to be superseded)
- **FDA 21 CFR Part 11**: Audit trail requirements (motivates cross-cutting coverage)

---

## 10. Conclusion

The v3 DAG model removes ID-encoding constraints, enabling many-to-many relationships, cleaner handling of skipped phases, and unambiguous cross-cutting coverage. With a clear migration path and backward compatibility layer, the transition is low-risk and high-benefit for audit teams and developers.

---

## Appendix A: Extended Example - Payment Processing

### Scenario
A pharma system processes payments for clinical trial participant compensation. Requirements span security (REQ-101), auditability (REQ-102), and accuracy (REQ-103).

### v2 Problem
```text
REQ-101 chain: SPEC-101-001, SPEC-101-002
REQ-102 chain: SPEC-102-001, SPEC-102-002
REQ-103 chain: SPEC-103-001, SPEC-103-002

Crypto validation component appears in SPEC-101-001 and SPEC-102-001
(same code, different IDs—confusing)
```

### v3 Solution
```text
Nodes:
  REQ-101: Security (encryption, key management)
  REQ-102: Auditability (log all transactions)
  REQ-103: Accuracy (amount verification, rounding)
  SPEC-010: Payment validation spec
  IMPL-010: PaymentValidator class
  TEST-010: test_payment_validation
  IMPL-020: CryptoValidator class
  TEST-020: test_crypto_validation

Edges:
  IMPL-010 --satisfies--> REQ-101
  IMPL-010 --satisfies--> REQ-102
  IMPL-010 --satisfies--> REQ-103
  IMPL-010 --depends-on--> IMPL-020
  TEST-010 --verifies--> IMPL-010
  TEST-020 --verifies--> IMPL-020

Coverage(REQ-101) = true if TEST-010 and TEST-020 both pass
```

**Result**: One PaymentValidator, one CryptoValidator, clear ownership, unambiguous coverage.

---

## Appendix B: Annotation Reference Card

```text
# Regulatory Requirement
# @gxp-id: REQ-001
# @gxp-phase: REQUIREMENT
# @gxp-risk: HIGH
Requirement text here

# User Story (satisfies requirement)
# @gxp-id: US-010
# @gxp-phase: SPEC
# @gxp-satisfies REQ-001, REQ-002
Description of user story

# Specification
# @gxp-id: SPEC-010
# @gxp-implements US-010
# @gxp-phase: SPEC
def validate_input():
    pass

# Implementation (may directly satisfy requirement)
# @gxp-id: IMPL-010
# @gxp-satisfies REQ-001
# @gxp-phase: IMPLEMENTATION
class Validator:
    pass

# Test (verifies specification or implementation)
# @gxp-id: TEST-010
# @gxp-verifies SPEC-010, IMPL-010
# @gxp-phase: TEST
def test_validator():
    assert True

# Low-risk utility (skips @gxp-satisfies)
# @gxp-id: UTIL-001
# @gxp-phase: IMPLEMENTATION
def format_date(d):
    return d.isoformat()
```

