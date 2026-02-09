```
   ______      ____    __  ___ ____
  / ____/_ __ / __ \  /  |/  // __ \
 / / __ | \/ // /_/ / / /|_/ // / / /
/ /_/ / >  < / ____/ / /  / // /_/ /
\____/ /_/\_\/_/     /_/  /_//_____/

  Compliance instructions for AI coding agents.
  One file. Any agent. Every regulated project.
```

<p align="center">
  <a href="https://gxp.md/spec"><img src="https://img.shields.io/badge/spec-v3.0.0-0d9488?style=flat-square" alt="Spec v3.0.0"></a>
  <a href="https://github.com/PL-James/gxp-md/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square" alt="License"></a>
  <a href="https://github.com/PL-James/gxp-md/issues"><img src="https://img.shields.io/github/issues/PL-James/gxp-md?style=flat-square&color=orange" alt="Issues"></a>
  <a href="https://github.com/sponsors/PL-James"><img src="https://img.shields.io/badge/sponsor-%E2%9D%A4-pink?style=flat-square" alt="Sponsor"></a>
</p>

---

## What is GxP.MD?

**GxP.MD** is a markdown-based compliance instruction standard for AI-assisted software development in regulated pharmaceutical and life sciences industries.

Drop a `GxP.MD` file in your project root. Your AI agent reads it, understands the regulatory context, and produces compliant code with full V-Model traceability — automatically.

```
 Your Project/
 +-- GxP.MD              <-- The compliance contract
 +-- .gxp/               <-- Artifacts, evidence, reports
 +-- src/                 <-- Code WITH inline annotations
 \-- tests/
     +-- iq/              <-- Installation Qualification
     +-- oq/              <-- Operational Qualification
     \-- pq/              <-- Performance Qualification
```

### The idea

AI agents are great at writing code. They're terrible at regulatory compliance — unless you tell them exactly what the rules are. GxP.MD is that instruction set: a single file that turns any AI coding agent into a GxP-aware development partner.

```
  REQ ──satisfies──▶ US ──implements──▶ SPEC ──implements──▶ CODE ──verifies──▶ TEST
   │                  │                   │                    ▲                  ▲
   └──satisfies───────┴───implements──────┴────────────────────┘──────verifies────┘
                         (many-to-many edges via @gxp-satisfies, @gxp-implements, @gxp-verifies)
```

### Key properties

- **Annotation-first** — traceability lives in code comments, not separate docs
- **Gate enforcement** — defines what must be true, not how to work
- **Risk-proportionate** — HIGH/MEDIUM/LOW with scaled requirements
- **Agent-agnostic** — works with Claude, GPT, Gemini, Copilot, or any future agent
- **Two-mode system** — lightweight `develop` mode, formalized `harden` mode per sprint
- **ALCOA+ compliant** — contemporaneous compliance records, not retroactive audit prep
- **Graph-based traceability** — many-to-many relationships via explicit edge tags, not ID encoding

### What's New in v3

v3 replaces the hierarchical ID-scheme traceability of v2 with a directed acyclic graph (DAG) model:

- **Edge tags**: `@gxp-satisfies`, `@gxp-implements`, `@gxp-verifies` replace `@gxp-req`, `@gxp-spec`, `@trace`
- **Opaque IDs**: `REQ-001`, `US-042`, `SPEC-137` — numbers don't encode parentage
- **Many-to-many**: A source file can satisfy multiple requirements, a test can verify multiple specs
- **Skipped phases**: LOW-risk paths like SPEC → CODE → TEST are valid shorter paths, not errors
- **Graph coverage**: Coverage is calculated via reachability analysis, not chain completeness

See [RFC-002](spec/rfc/RFC-002-graph-traceability.md) for the full rationale and migration guide.

---

## Quick Start

**1. Copy the starter template into your project:**

```bash
curl -o GxP.MD https://raw.githubusercontent.com/PL-James/gxp-md/main/templates/GxP.MD.starter
```

**2. Edit the YAML frontmatter** — set your project name, regulatory profile, and risk matrix.

**3. Initialize the artifact directory:**

```bash
mkdir -p .gxp/requirements .gxp/user_stories .gxp/specs .gxp/evidence .gxp/adr
```

**4. Start developing.** Your AI agent reads `GxP.MD` at session start and operates compliantly.

**5. Harden every sprint:**

```bash
python tools/gxpmd-harden.py --root .
```

This runs the compliance sweep: validates annotations, builds the traceability matrix, generates artifact stubs, and produces the compliance status report.

---

## Repository Structure

