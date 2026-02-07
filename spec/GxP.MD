---
# GxP.MD v2.0.0 — Annotation-First Compliance for AI Coding Agents
# Copyright 2026 PharmaLedger Association. All rights reserved.
gxpmd_version: "2.0.0"

project:
  name: ""                    # Human-readable product name
  id: ""                      # Unique product identifier
  version: ""                 # Current semantic version (MAJOR.MINOR.PATCH)
  owner: ""                   # Quality-responsible individual or team
  contact: ""                 # Email or distribution list for quality issues

regulatory:
  profile: pharma-standard    # pharma-standard | medical-device | clinical-trial | laboratory
  jurisdictions:
    - FDA
    - EMA
  frameworks:
    - "21 CFR Part 11"
    - "EU Annex 11"
  gamp_category: 5

risk:
  overall: HIGH
  matrix:
    HIGH:
      coverage_threshold: 95
      required_tiers:
        - IQ
        - OQ
        - PQ
      signing_required: false
      review_required: true
    MEDIUM:
      coverage_threshold: 80
      required_tiers:
        - OQ
        - PQ
      signing_required: false
      review_required: false
    LOW:
      coverage_threshold: 60
      required_tiers:
        - OQ
      signing_required: false
      review_required: false

annotations:
  schema_version: "1.0"
  required_tags:
    source:
      - "@gxp-req"
      - "@gxp-spec"
      - "@gxp-risk"
    test:
      - "@gxp-spec"
      - "@trace"
      - "@test-type"
      - "@gxp-risk"
  format: block_comment        # block_comment | decorator | companion_file

artifacts:
  directory: .gxp
  engine: none                 # rosie | custom | none
  formal_artifacts: optional   # required | optional | none
  traceability_enforcement: strict  # strict | warn | off

gates:
  pre_commit:
    - annotations_valid
    - no_untagged_gxp_code
  pre_merge:
    - all_tests_pass
    - coverage_meets_threshold
    - review_complete_if_required
    - no_orphan_annotations
  per_release:
    - harden_sweep_complete
    - traceability_matrix_current
    - evidence_packages_complete
    - compliance_status_generated
    - risk_assessment_current

harden:
  frequency: per_sprint        # per_sprint | per_release | manual
  outputs:
    - traceability_matrix
    - compliance_status_report
    - evidence_packages
    - gap_analysis

alcoa:
  attributable:
    enforce: true
    method: git_author
  legible:
    enforce: true
    method: markdown_lint
  contemporaneous:
    enforce: true
    method: commit_timestamp
  original:
    enforce: true
    method: jws_signature
  accurate:
    enforce: true
    method: system_state_hash

evidence:
  capture: ci_native           # ci_native | agent_manual | hybrid
  retention_days: 90
  signing_algorithm: ES256
  state_hash:
    algorithm: SHA-256
    scope: /src
    excludes:
      - node_modules
      - ".*"
      - "*.log"
      - dist

agent:
  mode: risk_proportionate     # strict | risk_proportionate | advisory
---

# GxP.MD Specification

**Version 2.0.0**

## Abstract

GxP.MD v2.0.0 is an annotation-first compliance instruction standard for AI coding agents operating on software systems subject to Good Practice (GxP) regulations in the pharmaceutical and life sciences industries.

A GxP.MD file is a single markdown document placed at the root of a software project. It contains machine-readable configuration in YAML frontmatter and human-readable behavioral directives in the markdown body. AI agents discover this file by convention, parse the configuration to understand the regulatory context, and follow the directives to produce compliant code, annotations, tests, and evidence.

Version 2.0.0 introduces three foundational changes from v1:

1. **Compliance-as-Code.** Traceability lives in structured code annotations during active development, not in a parallel documentation system. Separate artifact files are optional depth for complex or high-risk components.
2. **Gate Enforcement Over Process Enforcement.** The specification defines what must be true at each quality gate, not how the agent must work. Agents are free to code first and annotate later, or plan first and code later, as long as gates pass.
3. **Two-Mode System.** Development operates in `develop` mode (lightweight, annotation-driven) or `harden` mode (per-sprint compliance formalization). There is no separate audit mode. Harden IS audit-readiness, and it runs every sprint.

GxP.MD builds on the ROSIE RFC-001 artifact and evidence standard but does not require it. Projects using ROSIE tooling benefit from automated enforcement; projects without ROSIE enforce compliance through CI gates and manual review.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

---

## 1. Core Principles

### 1.1 Traceability is Law

The V-Model defines the shape of traceability in GxP-regulated software. Every piece of production code traces backward through a specification, a user story, and a requirement. Every test traces forward to the specification it verifies. The chain is:

```
REQ  -->  US  -->  SPEC  -->  SOURCE CODE  -->  TEST  -->  EVIDENCE
```

This chain MUST be complete for all GxP-relevant functionality. However, HOW this chain is maintained is flexible. In GxP.MD v2, traceability lives primarily in structured code annotations rather than in separate artifact files. The V-Model defines the required relationships; annotations express them.

The V-Model phases remain:

1. **Requirements** define WHAT the system must do. Each requirement receives a unique `REQ-{NNN}` identifier.
2. **User Stories** define WHO needs the capability and WHY. Each user story receives a `US-{NNN}-{NNN}` identifier linking it to its parent requirement.
3. **Specifications** define HOW each user story will be implemented. Each specification receives a `SPEC-{NNN}-{NNN}` identifier linking it to its parent user story.
4. **Implementation** is the source code itself. Source files carry `@gxp-req`, `@gxp-spec`, and `@gxp-risk` annotations linking them to their governing artifacts.
5. **Verification** proves that the implementation satisfies its specification. Tests carry `@gxp-spec`, `@trace`, `@test-type`, and `@gxp-risk` annotations and produce evidence packages.

A complete annotation chain looks like this:

```typescript
// In src/auth/login.ts:
/**
 * @gxp-req REQ-001 "System shall authenticate users via secure credential exchange"
 * @gxp-spec SPEC-001-001 "OAuth2 PKCE flow implementation"
 * @gxp-risk HIGH
 */

// In tests/oq/auth/login.test.ts:
/**
 * @gxp-spec SPEC-001-001
 * @trace US-001-001
 * @test-type OQ
 * @gxp-risk HIGH
 */
```

REQ-001 is the requirement. US-001-001 is the user story derived from it. SPEC-001-001 is the specification derived from the user story. The source file implements SPEC-001-001 and declares its governing requirement. The test file verifies SPEC-001-001 and traces to US-001-001. The chain is complete.

### 1.2 Annotations are Source of Truth

During active development, structured code annotations ARE the compliance record. The source code and test files, with their embedded annotations, constitute the primary traceability artifact.

This design eliminates drift. When traceability metadata lives in separate `.gxp/requirements/`, `.gxp/user_stories/`, and `.gxp/specs/` files, those files can diverge from the actual code. When annotations live IN the code, they move with the code, are reviewed with the code, and are versioned with the code.

Separate artifact files in `.gxp/` are OPTIONAL depth, not mandatory overhead:

- For HIGH risk components with complex regulatory justification, a formal `REQ-NNN.md` file provides space for regulatory basis, acceptance criteria, and detailed risk rationale that would be unwieldy as an annotation.
- For MEDIUM and LOW risk components, annotations alone are typically sufficient.
- During harden mode, formal documents are generated FROM annotations when separate files do not exist, ensuring the compliance record is always complete.

An agent MUST NOT maintain a parallel documentation system that duplicates what annotations already express. The annotation is the source of truth. Formal documents elaborate on it.

### 1.3 Gates Over Process

GxP.MD v2 does NOT prescribe a development workflow. It does not say "before writing code, create a specification file." It says "before merging, all code must have valid annotations and passing tests."

