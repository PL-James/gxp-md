---
# ============================================================================
# GxP.MD — Compliance Instructions for AI Coding Agents
# ============================================================================
# Version:  1.0.0
# Status:   Draft
# Date:     2026-02-07
# Author:   PharmaLedger Association
# License:  Copyright 2026 PharmaLedger Association. All rights reserved.
# ============================================================================
#
# This file is the canonical specification for GxP.MD, a markdown-based
# compliance instruction standard for AI coding agents operating on
# pharmaceutical and life sciences software systems.
#
# Place this file at the root of any regulated software project.
# AI agents discover and parse it by convention.
#
# Machine-readable configuration follows. Human-readable directives are in
# the markdown body below the frontmatter.
# ============================================================================

gxpmd_version: "1.0.0"

# ---------------------------------------------------------------------------
# Project Identity
# ---------------------------------------------------------------------------
# Identifies the software system under validation. Every field is REQUIRED.
# The `id` field MUST be a stable, globally unique identifier for the product
# (e.g., a product code, GTIN segment, or internal registry ID).
# ---------------------------------------------------------------------------
project:
  name: ""                    # Human-readable product name
  id: ""                      # Unique product identifier
  version: ""                 # Current semantic version (MAJOR.MINOR.PATCH)
  owner: ""                   # Quality-responsible individual or team
  contact: ""                 # Email or distribution list for quality issues

# ---------------------------------------------------------------------------
# Regulatory Context
# ---------------------------------------------------------------------------
# Defines the regulatory environment that governs this system. The `profile`
# selects a built-in configuration preset (see Appendix A). Jurisdictions
# and frameworks drive gate behavior and evidence requirements.
# ---------------------------------------------------------------------------
regulatory:
  profile: pharma-standard    # pharma-standard | medical-device | clinical-trial | laboratory
  jurisdictions:              # Regulatory bodies with authority
    - FDA
    - EMA
  frameworks:                 # Applicable regulatory frameworks
    - "21 CFR Part 11"
    - "EU Annex 11"
  gamp_category: 5            # GAMP 5 software category (1–5)

# ---------------------------------------------------------------------------
# Risk Configuration
# ---------------------------------------------------------------------------
# The risk matrix governs enforcement behavior. Each risk level defines
# thresholds for test coverage, required verification tiers, and whether
# cryptographic signing and peer review are mandated.
#
# Risk levels align with ICH Q9 and GAMP 5 risk assessment principles:
#   HIGH   — Direct impact on patient safety, product quality, or data
#            integrity of protected health information (PHI/PII).
#   MEDIUM — Impact on regulated workflows, audit trails, or critical
#            metadata. No direct patient safety impact.
#   LOW    — Cosmetic, UI-only, or non-GxP-impacting functionality.
#            No regulated data touched.
# ---------------------------------------------------------------------------
risk:
  overall: HIGH               # Project-level risk classification
  matrix:
    HIGH:
      coverage_threshold: 95  # Minimum test coverage percentage
      required_tiers:         # Verification tiers that MUST pass
        - IQ
        - OQ
        - PQ
      signing_required: true  # Evidence packages MUST be cryptographically signed
      review_required: true   # Peer review MUST be completed before merge
    MEDIUM:
      coverage_threshold: 80
      required_tiers:
        - OQ
        - PQ
      signing_required: true
      review_required: false
    LOW:
      coverage_threshold: 60
      required_tiers:
        - OQ
      signing_required: false
      review_required: false

# ---------------------------------------------------------------------------
# Artifact Configuration
# ---------------------------------------------------------------------------
# Controls how validation artifacts (requirements, user stories, specs,
# evidence) are stored and identified. The `engine` field declares which
# artifact management system produces and consumes these artifacts.
#
# The `id_schema` defines the naming convention for artifact identifiers.
# Tokens in braces are replaced at creation time:
#   {NNN}       — Zero-padded sequential number
#   {TIER}      — Verification tier (IQ, OQ, PQ)
#   {SPEC_ID}   — Parent specification identifier
#   {TIMESTAMP} — ISO 8601 timestamp (compact: YYYYMMDDTHHmmss)
# ---------------------------------------------------------------------------
artifacts:
  engine: rosie                # Artifact engine: rosie | custom
  directory: .gxp              # Root directory for all validation artifacts
  id_schema:
    requirement: "REQ-{NNN}"
    user_story: "US-{NNN}-{NNN}"
    specification: "SPEC-{NNN}-{NNN}"
    evidence: "{TIER}-{SPEC_ID}-{TIMESTAMP}"
  traceability_enforcement: strict  # strict | warn | off

# ---------------------------------------------------------------------------
# V-Model Definition
# ---------------------------------------------------------------------------
# The V-Model maps the software development lifecycle to verification
# activities. Each phase produces artifacts that trace forward to
# implementation and backward to verification.
#
# Phases:
#   Requirements    → define WHAT the system must do
#   User Stories    → define WHO needs it and WHY
#   Specifications  → define HOW it will be built
#   Implementation  → the source code itself
#   Verification    → tests and evidence proving correctness
#
# Tiers:
#   IQ — Installation Qualification: proves the system is installed correctly
#   OQ — Operational Qualification: proves the system works as specified
#   PQ — Performance Qualification: proves the system works for real users
# ---------------------------------------------------------------------------
vmodel:
  phases:
    - name: Requirements
      artifacts:
        - requirements
      id_prefix: REQ
    - name: User Stories
      artifacts:
        - user_stories
      id_prefix: US
    - name: Specifications
      artifacts:
        - specs
      id_prefix: SPEC
    - name: Implementation
      artifacts:
        - source_code
    - name: Verification
      artifacts:
        - tests
        - evidence
  tiers:
    IQ:
      scope: "Infrastructure and installation verification"
      includes:
        - dependency_tree
        - health_checks
        - migrations
        - environment_config
    OQ:
      scope: "Operational and functional verification"
      includes:
        - unit_tests
        - integration_tests
        - api_contract_tests
        - coverage_reports
    PQ:
      scope: "Performance and end-user workflow verification"
      includes:
        - e2e_tests
        - screenshots
        - traces
        - load_tests