```
gxp-md/
+-- spec/                    # The specification (source of truth)
|   +-- GxP.MD               #   Canonical spec document
|   +-- schema/v1.json        #   JSON Schema for frontmatter validation
|   \-- profiles/             #   Built-in regulatory profiles
|       +-- pharma-standard.yml
|       +-- medical-device.yml
|       +-- clinical-trial.yml
|       \-- laboratory.yml
|
+-- templates/               # Starter templates for adoption
|   +-- GxP.MD.starter        #   Drop-in GxP.MD file
|   +-- system-context.md     #   .gxp/system_context.md template
|   +-- requirement.md        #   .gxp/requirements/REQ-NNN.md
|   +-- user-story.md         #   .gxp/user_stories/US-NNN.md
|   +-- specification.md      #   .gxp/specs/SPEC-NNN.md
|   \-- evidence-manifest.json
|
+-- tools/                   # Compliance tooling
|   \-- gxpmd-harden.py       #   Compliance sweep tool (stdlib Python)
|
\-- site/                    # Documentation microsite (gxp.md)
```

## Regulatory Profiles

| Profile | Frameworks | Use Case |
|---------|-----------|----------|
| `pharma-standard` | 21 CFR Part 11, EU Annex 11, GAMP 5 | MES, LIMS, QMS, batch records |
| `medical-device` | IEC 62304, 21 CFR 820, EU MDR | SaMD, firmware, diagnostics |
| `clinical-trial` | ICH E6(R2), 21 CFR Part 11 | EDC, RTSM, CTMS, ePRO |
| `laboratory` | 21 CFR Part 58 (GLP), ISO 17025 | LIMS, CDS, ELN |

## How Annotations Work

Source files declare what they satisfy and implement:

```typescript
/**
 * @gxp-satisfies REQ-001, REQ-003
 * @gxp-implements SPEC-042
 * @gxp-risk HIGH
 */
export async function authenticate(creds: Credentials) { /* ... */ }
```

Test files declare what they verify:

```typescript
/**
 * @gxp-verifies SPEC-042
 * @test-type OQ
 * @gxp-risk HIGH
 */
describe("OAuth2 PKCE login", () => { /* ... */ });
```

Together they form the complete traceability graph — no separate documentation system needed.

## Harden Tool

`gxpmd-harden.py` is a zero-dependency Python script that executes the compliance sweep:

```
$ python tools/gxpmd-harden.py --root /path/to/project

============================================================
  GxP.MD COMPLIANCE SWEEP COMPLETE
============================================================
  Requirements:     12
  Complete chains:  11/12
  Errors:           1
  Warnings:         2
  Annotated files:  34
============================================================
```

**Outputs:**
- `.gxp/traceability-matrix.json` — traceability graph (DAG)
- `.gxp/compliance-status.md` — human-readable compliance report with sign-off section
- `.gxp/gap-analysis.json` — all validation errors, orphans, and coverage shortfalls
- `.gxp/requirements/REQ-NNN.md` — auto-generated stubs from annotations (draft)
- `.gxp/specs/SPEC-NNN.md` — auto-generated stubs from annotations (draft)

---

## Ecosystem

| Project | Description |
|---------|-------------|
| [**ROSIE RFC-001**](https://github.com/PL-James/ROSIE) | Artifact/evidence standard that GxP.MD wraps |
| [**Nexus**](https://github.com/PL-James/nexus) | GxP validation platform that consumes GxP.MD contracts |

## Documentation

Full documentation at **[gxp.md](https://gxp.md)** (or [gxp-md.pages.dev](https://gxp-md.pages.dev)):

- [Specification](https://gxp.md/spec) — the complete standard
- [Getting Started](https://gxp.md/getting-started) — step-by-step adoption guide
- [Templates](https://gxp.md/templates) — downloadable starter files
- [Regulatory Profiles](https://gxp.md/profiles) — pre-built compliance configurations

---

## Contributing

Contributions are welcome. Please open an [issue](https://github.com/PL-James/gxp-md/issues) first to discuss what you'd like to change.

- **Bug reports** and **feature requests** use structured issue templates
- PRs should target `main` with conventional commit messages

## License

Copyright 2026 James Gannon. Licensed under the [Apache License, Version 2.0](LICENSE).

You are free to use, modify, and distribute this work, including commercially, provided you include attribution to the original author and indicate any changes made. See the LICENSE file for full terms.

---

<p align="center">
  <sub>Created and maintained by <a href="https://policywonk.xyz">James Gannon</a> | Supported by <a href="https://pharmaledger.org">PharmaLedger Association</a></sub>
</p>