Compliance is enforced at three gate levels:

- **Pre-commit gates** validate annotation syntax and completeness.
- **Pre-merge gates** validate test pass status, coverage thresholds, and review requirements.
- **Per-release gates** validate traceability completeness, evidence formalization, and compliance status.

The specification tells agents WHAT must be true at each gate, not HOW to arrive there. An agent MAY:

- Code first and annotate before committing.
- Write annotations and tests first, then implement.
- Generate annotations from existing code during a migration.
- Use any internal reasoning or planning process.

All of these approaches are equally valid, provided the gates pass. This gives agents maximum effectiveness while maintaining regulatory rigor.

### 1.4 Risk-Proportionate Enforcement

Risk assessment is a continuous obligation, not a one-time activity. Every change that touches GxP-relevant functionality MUST be evaluated against the risk matrix defined in the frontmatter.

Risk levels are determined by the potential impact on regulated outcomes:

| Risk Level | Impact Domain | Examples |
|------------|--------------|---------|
| **HIGH** | Patient safety, product quality, PHI/PII data integrity | Authentication, dosage calculations, audit trails, data encryption, electronic signatures |
| **MEDIUM** | Regulated workflows, critical metadata, operational integrity | Batch processing, report generation, notification systems, role management |
| **LOW** | Non-GxP functionality, cosmetic elements, developer tooling | UI theming, internal dashboards, documentation sites, developer utilities |

Enforcement scales with risk level via the risk matrix in the frontmatter. HIGH risk components require the highest coverage thresholds, all verification tiers, and peer review. LOW risk components require only basic coverage and OQ-tier testing. The matrix is configurable per project.

### 1.5 Contemporaneous Compliance (ALCOA)

Compliance state MUST be demonstrated per sprint, iteration, or minor release — as configured by `harden.frequency`. This is a non-negotiable requirement derived from the ALCOA Contemporaneous principle: records must be created at the time of the activity, not retroactively.

The implications are:

- Every harden cycle produces a compliance snapshot: traceability matrix, compliance status report, evidence packages, and gap analysis.
- If an auditor arrives on any given day, the last harden output is the compliance record. There is no "audit preparation" phase because the last harden IS the audit record.
- Deferring compliance documentation to a pre-release or pre-audit batch activity violates ALCOA Contemporaneous. The work happened during the sprint; the compliance record MUST also be produced during the sprint.
- Harden mode runs at a defined cadence. It is a continuous obligation, not a batch activity.

There is no separate "audit mode." Harden IS the audit-readiness mode, and it runs every sprint.

### 1.6 Agent Agnosticism

GxP.MD is designed to be consumed by any AI coding agent — Claude, GPT, Gemini, Copilot, or any future system capable of reading markdown and YAML. Directives in this specification use plain language and standard formats. No agent-specific features, APIs, or capabilities are assumed.

Agents that cannot fulfill a MUST-level directive SHOULD halt and report the gap to the human operator rather than silently proceeding without compliance.

---

## 2. Annotation Schema

Annotations are the core mechanism by which GxP.MD v2 maintains traceability. This section defines the annotation tags, their syntax, and their placement rules.

### 2.1 Source File Annotations

Every source file implementing GxP-relevant logic MUST include annotations linking it to the governing requirements, specifications, and risk level.

#### Required Tags

| Tag | Format | Description |
|-----|--------|-------------|
| `@gxp-req` | `@gxp-req REQ-NNN` or `@gxp-req REQ-NNN "description"` | Links the source file to its governing requirement |
| `@gxp-spec` | `@gxp-spec SPEC-NNN-NNN` or `@gxp-spec SPEC-NNN-NNN "description"` | Links the source file to its governing specification |
| `@gxp-risk` | `@gxp-risk HIGH\|MEDIUM\|LOW` | Declares the risk classification of the component |

#### Optional Tags

| Tag | Format | Description |
|-----|--------|-------------|
| `@gxp-story` | `@gxp-story US-NNN-NNN` | Links the source file to a user story |

#### Format Examples

**TypeScript / JavaScript:**

```typescript
/**
 * @gxp-req REQ-001 "System shall authenticate users via secure credential exchange"
 * @gxp-spec SPEC-001-001 "OAuth2 PKCE flow implementation"
 * @gxp-risk HIGH
 */
export async function authenticateUser(credentials: LoginCredentials): Promise<AuthResult> {
  // implementation
}
```

**Python:**

```python
# @gxp-req REQ-003 "System shall validate batch records against schema"
# @gxp-spec SPEC-003-001 "JSON Schema validation for batch payloads"
# @gxp-risk MEDIUM
def validate_batch_record(record: dict, schema: dict) -> ValidationResult:
    # implementation
```

**Language-agnostic block comment:**

```
/*
 * @gxp-req REQ-005 "System shall encrypt PHI at rest"
 * @gxp-spec SPEC-005-001 "AES-256-GCM encryption for database fields"
 * @gxp-risk HIGH
 */
```

#### Tag Placement Rules

- Tags MUST appear in a block comment at the top of the file or immediately preceding the function, class, or module they govern.
- A single file MAY contain multiple annotation blocks if it implements multiple specifications. Each block governs the code that immediately follows it.
- Tags MUST use the exact format specified. Deviations (e.g., missing hyphens, incorrect casing of risk levels) will cause annotation validation failures at the pre-commit gate.
- The optional description string in `@gxp-req` and `@gxp-spec` SHOULD be included for readability but is not required. When omitted, the ID alone is sufficient for traceability.

### 2.2 Test File Annotations

Every test file verifying GxP-relevant functionality MUST include annotations linking it to the specification it verifies, the traceability chain, and the risk level.

#### Required Tags

| Tag | Format | Description |
|-----|--------|-------------|
| `@gxp-spec` | `@gxp-spec SPEC-NNN-NNN` | Links the test to the specification it verifies |
| `@trace` | `@trace US-NNN-NNN` | Links the test to the user story it validates |
| `@test-type` | `@test-type IQ\|OQ\|PQ` | Declares the verification tier |
| `@gxp-risk` | `@gxp-risk HIGH\|MEDIUM\|LOW` | Declares the risk level of the tested component |

#### Example (TypeScript / Vitest)

```typescript
/**
 * @gxp-spec SPEC-001-001
 * @trace US-001-001
 * @test-type OQ
 * @gxp-risk HIGH
 */
describe("User authentication - OAuth2 PKCE login flow", () => {
  it("should reject invalid credentials with 401 and audit trail entry", () => {
    // test implementation
  });

  it("should issue access token with correct scopes on valid credentials", () => {
    // test implementation
  });

  it("should create audit trail entry on successful login", () => {
    // test implementation
  });
});
```

#### Tag Placement

- Tags MUST appear in a block comment at the top of the test file or immediately preceding the `describe` block they govern.
- A single test file MAY contain multiple tag blocks if it covers multiple specifications. Each block governs the `describe` block that immediately follows it.

### 2.3 The Traceability Chain Through Annotations

Annotations form the V-Model traceability chain without requiring separate artifact files. The chain works as follows:

```
Source file (src/auth/login.ts):
  @gxp-req REQ-001           --> Requirement: "System shall authenticate users"
  @gxp-spec SPEC-001-001     --> Specification: "OAuth2 PKCE flow"
  @gxp-risk HIGH              --> Risk classification

Test file (tests/oq/auth/login.test.ts):
  @gxp-spec SPEC-001-001     --> Verifies the same specification
  @trace US-001-001           --> Traces to user story
  @test-type OQ               --> Verification tier
  @gxp-risk HIGH              --> Risk classification
```