# ---------------------------------------------------------------------------
# Quality Gates
# ---------------------------------------------------------------------------
# Gates are enforcement checkpoints in the development lifecycle. Each gate
# defines a set of conditions that MUST be satisfied before the workflow
# can proceed. Tooling SHOULD enforce these gates automatically.
# ---------------------------------------------------------------------------
gates:
  pre_commit:
    - traceability_audit           # All changed files trace to a spec or requirement
    - risk_assessment_current      # Risk assessment log reflects current state
    - no_orphan_artifacts          # No artifacts exist without parent traceability
    - gxp_tags_valid               # All @gxp-tag annotations are syntactically correct
  pre_merge:
    - all_tests_pass               # All IQ/OQ/PQ tests for affected components pass
    - coverage_meets_threshold     # Coverage meets or exceeds risk-level threshold
    - evidence_packages_signed     # Evidence packages are signed (if required by risk)
    - peer_review_complete         # Peer review approved (if required by risk)
    - no_validation_status_draft   # No artifacts in "draft" status for merged code
  pre_release:
    - all_gates_pass               # All pre_commit and pre_merge gates satisfied
    - validation_status_validated  # All artifacts in "validated" status
    - evidence_archived            # Evidence packages archived and retrievable
    - risk_assessment_signed_off   # Risk assessment signed by quality owner
    - system_state_hash_recorded   # SHA-256 of /src tree recorded in release manifest

# ---------------------------------------------------------------------------
# ALCOA+ Data Integrity
# ---------------------------------------------------------------------------
# ALCOA+ is the regulatory standard for data integrity in life sciences.
# Each principle maps to a concrete enforcement mechanism that agents and
# tooling MUST respect.
#
# Core ALCOA:
#   Attributable    — who performed the action
#   Legible         — can the data be read and understood
#   Contemporaneous — was the data recorded at the time of the activity
#   Original        — is this the first-generation record
#   Accurate        — does the data correctly reflect the activity
#
# Plus (+) extensions:
#   Complete        — is all data present, including re-runs and failures
#   Consistent      — are timestamps and sequences logical
#   Enduring        — will the data survive for the retention period
#   Available       — can authorized parties access the data when needed
# ---------------------------------------------------------------------------
alcoa:
  attributable:
    enforce: true
    method: git_author           # Git commit author as attribution source
  legible:
    enforce: true
    method: markdown_lint        # Markdown artifacts must pass linting
  contemporaneous:
    enforce: true
    method: commit_timestamp     # Evidence timestamps must match commit time (±5 min)
  original:
    enforce: true
    method: jws_signature        # JWS signatures prove original, unmodified records
  accurate:
    enforce: true
    method: system_state_hash    # SHA-256 hash of source tree at evidence time

# ---------------------------------------------------------------------------
# Evidence Configuration
# ---------------------------------------------------------------------------
# Controls how verification evidence is generated, signed, and stored.
# Evidence packages are self-contained directories containing:
#   metadata.json     — test identity, timestamps, result summary
#   environment.json  — runtime environment snapshot
#   test-output.log   — raw test runner output
#   manifest.json     — SHA-256 hashes of all package contents
#   signature.jws     — ES256 signature over manifest.json (if signing required)
# ---------------------------------------------------------------------------
evidence:
  signing_algorithm: ES256       # ECDSA with P-256 curve
  key_management: repository     # repository | vault | hsm
  retention_days: 90             # Minimum retention for evidence packages
  state_hash:
    algorithm: SHA-256
    scope: /src
    excludes:
      - node_modules
      - ".*"
      - "*.log"
      - dist

# ---------------------------------------------------------------------------
# Agent Behavior
# ---------------------------------------------------------------------------
# Directives that control how AI coding agents interact with this project.
# The `mode` field sets the overall enforcement posture:
#   strict              — All violations are blocking errors
#   risk_proportionate  — Enforcement scales with risk level
#   advisory            — Violations are warnings only (for adoption/migration)
# ---------------------------------------------------------------------------
agent:
  on_session_start:
    - "Read GxP.MD at project root"
    - "Read .gxp/system_context.md for system description and boundaries"
    - "Read .gxp/risk_assessment.log for open risks and mitigations"
    - "Run traceability audit to identify gaps"
  mode: risk_proportionate
  directives_version: "1.0.0"

---

# GxP.MD Specification

**Version 1.0.0 — Draft**

## Abstract

GxP.MD is a declarative compliance instruction standard for AI coding agents operating on software systems subject to Good Practice (GxP) regulations in the pharmaceutical and life sciences industries.

A GxP.MD file is a single markdown document placed at the root of a software project. It contains machine-readable configuration in YAML frontmatter and human-readable behavioral directives in the markdown body. AI agents discover this file by convention, parse the configuration to understand the regulatory context, and follow the directives to produce compliant code, artifacts, and evidence.

GxP.MD does not replace existing regulatory frameworks. It translates their requirements into actionable instructions that AI agents can execute. It wraps the ROSIE RFC-001 artifact and evidence standard and serves as the declarative contract consumed by validation platforms such as Nexus.

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt).

---

## 1. Core Principles

### 1.1 The V-Model is Law

The V-Model defines the relationship between development activities and verification activities. Every piece of production code MUST trace backward through a specification, a user story, and a requirement. Every test MUST trace forward to the specification it verifies.

An agent MUST NOT write implementation code for functionality that lacks a corresponding User Story and Technical Specification in the `.gxp/` artifact directory. If the required artifacts do not exist, the agent MUST create them first, following the artifact frontmatter schema defined in this specification, before writing any implementation code.

The V-Model phases are:

1. **Requirements** define WHAT the system must do. They capture regulatory obligations, business rules, and quality attributes. Each requirement receives a unique `REQ-{NNN}` identifier.

2. **User Stories** define WHO needs the capability and WHY. They decompose requirements into implementable units of work. Each user story receives a `US-{NNN}-{NNN}` identifier linking it to its parent requirement.

