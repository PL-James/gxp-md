---
# GxP Requirement Definition
# Requirements describe WHAT the system must do (regulatory/business needs).
# Name this file: .gxp/requirements/REQ-{NNN}-short-description.md
# Example: REQ-001-audit-trail.md, REQ-002-user-authentication.md

# Unique GxP identifier (format: REQ-NNN, zero-padded, opaque)
gxp_id: REQ-001

# Short, descriptive title
title: "Descriptive Requirement Title"

# List of requirements this requirement satisfies (parent/derived-from relationships)
# Leave empty [] for top-level requirements, or reference other REQ-NNN IDs
satisfies: []

# Detailed requirement description
description: |
  Clear, unambiguous statement of what the system MUST do.

  Use "The system shall..." language for regulatory requirements.

  Example: "The system shall maintain a tamper-proof audit trail of all
  GxP-critical actions, recording user ID, timestamp, action type, and
  affected data in accordance with 21 CFR Part 11.10(e)."

# Risk classification for this requirement
# HIGH   = Patient safety, regulatory compliance, data integrity
# MEDIUM = Quality system impact, indirect patient safety
# LOW    = Usability, performance (non-critical)
risk_level: HIGH

# Acceptance criteria (testable conditions for "done")
# Each criterion should be independently verifiable
acceptance_criteria:
  - "System records audit events with all required fields (user, timestamp, action, data)"
  - "Audit records are write-only (cannot be modified or deleted)"
  - "Audit log is accessible to authorized quality personnel"
  - "Audit trail includes both successful and failed actions"

# Current validation status
# DRAFT      = Being defined, not yet approved
# APPROVED   = Reviewed and approved by QA/business owner
# IMPLEMENTED = Coded and tested (linked to US/SPEC)
# VALIDATED  = Passed OQ/PQ testing
# DEPRECATED = No longer applicable (replaced or removed)
validation_status: DRAFT

---

# REQ-{NNN}: {Title}

## Business Context

<!-- Explain WHY this requirement exists -->

This requirement addresses [business need / regulatory obligation / user need].

**Regulatory Driver**: [21 CFR Part 11.10(e) / EU Annex 11 / GAMP 5 / etc.]

**Business Value**: [What business problem does this solve?]

## Functional Description

<!-- Describe WHAT the system must do in detail -->

The system shall provide the following capabilities:

1. **[Capability 1]**: Detailed description of what happens
2. **[Capability 2]**: Step-by-step behavior
3. **[Capability 3]**: Expected outcomes

### User Roles Affected

- **[Role Name]**: [What they can do related to this requirement]
- **[Role Name]**: [Their interaction with this feature]

## Regulatory Compliance

This requirement satisfies the following regulatory obligations:

- **21 CFR Part 11.10(e)**: Use of secure, computer-generated, time-stamped audit trails
- **EU Annex 11, Section 9**: Audit trails to record GxP-relevant changes
- **[Other standards]**: [Specific clauses]

## Data Requirements

### Data Captured

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| User ID | String | Yes | Authenticated user identifier |
| Timestamp | ISO 8601 | Yes | When the action occurred (UTC) |
| Action Type | Enum | Yes | CREATE, UPDATE, DELETE, APPROVE, etc. |
| Entity Type | String | Yes | What was changed (e.g., "Batch Record") |
| Entity ID | UUID | Yes | Unique identifier of affected record |
| Old Value | JSON | No | Previous state (for UPDATE actions) |
| New Value | JSON | No | New state (for CREATE/UPDATE) |

### Data Retention

- **Retention Period**: [7 years / 10 years / as per company policy]
- **Archive Strategy**: [How old data is archived]
- **Deletion Policy**: [When/how data can be deleted, if ever]

## Security & Access Control

### Access Requirements

| Role | Read | Create | Update | Delete |
|------|------|--------|--------|--------|
| Quality Manager | ✓ | - | - | - |
| System Admin | ✓ | - | - | - |
| Auditor | ✓ | - | - | - |

*Note: Audit records are write-only by the system; no user can modify them.*

### Security Controls

- **Authentication**: Required before any access
- **Authorization**: Role-based access control (RBAC)
- **Encryption**: [At-rest / In-transit requirements]
- **Audit**: All access attempts logged

## Performance Requirements

- **Response Time**: [< 500ms for queries]
- **Throughput**: [Support X concurrent users]
- **Storage**: [Estimate growth: Y GB per month]
- **Availability**: [99.9% uptime required?]

## Dependencies

### Technical Dependencies

- User authentication system (REQ-XXX)
- Database infrastructure (PostgreSQL)
- [Other system components]

### Business Process Dependencies

- [Upstream process that triggers this requirement]
- [Downstream processes that consume outputs]

## Traceability

### Parent/Derived Requirements

- REQ-XXX: [Parent requirement if this is a sub-requirement]
- REQ-XXX: [Related requirement in requirement hierarchy]

### Related User Stories

*User stories will reference this requirement via edge tags: @gxp-satisfies REQ-001*

- US-001: [User story title]
- US-002: [User story title]

### Related Specifications

*Specifications may directly implement this requirement via edge tags: @gxp-satisfies REQ-001*

- SPEC-001: [Spec title]
- SPEC-002: [Spec title]

## Acceptance Criteria (Testable)

Each criterion must be independently verifiable through testing:

1. ✓ **Audit Event Creation**: When a GxP-critical action occurs, an audit record is created with all required fields populated
2. ✓ **Immutability**: Audit records cannot be edited or deleted (database constraints enforce write-only)
3. ✓ **Access Control**: Only authorized roles can query audit logs
4. ✓ **Completeness**: Both successful and failed actions are logged
5. ✓ **Timestamp Accuracy**: Timestamps are recorded in UTC with millisecond precision

## Validation Approach

### Verification Method

- **IQ**: Verify audit table schema and database constraints
- **OQ**: Test audit event creation for all GxP-critical actions
- **PQ**: Verify audit trail in production-like conditions with realistic load

### Test Scenarios

1. **Positive Test**: Perform GxP action → Verify audit record created
2. **Negative Test**: Attempt to modify audit record → Verify failure
3. **Access Control Test**: Non-authorized user queries audit → Verify denial
4. **Load Test**: Simulate 1000 concurrent actions → Verify all audited

## Open Questions / Risks

<!-- Track unresolved issues during requirement definition -->

- [ ] **Question**: What happens if audit log storage is full?
  - **Status**: Under review with Ops team

- [ ] **Risk**: Audit log queries may slow down with large datasets
  - **Mitigation**: Implement database indexing and archival strategy

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | YYYY-MM-DD | Your Name | Initial draft |
| 0.2.0 | YYYY-MM-DD | QA Reviewer | Added acceptance criteria |

---

**Requirement Status**: DRAFT
**Approver**: [QA Lead Name]
**Approval Date**: [Pending]