The chain reads: REQ-001 is the governing requirement. US-001-001 is a user story derived from REQ-001 (the relationship is implicit in the ID scheme: US-001-xxx belongs to REQ-001). SPEC-001-001 is the specification derived from US-001-001 (SPEC-001-xxx belongs to US-001-xxx, which belongs to REQ-001). The source file declares it implements REQ-001 and SPEC-001-001. The test file declares it verifies SPEC-001-001 and traces to US-001-001.

When `traceability_enforcement` is set to `strict`:

- Every source file containing GxP-relevant logic MUST include at least `@gxp-spec` and `@gxp-risk` annotations.
- Every test file MUST include `@gxp-spec`, `@trace`, `@test-type`, and `@gxp-risk` annotations.
- No annotation MAY reference an ID that has no corresponding source file, test file, or formal artifact file.
- The traceability matrix generated during harden mode MUST resolve every annotation to a complete chain.

When `traceability_enforcement` is set to `warn`, violations produce warnings but do not block workflow progression. When set to `off`, traceability is not enforced.

### 2.4 When to Use Formal Artifact Files

Annotations are the primary traceability mechanism, but formal artifact files in `.gxp/` provide additional depth when the complexity or risk of a component warrants it.

**Requirements (`REQ-NNN.md`): RECOMMENDED for HIGH risk.**
Requirements define WHAT the system must do. This conceptually exists before code — regulatory obligations, business rules, and quality attributes have a source independent of implementation. A separate `REQ-NNN.md` in `.gxp/requirements/` provides space for:
- Regulatory basis and citations
- Detailed acceptance criteria
- Risk justification and impact analysis
- Relationship to other requirements

For LOW and MEDIUM risk components, the `@gxp-req REQ-NNN "description"` annotation in source code is sufficient. The requirement exists; it is simply expressed inline.

**User Stories (`US-NNN-NNN.md`): OPTIONAL.**
For many teams, the ticket, issue, or backlog item combined with the `@trace US-NNN-NNN` annotation in test files provides sufficient traceability. A separate user story file adds value when detailed acceptance criteria or given/when/then scenarios need formal documentation.

**Specifications (`SPEC-NNN-NNN.md`): OPTIONAL for LOW/MEDIUM risk.**
For HIGH risk components with complex design rationale, a separate `SPEC-NNN-NNN.md` in `.gxp/specs/` adds value by documenting design approach, data flows, security considerations, and API contracts. For simple features at LOW or MEDIUM risk, the annotation description combined with the code itself IS the specification.

**Harden mode generates formal documents from annotations when separate files do not exist.** This ensures the compliance record is always complete at sprint boundaries, regardless of whether the team maintains formal artifact files during development.

---

## 3. Develop Mode

Develop mode is the day-to-day operating mode. It is lightweight and annotation-driven. The agent writes code, adds annotations, writes tests, and passes gates.

### 3.1 Session Start Protocol

When an AI agent begins a development session on a project containing a GxP.MD file, it MUST:

1. **Read GxP.MD** at the project root. Parse the YAML frontmatter to load regulatory context, risk configuration, annotation requirements, and gate definitions.
2. **Read `.gxp/system_context.md`** if it exists, to understand system description, boundaries, and intended use.
3. **Understand the risk level** of the area being modified. Check the risk matrix and any component-level risk annotations already present in the code.

The agent SHOULD report any noteworthy findings (e.g., a component marked HIGH risk, an incomplete annotation chain in the area being modified) to the human operator before proceeding.

The session start protocol is intentionally minimal. The agent does not need to scan every artifact directory, run a full traceability audit, or read every file in `.gxp/`. It reads the configuration and gets oriented to the relevant area.

### 3.2 Writing Code

While writing implementation code, the agent MUST:

1. **Add annotations.** Every source file implementing GxP-relevant logic MUST include `@gxp-req`, `@gxp-spec`, and `@gxp-risk` annotations as defined in Section 2.1. Annotations MAY be added during coding or immediately after, as long as they are present before the pre-commit gate runs.

2. **Risk-assess the component.** Determine the risk level (HIGH, MEDIUM, LOW) of the component being modified based on the risk taxonomy in Section 1.4. Apply the enforcement rules corresponding to that risk level.

3. **Preserve existing annotations.** The agent MUST NOT remove or modify existing annotations unless the traceability mapping has genuinely changed.

4. **Update the risk assessment log when needed.** If the change introduces a new risk vector (e.g., a new external dependency, a new data flow involving PHI, a change to authentication logic), the agent MUST add an entry to `.gxp/risk_assessment.log`.

The agent is NOT required to:

- Create separate artifact files in `.gxp/requirements/`, `.gxp/user_stories/`, or `.gxp/specs/` before writing code. Annotations are sufficient for gate passage.
- Follow a prescribed planning workflow. The agent MAY plan extensively or code directly, as long as gates pass.
- Maintain a separate documentation system that parallels the code.

### 3.3 Writing Tests

Tests are the verification arm of the traceability chain. All test files for GxP-relevant functionality MUST include the annotations defined in Section 2.2.

Tests MUST be organized by verification tier in the project's test directory structure:

```
tests/
├── iq/                    # Installation Qualification
│   ├── dependencies.test.ts
│   ├── health-check.test.ts
│   └── migrations.test.ts
├── oq/                    # Operational Qualification
│   ├── auth/
│   │   ├── login.test.ts
│   │   └── session.test.ts
│   └── data/
│       └── validation.test.ts
└── pq/                    # Performance Qualification
    ├── auth/
    │   └── login.e2e.ts
    └── workflows/
        └── batch-processing.e2e.ts
```

#### Tier Definitions

**IQ (Installation Qualification):**
Verifies that the system is installed correctly and all dependencies are present and compatible.
- Dependency tree integrity (lock file matches, no missing packages)
- Health check endpoints respond correctly
- Database migrations apply cleanly
- Environment configuration is valid
- Service connectivity (database, cache, external APIs)

**OQ (Operational Qualification):**
Verifies that the system functions correctly according to its specifications under normal operating conditions.
- Unit tests for individual functions and modules
- Integration tests for component interactions
- API contract tests for endpoint behavior
- Input validation and error handling
- Business logic correctness

**PQ (Performance Qualification):**
Verifies that the system performs acceptably in conditions approximating real-world use.
- End-to-end tests simulating user workflows
- Visual regression tests
- Performance traces and timing assertions
- Load tests under expected concurrency
- Accessibility compliance tests (where applicable)

Evidence capture is CI-native. The test runner produces output; CI captures it. The agent does not manually create `metadata.json` or `environment.json` files during development. Evidence is formalized during harden mode from CI output.

### 3.4 Gate Enforcement (Develop Mode)

Gates are the primary compliance enforcement mechanism. They validate that the codebase meets compliance requirements at defined checkpoints.

#### Pre-Commit Gate

Checked before every commit. These gates ensure annotation hygiene at the individual change level.

- **Annotations valid.** All `@gxp-req`, `@gxp-spec`, `@gxp-risk`, `@gxp-story`, `@trace`, and `@test-type` annotations in modified files conform to the formats defined in Section 2. Syntactically invalid annotations block the commit.
- **No untagged GxP code.** All modified source files containing GxP-relevant logic include at least `@gxp-spec` and `@gxp-risk` annotations. A source file that implements regulated functionality without annotations is non-compliant.

#### Pre-Merge Gate

Checked before merging a feature branch into the main branch. These gates ensure verification is complete.