3. **Technical Specifications** define HOW each user story will be implemented. They describe the design approach, source files, test files, and verification tier. Each specification receives a `SPEC-{NNN}-{NNN}` identifier linking it to its parent user story.

4. **Implementation** is the source code itself. Every source file that implements GxP-relevant functionality MUST contain `@gxp-tag` annotations linking it to its governing specification.

5. **Verification** proves that the implementation satisfies its specification. Tests are organized by verification tier (IQ, OQ, PQ) and produce signed evidence packages.

### 1.2 Traceability is Mandatory

Traceability is the ability to follow any artifact from its origin requirement through implementation to verification evidence. It is the backbone of GxP compliance.

When `traceability_enforcement` is set to `strict`:

- Every source file containing GxP-relevant logic MUST include at least one `@gxp-tag SPEC-XXX` annotation linking it to a technical specification.
- Every test file MUST include `@trace US-XXX` or `@trace SPEC-XXX` annotations identifying what it verifies.
- Every specification MUST reference a parent user story via its `parent_id` frontmatter field.
- Every user story MUST reference a parent requirement via its `parent_id` frontmatter field.
- No artifact MAY exist without a valid traceability chain to a requirement.

When `traceability_enforcement` is set to `warn`, violations produce warnings but do not block workflow progression. When set to `off`, traceability is not enforced.

### 1.3 Risk Awareness

Risk assessment is not a one-time activity. It is a continuous obligation.

Every change that touches GxP-relevant functionality MUST be evaluated against the risk matrix defined in the frontmatter. The agent MUST:

- Identify the risk level of the component being modified (HIGH, MEDIUM, or LOW).
- Apply the enforcement rules corresponding to that risk level.
- Update `.gxp/risk_assessment.log` if the change introduces new risks or modifies existing risk mitigations.

Risk levels are determined by the potential impact on:

| Risk Level | Impact Domain | Examples |
|------------|--------------|---------|
| **HIGH** | Patient safety, product quality, PHI/PII data integrity | Authentication, dosage calculations, audit trails, data encryption, electronic signatures |
| **MEDIUM** | Regulated workflows, critical metadata, operational integrity | Batch processing, report generation, notification systems, role management |
| **LOW** | Non-GxP functionality, cosmetic elements, developer tooling | UI theming, internal dashboards, documentation sites, developer utilities |

### 1.4 Evidence Over Assurance

Compliance is demonstrated through verifiable evidence, not assertions.

An agent MUST NOT claim that code is compliant, tested, or validated without producing corresponding evidence artifacts. "It works" is not evidence. A signed evidence package containing test output, environment snapshot, and system state hash IS evidence.

Every verification activity MUST produce an evidence package in `.gxp/evidence/` following the package format defined in Section 5.3.

### 1.5 Agent Agnosticism

GxP.MD is designed to be consumed by any AI coding agent — Claude, GPT, Gemini, Copilot, or any future system capable of reading markdown and YAML. Directives in this specification use plain language and standard formats. No agent-specific features, APIs, or capabilities are assumed.

Agents that cannot fulfill a MUST-level directive SHOULD halt and report the gap to the human operator rather than silently proceeding without compliance.

---

## 2. Agent Behavior by Risk Level

The `agent.mode` field in the frontmatter controls the enforcement posture. In `risk_proportionate` mode (the default), the agent calibrates its behavior to the risk level of the component under modification.

### 2.1 HIGH Risk Components

HIGH risk components have direct impact on patient safety, product quality, or protected data integrity. The agent MUST apply maximum rigor.

**The agent MUST:**

1. Verify a complete traceability chain exists from the governing requirement through user story and specification before writing any code.
2. Include `@gxp-tag`, `@trace`, `@test-type`, and `@gxp-criticality HIGH` annotations in all source and test files.
3. Achieve test coverage at or above the `coverage_threshold` defined for HIGH risk (default: 95%).
4. Write tests spanning all three verification tiers: IQ, OQ, and PQ.
5. Generate signed evidence packages for every verification run using the configured signing algorithm.
6. Request peer review before any merge. The merge MUST NOT proceed until review is approved.
7. Update the risk assessment log with a rationale entry for any behavioral change.
8. Preserve all test output including failures, re-runs, and intermediate results. Selective deletion of test evidence is a data integrity violation.

**The agent MUST NOT:**

1. Skip or weaken any test to make a gate pass.
2. Modify evidence packages after generation.
3. Bypass signing requirements for any reason.
4. Merge code without completed peer review.
5. Modify risk levels without explicit human authorization.

### 2.2 MEDIUM Risk Components

MEDIUM risk components affect regulated workflows or critical metadata but have no direct patient safety impact. The agent SHOULD apply thorough verification with pragmatic scope.

**The agent SHOULD:**

1. Maintain complete traceability from specification through implementation to tests.
2. Include `@gxp-tag` and `@gxp-criticality MEDIUM` annotations in source and test files.
3. Achieve test coverage at or above the `coverage_threshold` defined for MEDIUM risk (default: 80%).
4. Write tests for OQ and PQ verification tiers.
5. Generate signed evidence packages for verification runs.

**The agent MAY:**

1. Omit IQ-tier verification if infrastructure components are unchanged.
2. Proceed without peer review, provided all automated gates pass.

### 2.3 LOW Risk Components

LOW risk components have no GxP data impact. The agent MAY apply minimal verification while maintaining basic traceability.

**The agent SHOULD:**

1. Maintain traceability at the specification level (source files link to specs).
2. Include `@gxp-criticality LOW` annotations in source files.
3. Achieve test coverage at or above the `coverage_threshold` defined for LOW risk (default: 60%).
4. Write OQ-tier tests for functional correctness.

**The agent MAY:**

1. Omit IQ and PQ verification tiers.
2. Omit cryptographic signing of evidence packages.
3. Omit peer review.

### 2.4 Strict Mode

When `agent.mode` is set to `strict`, ALL components are treated as HIGH risk regardless of their actual classification. All MUST-level directives from Section 2.1 apply universally. This mode is appropriate for initial validation campaigns or systems with uniformly high regulatory exposure.

