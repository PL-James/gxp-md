---
# System Context Document
# This file provides architectural overview and system boundaries.
# Name this file: .gxp/system_context.md

# Unique identifier for this system (generate once, never change)
id: "00000000-0000-0000-0000-000000000000"  # Replace with actual UUID

# Project metadata
project_name: "Your Project Name"
version: "0.1.0"

# GxP Risk Classification
# HIGH    = Direct patient safety impact, regulatory submissions, GMP records
# MEDIUM  = Quality system impact, indirect patient safety
# LOW     = Supporting tools, non-GxP infrastructure
gxp_risk_rating: HIGH

# Validation lifecycle state
# DRAFT       = Under development, not validated
# VALIDATED   = Passed IQ/OQ/PQ, approved for production use
# DEPRECATED  = No longer supported, migration required
validation_status: DRAFT

# Intended use statement (defines scope for validation)
intended_use: |
  Describe the PURPOSE of this system and WHO uses it.

  Example: "Web-based application for quality assurance personnel to
  review and approve manufacturing batch records in compliance with
  21 CFR Part 11 and EU Annex 11."

  Be specific about:
  - What the system does
  - Who the users are (roles)
  - What regulatory requirements it satisfies

# Regulatory context
regulatory_context:
  # Applicable regulatory standards
  primary_standards:
    - "21 CFR Part 11"  # FDA Electronic Records and Signatures
    - "EU Annex 11"     # Computerized Systems (EU GMP)
    # Add others: GAMP 5, ISO 13485, GDP, etc.

  # GAMP Software Category (determines validation approach)
  # 1 = Infrastructure software (OS, databases)
  # 3 = Non-configured products (COTS, no customization)
  # 4 = Configured products (COTS with configuration)
  # 5 = Custom applications (bespoke/custom code) ← Typical for AI-generated systems
  gamp_category: 5

  # Data classification level
  # GxP-Critical  = Contains/processes GxP records
  # GxP-Supporting = Supports GxP processes but doesn't store GxP data
  # Non-GxP        = No regulatory impact
  data_classification: "GxP-Critical"

# System boundary definition (critical for scope control)
system_boundary:
  # Components INSIDE the validated system boundary
  includes:
    - "Frontend web application (React)"
    - "Backend REST API (Node.js/Express)"
    - "PostgreSQL database and schema"
    - "Authentication and authorization logic"
    - "Business logic and workflows"
    # List all components requiring validation

  # Components OUTSIDE the validated system boundary
  excludes:
    - "Development tools (TypeScript compiler, Webpack)"
    - "CI/CD pipeline infrastructure"
    - "Cloud hosting platform (Railway, AWS, etc.)"
    - "Third-party npm packages"
    - "Operating system and runtime (Node.js)"
    # Clearly state what is NOT being validated

---

# System Context: {Project Name}

## System Purpose

<!-- Describe the business problem this system solves -->

This system provides [describe high-level capability] for [target users]
in order to [business outcome]. It supports compliance with [regulatory requirements].

## Architecture Overview

### Technology Stack

- **Frontend**: React 18, TypeScript, TailwindCSS
- **Backend**: Node.js, Express, TypeScript
- **Database**: PostgreSQL 15
- **Hosting**: [Railway / AWS / On-premise]
- **Authentication**: [JWT / OAuth / SAML]

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     SYSTEM BOUNDARY                         │
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   Frontend   │────────▶│   Backend    │                 │
│  │  (React SPA) │         │  (Express)   │                 │
│  └──────────────┘         └──────┬───────┘                 │
│                                   │                         │
│                                   ▼                         │
│                          ┌──────────────┐                  │
│                          │  PostgreSQL  │                  │
│                          │   Database   │                  │
│                          └──────────────┘                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
         │                          │
         ▼                          ▼
   [External IdP]            [External APIs]
   (if applicable)           (if applicable)
```

### Key Features

1. **User Management**: Role-based access control (RBAC)
2. **Data Entry**: Forms for [describe what data is entered]
3. **Workflows**: [Approval workflows, state machines, etc.]
4. **Reporting**: [What reports/exports are available]
5. **Audit Trail**: Tamper-proof audit logging (21 CFR Part 11)

## GxP-Critical Components

The following components handle GxP-critical data and require full validation:

| Component | Risk Level | Validation Tier | Rationale |
|-----------|-----------|-----------------|-----------|
| Authentication module | HIGH | OQ | Controls access to GxP records |
| Audit trail system | HIGH | OQ + PQ | Required for 21 CFR Part 11 compliance |
| [Feature name] | HIGH/MEDIUM/LOW | IQ/OQ/PQ | [Why this is critical] |

## Data Flow

### Primary Data Flows

1. **User Authentication**
   - User submits credentials → Backend validates → JWT issued → Session established

2. **[Business Process Name]**
   - [Describe step-by-step data flow through the system]

3. **Audit Logging**
   - All GxP-critical actions → Audit event generated → Stored in audit table

## Security & Access Control

### User Roles

| Role | Permissions | GxP Impact |
|------|-------------|------------|
| Admin | Full system access, user management | HIGH |
| Quality Manager | Review/approve records | HIGH |
| Operator | Data entry, view own records | MEDIUM |
| Auditor | Read-only access to audit logs | LOW |

### Authentication & Authorization

- **Authentication Method**: [JWT / OAuth 2.0 / SAML]
- **Password Policy**: [Min length, complexity, expiration]
- **Session Management**: [Timeout, concurrent sessions]
- **MFA Required**: [Yes/No, for which roles]

## Integration Points

### External Systems

| System | Integration Type | Data Exchanged | GxP Impact |
|--------|-----------------|----------------|------------|
| [ERP System] | REST API | [Product master data] | MEDIUM |
| [LIMS] | File export | [Test results] | HIGH |

### APIs and Interfaces

- **Public API**: [Yes/No] — [Authentication method]
- **Webhooks**: [Yes/No] — [Events published]
- **File Imports**: [Supported formats]

## Infrastructure

### Deployment Architecture

- **Environment**: [Cloud / On-premise / Hybrid]
- **Hosting**: [Railway / AWS / Azure]
- **Database**: PostgreSQL 15 (managed service)
- **Backup Strategy**: [Daily snapshots, 30-day retention]
- **Disaster Recovery**: [RTO/RPO targets]

### Scalability

- **Expected Load**: [X users, Y transactions/day]
- **Performance Targets**: [Page load < 2s, API response < 500ms]

## Validation Approach

### Verification Tiers

- **IQ (Installation Qualification)**: Verify deployment, configuration, infrastructure
- **OQ (Operational Qualification)**: Verify functional requirements under test conditions
- **PQ (Performance Qualification)**: Verify system performs in production-like conditions

### Test Coverage Requirements

- **Unit Tests**: 80% code coverage minimum
- **Integration Tests**: All API endpoints, database operations
- **E2E Tests**: Critical user workflows (login, data entry, approvals)
- **Performance Tests**: Load testing for expected user volume

## Change Control

### Change Categories

| Change Type | Approval Required | Re-validation Required |
|-------------|------------------|------------------------|
| Bug fix (non-GxP code) | Tech Lead | No |
| Bug fix (GxP-critical code) | QA + Tech Lead | Regression testing |
| New feature (GxP impact) | QA + Business Owner | Full OQ/PQ |
| Infrastructure change | Ops + QA | IQ verification |

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | YYYY-MM-DD | Your Name | Initial draft |

---

**Document Status**: DRAFT
**Next Review Date**: [Set review schedule]
**Approvals Required**: Quality Assurance, Technical Lead