- **All tests pass.** All tests for the affected components across all required verification tiers (as defined by the risk matrix) execute successfully. Zero failures.
- **Coverage meets threshold.** Test coverage for every modified component meets or exceeds the threshold defined for its risk level in the risk matrix.
- **Review complete if required.** For components where `review_required` is `true` at the component's risk level, at least one qualified reviewer has approved the changes.
- **No orphan annotations.** All annotation IDs in modified files resolve to either (a) a corresponding annotation in another file (e.g., a `@gxp-spec` in a source file has a matching `@gxp-spec` in a test file) or (b) a formal artifact file in `.gxp/`. An annotation referencing a non-existent ID is orphaned and blocks the merge.

If any gate fails, the agent MUST NOT proceed. The agent MUST identify the failure, propose a remediation, and re-attempt after fixing the issue.

---

## 4. Harden Mode

Harden mode formalizes the compliance state of the project. It runs at a defined cadence (per sprint, per release, or manually) and produces the artifacts required for audit readiness.

### 4.1 When to Harden

Harden mode MUST run at the frequency defined by `harden.frequency` in the frontmatter:

| Frequency | Cadence | Use Case |
|-----------|---------|----------|
| `per_sprint` | Every sprint or iteration boundary | Default. Satisfies ALCOA Contemporaneous for agile teams. |
| `per_release` | Every minor or major version release | For teams with longer release cycles. Minimum viable cadence. |
| `manual` | On-demand by human operator | For migration or adoption scenarios only. Not suitable for ongoing compliance. |

**`per_sprint` is the RECOMMENDED default.** ALCOA Contemporaneous requires that compliance documentation is produced at the time of the work. The work happens during the sprint; the compliance record MUST also be produced during the sprint. Deferring compliance documentation to a pre-release or pre-audit batch activity violates this principle.

The output of each harden cycle is the compliance state of the project at that point in time. If an auditor arrives on any given day, the last harden output demonstrates compliance. There is no separate audit preparation activity.

### 4.2 Compliance Sweep Protocol

During harden mode, the agent or tooling performs the following compliance sweep:

**Step 1: Annotation Validation**
Parse all source and test files in the project. Validate that:
- All annotations conform to the format defined in Section 2.
- All annotation IDs resolve to valid targets (other annotations, formal artifact files, or both).
- No orphan annotations exist (IDs that reference nothing).
- No GxP-relevant source files lack annotations.
- Risk classifications are consistent (a source file and its test file declare the same risk level).

**Step 2: Traceability Matrix Generation**
Build the complete REQ → US → SPEC → CODE → TEST chain from:
- Annotations in source files and test files.
- Formal artifact files in `.gxp/requirements/`, `.gxp/user_stories/`, and `.gxp/specs/` (if they exist).
- ID scheme relationships (US-001-xxx belongs to REQ-001; SPEC-001-xxx belongs to US-001-xxx).

Output the result to `.gxp/traceability-matrix.json` (format defined in Section 4.3).

**Step 3: Coverage Analysis**
For each component in the traceability matrix:
- Verify that test coverage meets or exceeds the threshold defined for its risk level.
- Verify that all required verification tiers (per the risk matrix) have corresponding test files with passing results.
- Flag components below threshold.

**Step 4: Evidence Formalization**
Collect CI test outputs from the current sprint or release cycle. Organize them into evidence packages in `.gxp/evidence/` following the structure defined in Section 4.5. Each evidence package is self-contained and includes metadata, environment snapshot, test output, and manifest.

**Step 5: Gap Analysis**
Identify and report:
- Missing annotations (GxP-relevant code without annotations).
- Incomplete traceability chains (a REQ with no corresponding SPEC, a SPEC with no corresponding test).
- Coverage shortfalls (components below their risk-level threshold).
- Missing evidence (test results that were not captured or formalized).
- Stale annotations (annotations referencing deleted or renamed artifacts).

**Step 6: Compliance Status Report**
Generate `.gxp/compliance-status.md` (format defined in Section 4.4) summarizing the compliance state.

### 4.3 Traceability Matrix Format

The traceability matrix is generated during harden mode and stored at `.gxp/traceability-matrix.json`. It is the machine-readable record of the complete V-Model chain.

```json
{
  "gxpmd_version": "2.0.0",
  "generated_at": "2026-02-07T14:30:00Z",
  "sprint": "2026-S03",
  "summary": {
    "total_chains": 12,
    "complete_chains": 11,
    "incomplete_chains": 1,
    "total_source_files": 34,
    "annotated_source_files": 34,
    "total_test_files": 48,
    "annotated_test_files": 48
  },
  "chains": [
    {
      "requirement": "REQ-001",
      "requirement_title": "System shall authenticate users via secure credential exchange",
      "user_stories": ["US-001-001", "US-001-002"],
      "specifications": ["SPEC-001-001", "SPEC-001-002"],
      "source_files": [
        "src/auth/login.ts",
        "src/auth/session.ts"
      ],
      "test_files": [
        "tests/oq/auth/login.test.ts",
        "tests/oq/auth/session.test.ts",
        "tests/pq/auth/login.e2e.ts"
      ],
      "risk_level": "HIGH",
      "coverage": 97.2,
      "required_tiers": ["IQ", "OQ", "PQ"],
      "covered_tiers": ["OQ", "PQ"],
      "status": "complete",
      "has_formal_artifacts": true
    }
  ],
  "gaps": [
    {
      "type": "missing_tier",
      "chain": "REQ-002",
      "detail": "IQ tier required for HIGH risk but no IQ test files found",
      "severity": "HIGH"
    }
  ]
}
```

The `chains` array contains one entry per requirement. Each entry lists all downstream artifacts (user stories, specifications, source files, test files) discovered through annotations and formal artifact files. The `status` field is `complete` when all required tiers have passing tests at or above the coverage threshold, and `incomplete` otherwise.

The `gaps` array lists all compliance gaps discovered during the sweep. Each gap includes a type, the affected chain, a human-readable detail, and a severity level.

### 4.4 Compliance Status Report

The compliance status report is generated during harden mode and stored at `.gxp/compliance-status.md`. It is the human-readable compliance record for the sprint.

```markdown
# Compliance Status Report

| Field | Value |
|-------|-------|
| **Sprint** | 2026-S03 |
| **Date** | 2026-02-07 |
| **GxP.MD Version** | 2.0.0 |
| **Project** | [project.name] |
| **Generated By** | [agent or tooling identifier] |

## Metrics Summary

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Annotation coverage (source files) | 100% | 100% | PASS |
| Annotation coverage (test files) | 100% | 100% | PASS |
| Traceability chain completeness | 91.7% (11/12) | 100% | FAIL |
| HIGH risk test coverage | 97.2% | 95% | PASS |
| MEDIUM risk test coverage | 84.1% | 80% | PASS |
| LOW risk test coverage | 72.3% | 60% | PASS |

## Open Gaps

| ID | Severity | Chain | Description | Remediation |
|----|----------|-------|-------------|-------------|
| GAP-001 | HIGH | REQ-002 | Missing IQ tier tests | Add IQ tests for infrastructure verification |

## Risk Assessment Status

- Risk assessment log last updated: 2026-02-05
- Open risks: 2 (1 HIGH, 1 MEDIUM)
- All mitigations current: Yes

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Quality Owner | | | |
| Technical Lead | | | |
```

The sign-off section is completed by human reviewers. The agent generates the report; humans review and sign it. An agent MUST NOT mark the sign-off as complete.

### 4.5 Evidence Package Structure

Evidence packages are formalized during harden mode from CI test output. They are stored in `.gxp/evidence/`.

#### Package Structure

```
.gxp/evidence/{TIER}-{SPEC_ID}-{TIMESTAMP}/
├── metadata.json          # Test identity and result summary
├── environment.json       # Runtime environment snapshot
├── test-output.log        # Raw test runner output (complete, unedited)
├── manifest.json          # SHA-256 hashes of all files in this package
└── signature.jws          # ES256 signature over manifest.json (optional)
```