### 2.5 Advisory Mode

When `agent.mode` is set to `advisory`, all directives are downgraded to SHOULD-level recommendations. Violations produce warnings but never block workflow progression. This mode is appropriate during GxP.MD adoption when teams are migrating from unstructured workflows.

---

## 3. Development Rules

### 3.1 Session Start Protocol

When an AI agent begins a development session on a project containing a GxP.MD file, it MUST execute the `agent.on_session_start` sequence defined in the frontmatter. The default sequence is:

1. **Read GxP.MD** at the project root. Parse the YAML frontmatter to load regulatory context, risk configuration, and gate definitions.
2. **Read `.gxp/system_context.md`** to understand the system description, boundaries, intended use, and operational environment.
3. **Read `.gxp/risk_assessment.log`** to understand current risks, open mitigations, and any risk-related constraints on development.
4. **Run a traceability audit** to identify orphan artifacts, broken links, and coverage gaps before making any changes.

The agent SHOULD report any findings from the session start protocol to the human operator before proceeding with development tasks.

### 3.2 Before Writing Code

Before writing implementation code for any GxP-relevant functionality, the agent MUST:

1. **Identify the governing specification.** Locate the `SPEC-XXX-XXX` artifact in `.gxp/specs/` that governs the functionality to be implemented. If no specification exists, create one first.
2. **Verify the traceability chain.** Confirm that the specification traces to a user story, and the user story traces to a requirement. If gaps exist, create the missing artifacts.
3. **Assess the risk level.** Determine whether the component is HIGH, MEDIUM, or LOW risk based on the risk taxonomy in Section 1.3 and the project's risk assessment log.
4. **Check for related open risks.** Review `.gxp/risk_assessment.log` for any open risks or mitigations that affect the component under development.
5. **Plan the verification approach.** Determine which verification tiers (IQ, OQ, PQ) are required based on the risk level and plan the test structure accordingly.

### 3.3 While Writing Code

While writing implementation code, the agent MUST:

1. **Maintain GxP tag annotations.** Every source file implementing GxP-relevant logic MUST include annotations in the following format:

   ```
   // @gxp-tag SPEC-001-003
   // @gxp-criticality HIGH
   ```

   Or the equivalent comment syntax for the file's language.

2. **Preserve existing annotations.** The agent MUST NOT remove or modify existing `@gxp-tag` annotations unless the traceability mapping has genuinely changed.

3. **Follow the specification.** Implementation MUST conform to the design approach described in the governing specification. Deviations from the specification require an Architecture Decision Record (ADR) in `.gxp/adr/`.

4. **Update risk assessment when needed.** If the implementation introduces a new risk vector (e.g., a new external dependency, a new data flow involving PHI, a change to authentication logic), the agent MUST add an entry to `.gxp/risk_assessment.log` with:
   - Date and author
   - Component affected
   - Risk description
   - Proposed mitigation
   - Risk level (HIGH/MEDIUM/LOW)

5. **Respect system boundaries.** The agent MUST NOT modify code outside the scope of the governing specification without first creating or updating the relevant specification artifacts.

### 3.4 After Writing Code

After completing implementation code, the agent MUST:

1. **Run all affected tests.** Execute tests for the modified component across all required verification tiers.
2. **Verify coverage thresholds.** Confirm that test coverage meets or exceeds the threshold defined for the component's risk level.
3. **Generate evidence packages.** Produce evidence packages for each verification tier executed (see Section 5.3).
4. **Run gate checks.** Execute the `pre_commit` gate checks defined in the frontmatter.
5. **Report results.** Summarize test results, coverage metrics, and gate status to the human operator.

If any gate check fails, the agent MUST NOT proceed with the commit. The agent MUST identify the failure, propose a remediation, and request human guidance if the fix is non-trivial.

---

## 4. Documentation Rules

### 4.1 Artifact Frontmatter Schema

All validation artifacts in the `.gxp/` directory MUST use YAML frontmatter conforming to the schemas below. The frontmatter is both human-readable documentation and machine-parseable metadata.

#### 4.1.1 Requirements (`.gxp/requirements/REQ-NNN.md`)

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
created: "2026-01-15"
updated: "2026-01-15"
author: "author@example.com"
---
```

**Body:** Detailed requirement narrative including regulatory basis, business justification, and any constraints.

#### 4.1.2 User Stories (`.gxp/user_stories/US-NNN-NNN.md`)

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
created: "2026-01-15"
updated: "2026-01-15"
author: "author@example.com"
---
```

**Body:** User story narrative in standard "As a [role], I want [capability], so that [benefit]" format, followed by detailed acceptance criteria and edge cases.

#### 4.1.3 Technical Specifications (`.gxp/specs/SPEC-NNN-NNN.md`)

```yaml
---
gxp_id: SPEC-001-001
title: "Specification title"
parent_id: US-001-001              # Parent user story ID
verification_tier: OQ              # IQ | OQ | PQ
design_approach: "Brief description of the implementation approach"
source_files:
  - "src/modules/auth/login.ts"
  - "src/modules/auth/session.ts"
test_files:
  - "tests/oq/auth/login.test.ts"
  - "tests/pq/auth/login.e2e.ts"
validation_status: draft           # draft | in_review | validated | retired
created: "2026-01-15"
updated: "2026-01-15"
author: "author@example.com"
---
```

**Body:** Detailed technical design including data flows, API contracts, error handling strategy, and security considerations.

#### 4.1.4 Validation Status Lifecycle

Artifacts progress through the following statuses:

| Status | Meaning |
|--------|---------|
| `draft` | Initial creation. Content may be incomplete. |
| `in_review` | Content complete. Awaiting peer review or quality review. |
| `validated` | Reviewed and approved. Linked implementation and tests are verified. |
| `retired` | No longer active. Retained for audit trail purposes. |

An agent MUST NOT set `validation_status` to `validated` without human authorization. Validation is a quality decision that requires human judgement.

### 4.2 Architecture Decision Records

When the agent deviates from a specification's design approach or makes a significant architectural decision, it MUST create an ADR in `.gxp/adr/`.