#### metadata.json

```json
{
  "spec_id": "SPEC-001-001",
  "tier": "OQ",
  "gxp_risk": "HIGH",
  "timestamp": "2026-02-07T14:30:00Z",
  "duration_ms": 4523,
  "result": "pass",
  "test_count": 12,
  "pass_count": 12,
  "fail_count": 0,
  "skip_count": 0,
  "coverage": {
    "lines": 97.2,
    "branches": 94.8,
    "functions": 98.1
  },
  "system_state_hash": "sha256:a1b2c3d4e5f6..."
}
```

#### environment.json

```json
{
  "os": "linux",
  "os_version": "6.1.0",
  "node_version": "22.0.0",
  "runtime": "vitest 3.0.0",
  "ci": true,
  "ci_provider": "github-actions",
  "git_commit": "abc123def456",
  "git_branch": "feat/auth-login",
  "git_dirty": false
}
```

#### manifest.json

```json
{
  "algorithm": "SHA-256",
  "files": {
    "metadata.json": "sha256:...",
    "environment.json": "sha256:...",
    "test-output.log": "sha256:..."
  },
  "generated_at": "2026-02-07T14:30:05Z"
}
```

Evidence packages are formalized during harden from CI output. During develop mode, the CI pipeline captures test results natively. During harden mode, those results are organized into the evidence package structure, manifests are computed, and optional signatures are applied.

The agent does NOT manually create evidence packages during development. Evidence capture is CI-native by default (`evidence.capture: ci_native`). The harden process formalizes what CI already captured.

#### Signing

When `signing_required` is `true` for the component's risk level, the evidence package SHOULD include a `signature.jws` file containing an ES256 (ECDSA with P-256) JSON Web Signature over the contents of `manifest.json`.

Signing is an integrity enhancement. Evidence capture is the primary requirement. If signing infrastructure is not available, evidence packages without signatures are still valid, but the absence SHOULD be noted in the compliance status report.

The agent MUST NOT generate, rotate, or delete signing keys without explicit human authorization.

#### Evidence Integrity Rules

1. Evidence packages MUST NOT be modified after generation. Any modification invalidates the manifest hashes and signature.
2. Failed test runs MUST be preserved. Selective deletion of failure evidence is a data integrity violation under ALCOA+ principles.
3. The `test-output.log` MUST contain the complete, unedited output from the test runner. Truncation or filtering is prohibited.
4. The `system_state_hash` in `metadata.json` MUST be computed at the time of test execution using the algorithm and scope defined in `evidence.state_hash`.

---

## 5. Risk-Level Behavior

The `agent.mode` field in the frontmatter controls the enforcement posture. In `risk_proportionate` mode (the default), the agent calibrates its behavior to the risk level of the component under modification.

### 5.1 HIGH Risk Components

HIGH risk components have direct impact on patient safety, product quality, or protected data integrity. The agent MUST apply maximum rigor.

**The agent MUST:**

1. Ensure complete annotation coverage: `@gxp-req`, `@gxp-spec`, and `@gxp-risk HIGH` on all source files; `@gxp-spec`, `@trace`, `@test-type`, and `@gxp-risk HIGH` on all test files.
2. Achieve test coverage at or above the `coverage_threshold` defined for HIGH risk (default: 95%).
3. Write tests spanning all three verification tiers: IQ, OQ, and PQ.
4. Request peer review before any merge. The merge MUST NOT proceed until review is approved.
5. Update the risk assessment log with a rationale entry for any behavioral change.
6. Preserve all test output including failures, re-runs, and intermediate results.

**The agent SHOULD:**

1. Create formal artifact files (`REQ-NNN.md`, `SPEC-NNN-NNN.md`) in `.gxp/` for HIGH risk components. Formal files provide space for regulatory basis, acceptance criteria, and detailed design rationale that annotations alone may not capture adequately.
2. Generate signed evidence packages when signing infrastructure is available.

**The agent MUST NOT:**

1. Skip or weaken any test to make a gate pass.
2. Modify evidence packages after generation.
3. Merge code without completed peer review.
4. Modify risk levels without explicit human authorization.

### 5.2 MEDIUM Risk Components

MEDIUM risk components affect regulated workflows or critical metadata but have no direct patient safety impact. The agent SHOULD apply thorough verification with pragmatic scope.

**The agent MUST:**

1. Include `@gxp-spec` and `@gxp-risk MEDIUM` annotations in source and test files.
2. Achieve test coverage at or above the `coverage_threshold` defined for MEDIUM risk (default: 80%).
3. Write tests for OQ and PQ verification tiers.

**The agent MAY:**

1. Omit IQ-tier verification if infrastructure components are unchanged.
2. Proceed without peer review, provided all automated gates pass.
3. Omit formal artifact files in `.gxp/`. Annotations are sufficient for MEDIUM risk traceability.

### 5.3 LOW Risk Components

LOW risk components have no GxP data impact. The agent MAY apply minimal verification while maintaining basic traceability.

**The agent SHOULD:**

1. Include `@gxp-spec` and `@gxp-risk LOW` annotations in source files.
2. Achieve test coverage at or above the `coverage_threshold` defined for LOW risk (default: 60%).
3. Write OQ-tier tests for functional correctness.

**The agent MAY:**

1. Omit IQ and PQ verification tiers.
2. Omit `@gxp-req` and `@trace` annotations. For LOW risk, a `@gxp-spec` reference is sufficient traceability.
3. Omit formal artifact files entirely.

### 5.4 Strict Mode

When `agent.mode` is set to `strict`, ALL components are treated as HIGH risk regardless of their actual classification. All MUST-level directives from Section 5.1 apply universally. This mode is appropriate for initial validation campaigns or systems with uniformly high regulatory exposure.

### 5.5 Advisory Mode

When `agent.mode` is set to `advisory`, all directives are downgraded to SHOULD-level recommendations. Violations produce warnings but never block workflow progression. This mode is appropriate during GxP.MD adoption when teams are migrating from unstructured workflows to annotation-based compliance.

---

## 6. Testing Rules

### 6.1 Test Tag Format

All test files in a GxP.MD-governed project MUST include standardized annotations as defined in Section 2.2. These annotations enable automated traceability auditing and evidence generation.

#### Required Tags (Recap)

| Tag | Format | Description |
|-----|--------|-------------|
| `@gxp-spec` | `@gxp-spec SPEC-NNN-NNN` | Links the test to the specification it verifies |
| `@trace` | `@trace US-NNN-NNN` | Links the test to the user story it validates |
| `@test-type` | `@test-type IQ\|OQ\|PQ` | Declares the verification tier |
| `@gxp-risk` | `@gxp-risk HIGH\|MEDIUM\|LOW` | Declares the risk level of the tested component |

### 6.2 CI-Native Evidence Capture

Evidence capture is CI-native by default. This means:

1. The test runner produces structured output (JSON, JUnit XML, or equivalent).
2. The CI pipeline captures this output as a build artifact.
3. During harden mode, captured output is organized into evidence packages.

The agent does NOT manually create `metadata.json`, `environment.json`, or `manifest.json` during development. These are generated during the harden process from CI artifacts. This keeps the development workflow lightweight while ensuring evidence is available for formalization.

When `evidence.capture` is set to `hybrid`, the agent MAY create evidence packages during development for HIGH risk components where immediate evidence formalization is desired. When set to `agent_manual`, the agent creates evidence packages after every test execution (v1 behavior).

### 6.3 Fallback Inference for Untagged Tests

When the agent encounters test files that lack annotations (e.g., in legacy codebases being migrated to GxP.MD), it SHOULD apply fallback inference rules:

1. **Directory-based inference:** Tests in `tests/iq/` are inferred as IQ tier, `tests/oq/` as OQ, `tests/pq/` as PQ.
2. **Filename-based inference:** Files ending in `.e2e.ts` or `.e2e.test.ts` are inferred as PQ tier. Files ending in `.test.ts` without further qualification are inferred as OQ tier.
3. **No inference for risk or traceability.** The agent MUST NOT infer `@gxp-risk` or `@gxp-spec` values. These require explicit annotation.

Inferred tags SHOULD be flagged in the harden mode gap analysis with a recommendation to add explicit annotations.

---

## 7. Data Integrity — ALCOA+ Compliance

ALCOA+ is the gold standard for data integrity in pharmaceutical and life sciences environments. Every AI agent operating under GxP.MD MUST respect these principles in all actions that create, modify, or reference regulated data and artifacts.

### 7.1 Attributable

Every action that creates or modifies a regulated artifact MUST be attributable to a specific individual.

- The agent MUST ensure that all commits are authored by an identifiable individual (via `git_author`). Commits with generic, shared, or anonymous authorship are non-compliant.
- When an AI agent generates code or artifacts, the commit MUST be attributed to the human operator who directed the work. The agent MAY be identified as a co-author (e.g., via `Co-Authored-By` trailer) but MUST NOT be the sole author of record.
- Annotations in source files inherit attribution from the git commit that introduced them.

### 7.2 Legible

All artifacts, evidence, and documentation MUST be readable and understandable by qualified personnel.

- Markdown artifacts MUST pass a markdown linter without errors.
- Code comments and annotations MUST be written in clear, unambiguous language.
- Evidence package contents MUST be in standard, non-proprietary formats (JSON, plain text, markdown).
- The agent MUST NOT produce artifacts that require specialized tooling to read beyond standard text editors and JSON parsers.

### 7.3 Contemporaneous

Records MUST be created at the time the activity occurs, not retroactively.

- Evidence packages MUST be formalized during the harden cycle for the sprint in which the work was performed. Retroactive evidence generation for work performed in a prior sprint is a contemporaneity violation.
- The harden cycle MUST run at the cadence defined by `harden.frequency`. Skipping a harden cycle creates a gap in the contemporaneous compliance record.
- The agent MUST NOT backdate or forward-date any timestamps in artifacts or evidence.
- Annotations SHOULD be committed in the same commit or commit sequence as the code they govern. Large batches of annotation-only commits after the fact indicate a contemporaneity risk.

### 7.4 Original

Records MUST be the first-generation, unaltered version.

- Annotations in source code, versioned by git, are inherently original. The git history provides a tamper-evident record of when each annotation was introduced and by whom.
- Evidence packages SHOULD be signed using JWS to prove they have not been altered after generation, when signing is enabled for the project's risk level.
- The manifest hash chain (file hashes -> manifest -> optional signature) provides proof of originality.
- The agent MUST NOT regenerate evidence packages to replace unfavorable results. If a test fails and is subsequently fixed, BOTH the failure evidence and the passing evidence MUST be retained.

### 7.5 Accurate

Records MUST correctly reflect the activity they document.

- The system state hash recorded in evidence packages MUST match the actual SHA-256 hash of the `/src` tree at the time of test execution.
- Coverage numbers in `metadata.json` MUST match the raw coverage data in the test output.
- The agent MUST NOT manually adjust test results, coverage numbers, or any other metrics in evidence packages.
- Annotations MUST accurately reflect the component's actual risk level, governing requirement, and governing specification.

### 7.6 Complete (ALCOA+ Extension)

All data MUST be present, including failed attempts, re-runs, and negative results.

- All test executions MUST produce evidence — not only successful runs.
- When a test suite is re-run after a failure, both the failing and passing evidence MUST be retained. Evidence directories are append-only.
- Skip counts MUST be recorded and justified. An agent MUST NOT skip tests to improve pass rates without documenting the justification.
- The traceability matrix generated during harden mode MUST include all chains, not only complete ones. Incomplete chains are reported in the gaps array.

### 7.7 Consistent (ALCOA+ Extension)

Records MUST demonstrate logical consistency in timestamps, sequences, and cross-references.

- Evidence package timestamps MUST be chronologically consistent with the commit history.
- Artifact version sequences MUST be monotonically increasing.
- Annotations referencing the same specification ID MUST use the same risk level classification. Inconsistent risk levels across source and test files are a consistency violation flagged during harden.

### 7.8 Enduring (ALCOA+ Extension)

Records MUST survive for the defined retention period.

- Evidence packages MUST NOT be deleted before `evidence.retention_days` has elapsed.
- The agent MUST NOT include evidence directories in `.gitignore` or any other exclusion mechanism.
- When evidence approaches the retention limit, the agent SHOULD notify the human operator to initiate archival procedures.

### 7.9 Available (ALCOA+ Extension)

Records MUST be accessible to authorized parties when needed.

- All artifacts and evidence MUST be stored in the `.gxp/` directory within the project repository, accessible to all authorized contributors.
- Evidence packages MUST NOT be encrypted with individual keys that would prevent authorized access.
- The traceability matrix and compliance status report generated during harden mode serve as indexes for rapid audit retrieval.

---

## 8. Quality Gates

Quality gates are the primary compliance enforcement mechanism in GxP.MD v2. They define what must be true at each checkpoint, not how the agent must work to get there.

### 8.1 Pre-Commit Gate

Scope: Individual commits. Protects annotation hygiene.

| Check | Description |
|-------|-------------|
| `annotations_valid` | All `@gxp-req`, `@gxp-spec`, `@gxp-risk`, `@gxp-story`, `@trace`, and `@test-type` annotations in modified files conform to Section 2 format. |
| `no_untagged_gxp_code` | All modified source files containing GxP-relevant logic include at minimum `@gxp-spec` and `@gxp-risk` annotations. |

Pre-commit gates are lightweight and fast. They validate syntax and presence, not completeness.

### 8.2 Pre-Merge Gate

Scope: Feature branch merges. Protects the shared codebase.

| Check | Description |
|-------|-------------|
| `all_tests_pass` | All tests for affected components across all required verification tiers pass. Zero failures. |
| `coverage_meets_threshold` | Test coverage for every modified component meets or exceeds its risk-level threshold. |
| `review_complete_if_required` | For components where `review_required` is `true`, at least one reviewer has approved. |
| `no_orphan_annotations` | All annotation IDs in modified files resolve to a corresponding annotation or formal artifact. |

Pre-merge gates are the primary enforcement point during development. They ensure that no code reaches the main branch without valid annotations, passing tests, and sufficient coverage.

### 8.3 Per-Release Gate (Harden)

Scope: Sprint boundaries, release boundaries. Protects the compliance record.

| Check | Description |
|-------|-------------|
| `harden_sweep_complete` | The compliance sweep protocol (Section 4.2) has been executed for this sprint/release. |
| `traceability_matrix_current` | `.gxp/traceability-matrix.json` reflects the current state of all annotations and artifacts. |
| `evidence_packages_complete` | Evidence packages exist for all test executions in the current sprint/release. |
| `compliance_status_generated` | `.gxp/compliance-status.md` has been generated with current metrics and gap analysis. |
| `risk_assessment_current` | `.gxp/risk_assessment.log` reflects the current risk landscape. No stale or unaddressed risks. |

Per-release gates ensure that the compliance record is complete and current at every sprint boundary. They are the mechanism by which ALCOA Contemporaneous is enforced.

---

## 9. Repository Structure

A project governed by GxP.MD v2 MUST maintain the following directory structure:

```
project-root/
├── GxP.MD                          # Compliance instructions (this file)
├── .gxp/                           # Compliance output and project-level docs
│   ├── system_context.md           # System description (manually maintained)
│   ├── risk_assessment.log         # Risk register (manually maintained)
│   ├── requirements/               # OPTIONAL: formal requirement docs (REQ-NNN.md)
│   ├── user_stories/               # OPTIONAL: formal user story docs (US-NNN-NNN.md)
│   ├── specs/                      # OPTIONAL: formal specification docs (SPEC-NNN-NNN.md)
│   ├── adr/                        # OPTIONAL: architecture decision records
│   ├── evidence/                   # Evidence packages (generated during harden)
│   │   ├── IQ-SPEC-001-001-20260207T143000/
│   │   ├── OQ-SPEC-001-001-20260207T143000/
│   │   └── PQ-SPEC-001-001-20260207T150000/
│   ├── traceability-matrix.json    # Generated during harden
│   └── compliance-status.md        # Generated during harden
├── src/                            # Source code WITH inline annotations
└── tests/                          # Tests WITH inline annotations
    ├── iq/
    ├── oq/
    └── pq/
```

The `.gxp/` directory contains three categories of content:

1. **Manually maintained project documents.** `system_context.md` describes the system. `risk_assessment.log` tracks risks. These are written and updated by humans (or agents directed by humans) and are not auto-generated.

2. **Optional formal artifact files.** `requirements/`, `user_stories/`, `specs/`, and `adr/` contain formal documents for teams that want the additional depth. These directories MAY be empty or absent. Annotations in source and test files provide the baseline traceability; formal files provide elaboration.

3. **Generated compliance outputs.** `traceability-matrix.json`, `compliance-status.md`, and `evidence/` are produced during harden mode. They are the output of the compliance sweep, not manually authored.

### 9.1 System Context Document

The `.gxp/system_context.md` file SHOULD describe:

- **System name and purpose.** What the system does and why it exists.
- **System boundaries.** What is in scope and what is out of scope for GxP validation.
- **Intended use.** Who uses the system, in what context, and for what purpose.
- **Operational environment.** Where the system runs and key infrastructure dependencies.
- **Interfaces.** External systems, APIs, and data flows that cross the system boundary.
- **Regulatory basis.** Which regulations apply and why.

### 9.2 Risk Assessment Log

The `.gxp/risk_assessment.log` is a chronological record of risk identification, assessment, and mitigation activities. Each entry MUST include:

```markdown
## RISK-{NNN}: {Title}

- **Date:** 2026-02-07
- **Author:** author@example.com
- **Component:** src/modules/auth/
- **Risk Level:** HIGH
- **Description:** Description of the identified risk.
- **Impact:** What could go wrong if the risk materializes.
- **Mitigation:** What controls are in place to reduce the risk.
- **Status:** open | mitigated | accepted | closed
```

---

## 10. Artifact Schemas (For Formal Artifact Files)

This section defines the frontmatter schemas for optional formal artifact files in `.gxp/`. These schemas apply to teams that choose to maintain separate requirement, user story, and specification documents for additional depth beyond what annotations provide.

Formal artifact files are NOT required for GxP.MD v2 compliance. Annotations are the primary traceability mechanism. These schemas are provided for teams that want or need the additional documentation.

### 10.1 Requirements (`.gxp/requirements/REQ-NNN.md`)

```yaml
---
gxp_id: REQ-001
title: "Requirement title"
parent_id: null                    # null for top-level requirements
description: "Detailed requirement description"
risk_level: HIGH                   # HIGH | MEDIUM | LOW
acceptance_criteria:
  - "Criterion 1"
  - "Criterion 2"
validation_status: draft           # draft | in_review | validated | retired
created: "2026-02-07"
updated: "2026-02-07"
author: "author@example.com"
---
```

**Body:** Detailed requirement narrative including regulatory basis, business justification, and any constraints.

### 10.2 User Stories (`.gxp/user_stories/US-NNN-NNN.md`)

```yaml
---
gxp_id: US-001-001
title: "User story title"
parent_id: REQ-001                 # Parent requirement ID
acceptance_criteria:
  - "Given/When/Then criterion 1"
  - "Given/When/Then criterion 2"
verification_tier: OQ              # Primary verification tier: IQ | OQ | PQ
validation_status: draft           # draft | in_review | validated | retired
created: "2026-02-07"
updated: "2026-02-07"
author: "author@example.com"
---
```

**Body:** User story narrative in "As a [role], I want [capability], so that [benefit]" format, followed by detailed acceptance criteria.

### 10.3 Technical Specifications (`.gxp/specs/SPEC-NNN-NNN.md`)

```yaml
---
gxp_id: SPEC-001-001
title: "Specification title"
parent_id: US-001-001              # Parent user story ID
verification_tier: OQ              # IQ | OQ | PQ
design_approach: "Brief description of the implementation approach"
source_files:
  - "src/modules/auth/login.ts"
test_files:
  - "tests/oq/auth/login.test.ts"
validation_status: draft           # draft | in_review | validated | retired
created: "2026-02-07"
updated: "2026-02-07"
author: "author@example.com"
---
```

**Body:** Detailed technical design including data flows, API contracts, error handling strategy, and security considerations.

### 10.4 Validation Status Lifecycle

Artifacts that use formal files progress through the following statuses:

| Status | Meaning |
|--------|---------|
| `draft` | Initial creation. Content may be incomplete. |
| `in_review` | Content complete. Awaiting peer review or quality review. |
| `validated` | Reviewed and approved. Linked implementation and tests are verified. |
| `retired` | No longer active. Retained for audit trail purposes. |

An agent MUST NOT set `validation_status` to `validated` without human authorization. Validation is a quality decision that requires human judgement.

---

## 11. Appendix A: Regulatory Profile Reference

The `regulatory.profile` field in the frontmatter selects a built-in configuration preset that adjusts default behaviors for common regulatory scenarios. Profiles set sensible defaults; individual fields can still be overridden.

### 11.1 `pharma-standard`

**Scope:** General pharmaceutical software systems subject to GxP regulations.

**Typical use:** Manufacturing execution systems, laboratory information management, quality management systems, document management, batch record systems.

**Default configuration:**
- Frameworks: 21 CFR Part 11, EU Annex 11
- GAMP Category: 5 (custom software)
- All three verification tiers required for HIGH risk
- Peer review required for HIGH risk
- Per-sprint harden frequency

### 11.2 `medical-device`

**Scope:** Software that is or is a component of a medical device, subject to IEC 62304 and FDA 21 CFR Part 820.

**Typical use:** Software as a Medical Device (SaMD), embedded device firmware, clinical decision support systems, diagnostic software.

**Default configuration:**
- Frameworks: IEC 62304, 21 CFR Part 820, EU MDR
- GAMP Category: 5
- Software safety classification mapping (Class A/B/C per IEC 62304)
- All three verification tiers required for MEDIUM and HIGH risk
- Peer review required for MEDIUM and HIGH risk
- Additional requirement for SOUP (Software of Unknown Provenance) documentation
- Per-sprint harden frequency

### 11.3 `clinical-trial`

**Scope:** Software supporting clinical trial operations, subject to 21 CFR Part 11 and ICH E6(R2) GCP.

**Typical use:** Electronic data capture (EDC), randomization and trial supply management (RTSM), clinical trial management systems (CTMS), ePRO/eCOA platforms.

**Default configuration:**
- Frameworks: 21 CFR Part 11, ICH E6(R2), EU Annex 11
- GAMP Category: 5
- Enhanced audit trail requirements (capture before/after values for all data changes)
- All three verification tiers required for HIGH risk
- Peer review required for HIGH and MEDIUM risk
- Per-sprint harden frequency

### 11.4 `laboratory`

**Scope:** Laboratory informatics software subject to GLP and GMP requirements.

**Typical use:** LIMS, chromatography data systems, electronic lab notebooks, instrument integration software.

**Default configuration:**
- Frameworks: 21 CFR Part 11, OECD GLP Principles, EU Annex 11
- GAMP Category: 4 or 5
- Emphasis on data acquisition integrity (instrument-to-system data flow)
- OQ and PQ verification tiers required for MEDIUM and HIGH risk
- Peer review required for HIGH risk
- Per-sprint harden frequency

---

## 12. Appendix B: Custom Directives

GxP.MD supports project-specific extensions through custom directives. These directives augment (but MUST NOT contradict) the standard directives defined in this specification.

### 12.1 Defining Custom Directives

Custom directives are added as additional sections in the markdown body of the project's GxP.MD file, after the standard sections:

```markdown
## Custom Directives

### CD-001: [Directive Title]

**Scope:** Which components or activities this directive applies to.
**Risk Level:** HIGH | MEDIUM | LOW
**Directive:** The behavioral instruction using RFC 2119 keywords.
**Rationale:** Why this directive exists (regulatory basis or business justification).
```

### 12.2 Custom Directive Rules

1. Custom directives MUST use RFC 2119 keywords for severity.
2. Custom directives MUST NOT weaken any MUST-level standard directive.
3. Custom directives MAY strengthen SHOULD-level or MAY-level standard directives.
4. Custom directives MUST include a rationale explaining their regulatory or business basis.
5. Custom directives SHOULD be reviewed and approved by the quality owner.

### 12.3 Custom Frontmatter Extensions

The YAML frontmatter supports a `custom` key for project-specific configuration:

```yaml
custom:
  electronic_signatures:
    require_meaning: true
    require_mfa: true
  audit_trail:
    capture_before_after: true
    require_reason: true
  soup:
    inventory_required: true
    risk_assessment_required: true
```

Custom frontmatter keys are opaque to the GxP.MD specification — they are consumed by tooling and agents that understand the project-specific extensions.

---

## 13. Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **ADR** | Architecture Decision Record. A document recording a significant architectural decision, its context, and consequences. |
| **ALCOA+** | Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available. The regulatory standard for data integrity. |
| **Annotation** | A structured comment in a source or test file that declares traceability, risk level, and verification tier for GxP compliance. The primary compliance mechanism in GxP.MD v2. |
| **Artifact** | A documented deliverable in the validation lifecycle: requirement, user story, specification, or evidence package. In v2, annotations are the primary artifacts; formal files are optional. |
| **Compliance Sweep** | The systematic process executed during harden mode that validates annotations, builds the traceability matrix, analyzes coverage, and produces the compliance status report. |
| **Develop Mode** | The day-to-day operating mode. Lightweight, annotation-driven. Gates enforce compliance at commit and merge boundaries. |
| **Evidence Package** | A self-contained directory containing test results, environment data, manifest hashes, and optional cryptographic signature proving verification was performed. Formalized during harden mode. |
| **Formal Artifact File** | A separate markdown document in `.gxp/` (e.g., `REQ-NNN.md`, `SPEC-NNN-NNN.md`) providing detailed documentation beyond what annotations express. Optional in v2. |
| **GAMP** | Good Automated Manufacturing Practice. ISPE guidelines for validating computerized systems. Category 5 = custom-built software. |
| **Gate** | An enforcement checkpoint that blocks workflow progression until defined conditions are met. The primary compliance enforcement mechanism in v2. |
| **GxP** | Good Practice. An umbrella term for quality guidelines and regulations including GMP, GLP, GCP, GDP, and related standards. |
| **Harden Mode** | The per-sprint compliance formalization mode. Produces traceability matrix, compliance status report, evidence packages, and gap analysis. This IS audit-readiness. |
| **IQ** | Installation Qualification. Verification that a system is installed correctly with all dependencies present and configured. |
| **JWS** | JSON Web Signature. A standard (RFC 7515) for digitally signing JSON payloads. Used for optional evidence package signing. |
| **OQ** | Operational Qualification. Verification that a system functions correctly according to its specifications. |
| **PHI** | Protected Health Information. Individually identifiable health data subject to privacy regulations (e.g., HIPAA). |
| **PQ** | Performance Qualification. Verification that a system performs acceptably under conditions approximating real-world use. |
| **Risk Matrix** | The configuration mapping risk levels (HIGH/MEDIUM/LOW) to enforcement requirements (coverage, tiers, signing, review). |
| **ROSIE** | The artifact and evidence standard (RFC-001) that defines the `.gxp/` directory structure and evidence package format. Compatible with but not required by GxP.MD v2. |
| **SOUP** | Software of Unknown Provenance. Third-party software components not developed under the project's quality system. |
| **Traceability** | The ability to follow any component from its origin requirement through implementation to verification evidence, and vice versa. Maintained through annotations in v2. |
| **Traceability Matrix** | A JSON document generated during harden mode that maps the complete REQ -> US -> SPEC -> CODE -> TEST chain for every requirement. |
| **V-Model** | A software development model where each development phase has a corresponding verification phase. In v2, the V-Model defines the shape of traceability; annotations express the relationships. |
| **Verification Tier** | A category of testing activity (IQ, OQ, or PQ) aligned with qualification protocols in the V-Model. |

---

## 14. Appendix D: Conformance

### 14.1 Specification Conformance Levels

Implementations of GxP.MD tooling MUST declare their conformance level:

| Level | Description |
|-------|-------------|
| **Level 1: Parse** | Can parse GxP.MD frontmatter and extract configuration values. |
| **Level 2: Annotate** | Level 1 + can parse and validate annotations in source and test files. |
| **Level 3: Gate** | Level 2 + can enforce quality gates (pre-commit, pre-merge) and block non-compliant actions. |
| **Level 4: Harden** | Level 3 + can execute the compliance sweep and generate traceability matrix, compliance status report, and evidence packages. |
| **Level 5: Full** | Level 4 + can manage the complete artifact lifecycle including formal files, signing, and retention enforcement. |

### 14.2 Agent Conformance

An AI coding agent claims GxP.MD conformance by declaring which specification version it supports and at what level. Conformance is demonstrated through behavior, not assertion — an agent claiming Level 4 conformance MUST be capable of executing all develop and harden mode directives in this specification when operating on a GxP.MD-governed project.

### 14.3 Version Compatibility

GxP.MD follows semantic versioning. Tooling MUST:

- Support the exact `gxpmd_version` declared in the frontmatter.
- SHOULD support backward-compatible minor versions (e.g., tooling supporting 2.1.0 SHOULD support 2.0.0).
- MUST reject frontmatter with a major version it does not support, with a clear error message.

### 14.4 Migration from v1

Projects migrating from GxP.MD v1.0.0 to v2.0.0 SHOULD:

1. Set `agent.mode` to `advisory` during the migration period. This allows existing workflows to continue while annotations are added incrementally.
2. Add annotations to source and test files as they are modified. There is no requirement to annotate the entire codebase at once.
3. Set `artifacts.formal_artifacts` to `optional` to preserve existing `.gxp/requirements/`, `.gxp/user_stories/`, and `.gxp/specs/` files while removing the requirement to create new ones.
4. Run the first harden cycle once a meaningful portion of the codebase is annotated. The gap analysis will identify remaining unannotated areas.
5. Transition to `risk_proportionate` mode once annotation coverage is sufficient for the project's risk profile.

Existing formal artifact files are NOT invalidated by v2. They are incorporated into the traceability matrix alongside annotations. The v2 model is additive — annotations provide the baseline; formal files provide optional depth.

---

*End of GxP.MD Specification v2.0.0*