ADR filename format: `ADR-{NNN}-{short-description}.md`

```yaml
---
adr_id: ADR-001
title: "Decision title"
status: proposed                   # proposed | accepted | superseded | deprecated
date: "2026-01-15"
decision_makers:
  - "author@example.com"
related_specs:
  - SPEC-001-001
---
```

**Body sections:**
- **Context:** What situation prompted this decision?
- **Decision:** What was decided and why?
- **Consequences:** What are the trade-offs? What changes as a result?
- **Alternatives Considered:** What other options were evaluated?

### 4.3 Change Control

When modifying existing artifacts:

1. The `updated` field in frontmatter MUST be set to the current date.
2. The `validation_status` MUST be reset to `draft` if the change is substantive (alters acceptance criteria, design approach, or risk level).
3. The project `version` field in the GxP.MD frontmatter SHOULD be incremented following semantic versioning:
   - **PATCH** for non-functional changes (typos, formatting, clarifications).
   - **MINOR** for new artifacts or non-breaking functional changes.
   - **MAJOR** for breaking changes to interfaces, data models, or risk levels.

---

## 5. Testing Rules

### 5.1 Test Tag Format

All test files in a GxP.MD-governed project MUST include standardized annotations that enable automated traceability auditing and evidence generation.

#### Required Tags

| Tag | Format | Description |
|-----|--------|-------------|
| `@gxp-tag` | `@gxp-tag SPEC-NNN-NNN` | Links the test to the specification it verifies |
| `@trace` | `@trace US-NNN-NNN` | Links the test to the user story it validates |
| `@test-type` | `@test-type IQ\|OQ\|PQ` | Declares the verification tier |
| `@gxp-criticality` | `@gxp-criticality HIGH\|MEDIUM\|LOW` | Declares the risk level of the tested component |

#### Example (TypeScript / Vitest)

```typescript
/**
 * @gxp-tag SPEC-001-003
 * @trace US-001-001
 * @test-type OQ
 * @gxp-criticality HIGH
 */
describe("User authentication - login flow", () => {
  it("should reject invalid credentials with appropriate error", () => {
    // test implementation
  });

  it("should create audit trail entry on successful login", () => {
    // test implementation
  });
});
```

#### Tag Placement

- Tags MUST appear in a block comment at the top of the test file or immediately preceding the test suite (describe block) they govern.
- A single test file MAY contain multiple tag blocks if it covers multiple specifications. Each block governs the test suite that immediately follows it.
- Tags MUST use the exact format specified. Deviations (e.g., missing hyphens, incorrect casing) will cause traceability audit failures.

### 5.2 Verification Tier Organization

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
- Coverage reports

**PQ (Performance Qualification):**
Verifies that the system performs acceptably in conditions approximating real-world use.

- End-to-end tests simulating user workflows
- Screenshots or visual regression tests
- Performance traces and timing assertions
- Load tests under expected concurrency
- Accessibility compliance tests (where applicable)

### 5.3 Evidence Generation

Every test execution that contributes to GxP verification MUST produce an evidence package. Evidence packages are self-contained directories stored in `.gxp/evidence/`.

#### Package Structure

```
.gxp/evidence/{TIER}-{SPEC_ID}-{TIMESTAMP}/
├── metadata.json          # Test identity and result summary
├── environment.json       # Runtime environment snapshot
├── test-output.log        # Raw test runner output (complete, unedited)
├── manifest.json          # SHA-256 hashes of all files in this package
└── signature.jws          # ES256 signature over manifest.json (if required)
```

#### metadata.json Schema

```json
{
  "spec_id": "SPEC-001-003",
  "tier": "OQ",
  "gxp_criticality": "HIGH",
  "timestamp": "2026-01-15T14:30:00Z",
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

#### environment.json Schema

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

#### manifest.json Schema

```json
{
  "algorithm": "SHA-256",
  "files": {
    "metadata.json": "sha256:...",
    "environment.json": "sha256:...",
    "test-output.log": "sha256:..."
  },
  "generated_at": "2026-01-15T14:30:05Z"
}
```

#### Signing

When `signing_required` is `true` for the component's risk level, the evidence package MUST include a `signature.jws` file containing an ES256 (ECDSA with P-256) JSON Web Signature over the contents of `manifest.json`.

The signing key MUST be managed according to the `evidence.key_management` configuration:

| Method | Description |
|--------|-------------|
| `repository` | Key pair stored in `.gxp/keys/` (suitable for development; NOT for production) |
| `vault` | Key pair managed by a secrets manager (e.g., HashiCorp Vault, AWS KMS) |
| `hsm` | Key pair stored in a Hardware Security Module (highest assurance) |

The agent MUST NOT generate, rotate, or delete signing keys without explicit human authorization.

#### Evidence Integrity Rules

1. Evidence packages MUST NOT be modified after generation. Any modification invalidates the manifest hashes and signature.
2. Failed test runs MUST be preserved in evidence. Selective deletion of failure evidence is a data integrity violation under ALCOA+ principles.
3. The `test-output.log` MUST contain the complete, unedited output from the test runner. Truncation or filtering is prohibited.
4. The `system_state_hash` in `metadata.json` MUST be computed at the time of test execution using the algorithm and scope defined in `evidence.state_hash`.

### 5.4 Fallback Inference for Untagged Tests

When the agent encounters test files that lack `@gxp-tag` annotations (e.g., in legacy codebases being migrated to GxP.MD), it SHOULD apply fallback inference rules:

1. **Directory-based inference:** Tests in `tests/iq/` are inferred as IQ tier, `tests/oq/` as OQ, `tests/pq/` as PQ.
2. **Filename-based inference:** Files ending in `.e2e.ts` or `.e2e.test.ts` are inferred as PQ tier. Files ending in `.test.ts` without further qualification are inferred as OQ tier.
3. **No inference for criticality or traceability.** The agent MUST NOT infer `@gxp-criticality` or `@gxp-tag` values. These require explicit annotation.

Inferred tags SHOULD be flagged in the traceability audit report with a recommendation to add explicit annotations.

---

## 6. Data Integrity — ALCOA+ Compliance

ALCOA+ is the gold standard for data integrity in pharmaceutical and life sciences environments. Every AI agent operating under GxP.MD MUST respect these principles in all actions that create, modify, or reference regulated data and artifacts.

### 6.1 Attributable

Every action that creates or modifies a regulated artifact MUST be attributable to a specific individual.

**Agent Rules:**

- The agent MUST ensure that all commits are authored by an identifiable individual (via `git_author`). Commits with generic, shared, or anonymous authorship are non-compliant.
- When an AI agent generates code or artifacts, the commit MUST be attributed to the human operator who directed the work. The agent MAY be identified as a co-author (e.g., via `Co-Authored-By` trailer) but MUST NOT be the sole author of record.
- Evidence packages MUST record the responsible individual in `metadata.json`.

### 6.2 Legible

All artifacts, evidence, and documentation MUST be readable and understandable by qualified personnel.

**Agent Rules:**

- Markdown artifacts MUST pass a markdown linter without errors. The linter configuration SHOULD be defined in the project's tooling setup.
- Code comments and annotations MUST be written in clear, unambiguous language.
- Evidence package contents MUST be in standard, non-proprietary formats (JSON, plain text, markdown).
- The agent MUST NOT produce artifacts that require specialized tooling to read beyond standard text editors and JSON parsers.

### 6.3 Contemporaneous

Records MUST be created at the time the activity occurs, not retroactively.

**Agent Rules:**

- Evidence packages MUST be generated immediately after test execution, within the same CI/CD run or development session.
- The timestamp in `metadata.json` MUST be within 5 minutes of the actual test execution time.
- The agent MUST NOT backdate or forward-date any timestamps in artifacts or evidence.
- Commits SHOULD be made promptly after completing work. Large batches of uncommitted changes indicate a contemporaneity risk.

### 6.4 Original

Records MUST be the first-generation, unaltered version.

**Agent Rules:**

- Evidence packages MUST be signed using JWS to prove they have not been altered after generation.
- The manifest hash chain (file hashes → manifest → signature) provides cryptographic proof of originality.
- The agent MUST NOT regenerate evidence packages to replace unfavorable results. If a test fails and is subsequently fixed, BOTH the failure evidence and the passing evidence MUST be retained.
- Copies of artifacts (e.g., for archival or reporting) MUST reference the original location and hash.

### 6.5 Accurate

Records MUST correctly reflect the activity they document.

**Agent Rules:**

- The system state hash recorded in evidence packages MUST match the actual SHA-256 hash of the `/src` tree at the time of test execution.
- Coverage numbers in `metadata.json` MUST match the raw coverage data in the test output.
- The agent MUST NOT manually adjust test results, coverage numbers, or any other metrics in evidence packages.
- If a discrepancy is detected between test output and metadata, the agent MUST flag the discrepancy and regenerate the evidence package.

### 6.6 Complete (ALCOA+ Extension)

All data MUST be present, including failed attempts, re-runs, and negative results.

**Agent Rules:**

- All test executions MUST produce evidence packages — not only successful runs.
- When a test suite is re-run after a failure, both the failing evidence package and the passing evidence package MUST be retained. Evidence directories are append-only.
- Skip counts MUST be recorded and justified. An agent MUST NOT skip tests to improve pass rates without documenting the justification in the evidence metadata.
- Partial test runs MUST be flagged as incomplete in `metadata.json`.

### 6.7 Consistent (ALCOA+ Extension)

Records MUST demonstrate logical consistency in timestamps, sequences, and cross-references.

**Agent Rules:**

- Evidence package timestamps MUST be chronologically consistent with the commit history. Evidence cannot precede the commit that introduced the tested code.
- Artifact version sequences MUST be monotonically increasing. An agent MUST NOT create artifacts with IDs that conflict with or duplicate existing artifacts.
- Cross-references between artifacts MUST be bidirectionally consistent. If SPEC-001-001 references US-001-001 as its parent, then US-001-001's child list MUST include SPEC-001-001.

### 6.8 Enduring (ALCOA+ Extension)

Records MUST survive for the defined retention period.

**Agent Rules:**

- Evidence packages MUST NOT be deleted before `evidence.retention_days` has elapsed.
- The agent MUST NOT include evidence directories in `.gitignore` or any other exclusion mechanism.
- When evidence approaches the retention limit, the agent SHOULD notify the human operator to initiate archival procedures.
- Archived evidence MUST remain retrievable and verifiable (signature and hash chain intact).

### 6.9 Available (ALCOA+ Extension)

Records MUST be accessible to authorized parties when needed.

**Agent Rules:**

- All artifacts and evidence MUST be stored in the `.gxp/` directory within the project repository, accessible to all authorized contributors.
- Evidence packages MUST NOT be encrypted with individual keys that would prevent authorized access. If encryption is required, use team-level or organizational keys.
- The agent SHOULD maintain an index of evidence packages (e.g., `.gxp/evidence/index.json`) to facilitate rapid retrieval during audits.

---

## 7. Quality Gate Checklists

Quality gates are enforcement checkpoints that prevent non-compliant code from progressing through the development lifecycle. The following checklists expand on the gate definitions in the frontmatter.

### 7.1 Pre-Commit Gate

Checked before every commit to the repository. These gates protect the integrity of the codebase at the individual change level.

- [ ] **Traceability audit passes.** All modified source files containing GxP-relevant logic include valid `@gxp-tag` annotations linking to specifications in `.gxp/specs/`.
- [ ] **Risk assessment is current.** If the change introduces new risk vectors or modifies risk mitigations, `.gxp/risk_assessment.log` has been updated.
- [ ] **No orphan artifacts.** No artifacts exist in `.gxp/` without a valid traceability chain to a parent artifact. No specifications reference non-existent user stories; no user stories reference non-existent requirements.
- [ ] **GxP tags are syntactically valid.** All `@gxp-tag`, `@trace`, `@test-type`, and `@gxp-criticality` annotations conform to the formats defined in Section 5.1.
- [ ] **No unresolved conflicts.** No merge conflict markers exist in any committed file.

### 7.2 Pre-Merge Gate

Checked before merging a feature branch into the main branch. These gates protect the shared codebase and ensure verification is complete.

- [ ] **All tests pass.** All IQ, OQ, and PQ tests for the affected components execute successfully. Zero test failures.
- [ ] **Coverage meets threshold.** Test coverage for every modified component meets or exceeds the threshold defined for its risk level in the risk matrix.
- [ ] **Evidence packages are signed.** For components where `signing_required` is `true`, all evidence packages include valid `signature.jws` files.
- [ ] **Peer review is complete.** For components where `review_required` is `true`, at least one qualified reviewer has approved the changes.
- [ ] **No draft-status artifacts for merged code.** All artifacts governing the merged functionality have `validation_status` of `in_review` or higher. No `draft` artifacts may govern production code on the main branch.

### 7.3 Pre-Release Gate

Checked before creating a release artifact (tag, package, deployment). These gates protect the deployed product and ensure the complete validation record is intact.

- [ ] **All pre-commit and pre-merge gates pass.** The cumulative gate status for all changes since the last release is clean.
- [ ] **All artifacts are validated.** Every requirement, user story, and specification governing the release has `validation_status: validated`.
- [ ] **Evidence is archived.** All evidence packages for the release are archived and retrievable outside the active repository (e.g., in an artifact store or compliance vault).
- [ ] **Risk assessment is signed off.** The risk assessment log has been reviewed and signed off by the quality owner identified in `project.owner`.
- [ ] **System state hash is recorded.** The SHA-256 hash of the `/src` tree at the release commit is recorded in the release manifest and matches the hash in the most recent evidence packages.
- [ ] **Release manifest is complete.** A release manifest enumerating all artifacts, evidence packages, and their hashes is generated and signed.

---

## 8. Repository Structure

A project governed by GxP.MD MUST maintain the following directory structure:

```
project-root/
├── GxP.MD                         # This file — compliance instructions
├── .gxp/                          # Validation artifact root
│   ├── system_context.md          # System description, boundaries, intended use
│   ├── risk_assessment.log        # Running risk assessment log
│   ├── requirements/              # Requirement artifacts (REQ-NNN.md)
│   ├── user_stories/              # User story artifacts (US-NNN-NNN.md)
│   ├── specs/                     # Technical specifications (SPEC-NNN-NNN.md)
│   ├── adr/                       # Architecture decision records (ADR-NNN-*.md)
│   ├── evidence/                  # Signed evidence packages
│   │   ├── index.json             # Evidence package index (optional but recommended)
│   │   ├── IQ-SPEC-001-001-20260115T143000/
│   │   ├── OQ-SPEC-001-001-20260115T143000/
│   │   └── PQ-SPEC-001-001-20260115T150000/
│   └── keys/                      # Signing keys (if key_management: repository)
├── src/                           # Source code
└── tests/                         # Test code, organized by tier
    ├── iq/
    ├── oq/
    └── pq/
```

### 8.1 System Context Document

The `.gxp/system_context.md` file MUST describe:

- **System name and purpose.** What the system does and why it exists.
- **System boundaries.** What is in scope and what is out of scope for GxP validation.
- **Intended use.** Who uses the system, in what context, and for what purpose.
- **Operational environment.** Where the system runs (cloud, on-premise, hybrid) and key infrastructure dependencies.
- **Interfaces.** External systems, APIs, and data flows that cross the system boundary.
- **Regulatory basis.** Which regulations apply and why.

### 8.2 Risk Assessment Log

The `.gxp/risk_assessment.log` is a chronological record of risk identification, assessment, and mitigation activities. Each entry MUST include:

```markdown
## RISK-{NNN}: {Title}

- **Date:** 2026-01-15
- **Author:** author@example.com
- **Component:** src/modules/auth/
- **Risk Level:** HIGH
- **Description:** Description of the identified risk.
- **Impact:** What could go wrong if the risk materializes.
- **Mitigation:** What controls are in place to reduce the risk.
- **Status:** open | mitigated | accepted | closed
```

---

## 9. Appendix A: Regulatory Profile Reference

The `regulatory.profile` field in the frontmatter selects a built-in configuration preset that adjusts default behaviors for common regulatory scenarios. Profiles set sensible defaults; individual fields can still be overridden.

### 9.1 `pharma-standard`

**Scope:** General pharmaceutical software systems subject to GxP regulations.

**Typical use:** Manufacturing execution systems, laboratory information management, quality management systems, document management, batch record systems.

**Default configuration:**
- Frameworks: 21 CFR Part 11, EU Annex 11
- GAMP Category: 5 (custom software)
- All three verification tiers required for HIGH risk
- Evidence signing required for HIGH and MEDIUM risk
- Peer review required for HIGH risk

### 9.2 `medical-device`

**Scope:** Software that is or is a component of a medical device, subject to IEC 62304 and FDA 21 CFR Part 820.

**Typical use:** Software as a Medical Device (SaMD), embedded device firmware, clinical decision support systems, diagnostic software.

**Default configuration:**
- Frameworks: IEC 62304, 21 CFR Part 820, EU MDR
- GAMP Category: 5
- Software safety classification mapping (Class A/B/C per IEC 62304)
- All three verification tiers required for MEDIUM and HIGH risk
- Evidence signing required at all risk levels
- Peer review required for MEDIUM and HIGH risk
- Additional requirement for software of unknown provenance (SOUP) documentation

### 9.3 `clinical-trial`

**Scope:** Software supporting clinical trial operations, subject to 21 CFR Part 11 and ICH E6(R2) GCP.

**Typical use:** Electronic data capture (EDC), randomization and trial supply management (RTSM), clinical trial management systems (CTMS), ePRO/eCOA platforms.

**Default configuration:**
- Frameworks: 21 CFR Part 11, ICH E6(R2), EU Annex 11
- GAMP Category: 5
- Enhanced audit trail requirements (capture before/after values for all data changes)
- All three verification tiers required for HIGH risk
- Evidence signing required at all risk levels
- Peer review required for HIGH and MEDIUM risk

### 9.4 `laboratory`

**Scope:** Laboratory informatics software subject to GLP and GMP requirements.

**Typical use:** LIMS, chromatography data systems, electronic lab notebooks, instrument integration software.

**Default configuration:**
- Frameworks: 21 CFR Part 11, OECD GLP Principles, EU Annex 11
- GAMP Category: 4 or 5
- Emphasis on data acquisition integrity (instrument-to-system data flow)
- OQ and PQ verification tiers required for MEDIUM and HIGH risk
- Evidence signing required for HIGH risk
- Peer review required for HIGH risk

---

## 10. Appendix B: Custom Directives

GxP.MD supports project-specific extensions through the custom directives section. These directives augment (but MUST NOT contradict) the standard directives defined in this specification.

### 10.1 Defining Custom Directives

Custom directives are added as additional sections in the markdown body of the project's GxP.MD file, after the standard sections. They MUST be clearly demarcated:

```markdown
---

## Custom Directives

### CD-001: [Directive Title]

**Scope:** Which components or activities this directive applies to.
**Risk Level:** HIGH | MEDIUM | LOW
**Directive:** The behavioral instruction using RFC 2119 keywords.
**Rationale:** Why this directive exists (regulatory basis or business justification).
```

### 10.2 Custom Directive Rules

1. Custom directives MUST use RFC 2119 keywords for severity.
2. Custom directives MUST NOT weaken any MUST-level standard directive. A custom directive cannot make something optional that the standard requires.
3. Custom directives MAY strengthen SHOULD-level or MAY-level standard directives (e.g., making a SHOULD into a MUST for a specific project).
4. Custom directives MUST include a rationale explaining their regulatory or business basis.
5. Custom directives SHOULD be reviewed and approved by the quality owner before inclusion.

### 10.3 Custom Frontmatter Extensions

The YAML frontmatter supports a `custom` key for project-specific configuration:

```yaml
custom:
  electronic_signatures:
    require_meaning: true       # Require signature meaning (e.g., "approved", "reviewed")
    require_mfa: true           # Require multi-factor authentication for signing
  audit_trail:
    capture_before_after: true  # Capture before/after values for all data changes
    require_reason: true        # Require reason-for-change on every modification
  soup:                         # Software of Unknown Provenance
    inventory_required: true
    risk_assessment_required: true
```

Custom frontmatter keys are opaque to the GxP.MD specification — they are consumed by tooling and agents that understand the project-specific extensions.

---

## 11. Appendix C: Glossary

| Term | Definition |
|------|-----------|
| **ADR** | Architecture Decision Record. A document recording a significant architectural decision, its context, and consequences. |
| **ALCOA+** | Attributable, Legible, Contemporaneous, Original, Accurate + Complete, Consistent, Enduring, Available. The regulatory standard for data integrity. |
| **Artifact** | A documented deliverable in the validation lifecycle: requirement, user story, specification, or evidence package. |
| **Evidence Package** | A self-contained directory containing test results, environment data, manifest hashes, and cryptographic signature proving verification was performed. |
| **GAMP** | Good Automated Manufacturing Practice. ISPE guidelines for validating computerized systems. Category 5 = custom-built software. |
| **Gate** | An enforcement checkpoint that blocks workflow progression until defined conditions are met. |
| **GxP** | Good Practice. An umbrella term for quality guidelines and regulations including GMP, GLP, GCP, GDP, and related standards. |
| **IQ** | Installation Qualification. Verification that a system is installed correctly with all dependencies present and configured. |
| **JWS** | JSON Web Signature. A standard (RFC 7515) for digitally signing JSON payloads. Used for evidence package signing. |
| **OQ** | Operational Qualification. Verification that a system functions correctly according to its specifications. |
| **PHI** | Protected Health Information. Individually identifiable health data subject to privacy regulations (e.g., HIPAA). |
| **PQ** | Performance Qualification. Verification that a system performs acceptably under conditions approximating real-world use. |
| **Risk Matrix** | The configuration mapping risk levels (HIGH/MEDIUM/LOW) to enforcement requirements (coverage, tiers, signing, review). |
| **ROSIE** | The artifact and evidence standard (RFC-001) that defines the `.gxp/` directory structure and evidence package format. |
| **SOUP** | Software of Unknown Provenance. Third-party software components not developed under the project's quality system. |
| **Traceability** | The ability to follow an artifact from its origin requirement through implementation to verification evidence, and vice versa. |
| **V-Model** | A software development model where each development phase has a corresponding verification phase, forming a V-shape. |
| **Verification Tier** | A category of testing activity (IQ, OQ, or PQ) aligned with qualification protocols in the V-Model. |

---

## 12. Appendix D: Conformance

### 12.1 Specification Conformance Levels

Implementations of GxP.MD tooling MUST declare their conformance level:

| Level | Description |
|-------|-------------|
| **Level 1: Parse** | Can parse GxP.MD frontmatter and extract configuration values. |
| **Level 2: Audit** | Level 1 + can perform traceability audits and identify gaps. |
| **Level 3: Enforce** | Level 2 + can enforce quality gates and block non-compliant actions. |
| **Level 4: Generate** | Level 3 + can generate evidence packages with signing. |
| **Level 5: Full** | Level 4 + can create and manage the complete artifact lifecycle. |

### 12.2 Agent Conformance

An AI coding agent claims GxP.MD conformance by declaring which specification version it supports and at what level. Conformance is demonstrated through behavior, not assertion — an agent claiming Level 5 conformance MUST be capable of executing all directives in this specification when operating on a GxP.MD-governed project.

### 12.3 Version Compatibility

GxP.MD follows semantic versioning. Tooling MUST:

- Support the exact `gxpmd_version` declared in the frontmatter.
- SHOULD support backward-compatible minor versions (e.g., tooling supporting 1.2.0 SHOULD support 1.0.0 and 1.1.0).
- MUST reject frontmatter with a major version it does not support, with a clear error message.

---

*End of GxP.MD Specification v1.0.0*
