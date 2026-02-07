---
# GxP User Story
# User stories describe HOW users interact with the system to satisfy a requirement.
# Name this file: .gxp/user_stories/US-{REQ}-{NNN}-short-description.md
# Example: US-001-001-view-audit-log.md (first story for REQ-001)

# Unique GxP identifier (format: US-{REQ}-{NNN})
# First segment matches parent requirement, second is story number
gxp_id: US-001-001

# Short, descriptive title (user-facing language)
title: "User Story Title (As a [role], I want to [action])"

# Parent requirement this story implements (REQUIRED)
parent_id: REQ-001

# Acceptance criteria (testable conditions)
# Each criterion should be independently verifiable
acceptance_criteria:
  - "When [trigger], then [expected outcome]"
  - "Given [precondition], when [action], then [result]"
  - "System displays [expected UI element] with [expected data]"

# Verification tier (when this story is tested)
# IQ = Installation Qualification (infrastructure setup)
# OQ = Operational Qualification (functional testing)
# PQ = Performance Qualification (real-world performance)
verification_tier: OQ

# Current validation status
# DRAFT       = Being defined
# READY       = Approved, ready for implementation
# IN_PROGRESS = Being coded/tested
# VALIDATED   = Passed verification testing
# DEPRECATED  = No longer applicable
validation_status: DRAFT

---

# US-{REQ}-{NNN}: {Title}

## User Story

**As a** [user role],
**I want to** [perform some action],
**So that** [I achieve some goal/benefit].

**Example:**

> **As a** Quality Manager,
> **I want to** view a chronological audit log of all batch record approvals,
> **So that** I can verify compliance with manufacturing procedures during regulatory inspections.

## Context

<!-- Explain when and why this story is needed -->

This user story supports [parent requirement] by enabling [user role] to [accomplish task].

**Scenario**: [Describe a real-world situation where this story applies]

## Detailed Requirements

### User Flow

1. **Precondition**: User is authenticated and has [required role/permission]
2. **User Action**: User navigates to [screen/page] and clicks [button/link]
3. **System Behavior**: System displays [expected output]
4. **Postcondition**: User can now [perform next action]

### UI/UX Requirements

- **Screen/Page**: [Audit Log Viewer]
- **Navigation**: Accessible from [Main Menu > Compliance > Audit Logs]
- **Controls**:
  - Filter by date range (start date, end date)
  - Filter by user (dropdown, searchable)
  - Filter by action type (CREATE, UPDATE, DELETE, APPROVE)
  - Export button (downloads CSV)

### Data Display

| Field | Display Format | Example |
|-------|---------------|---------|
| Timestamp | YYYY-MM-DD HH:MM:SS UTC | 2025-02-07 14:23:15 UTC |
| User | Full Name (Username) | John Smith (jsmith) |
| Action | Human-readable verb | Approved Batch Record |
| Entity | Type + ID | Batch Record #12345 |
| Changes | Summary or "View Details" link | Status: Pending → Approved |

## Acceptance Criteria (Testable)

Use **Given-When-Then** format for clarity:

1. **AC1: Access Control**
   - **Given** I am logged in as a Quality Manager
   - **When** I navigate to the Audit Log page
   - **Then** I see a list of audit events

2. **AC2: Filtering by Date**
   - **Given** I am on the Audit Log page
   - **When** I set a date range filter (2025-02-01 to 2025-02-07)
   - **Then** only audit events within that date range are displayed

3. **AC3: Unauthorized Access Prevention**
   - **Given** I am logged in as an Operator (non-privileged role)
   - **When** I attempt to access the Audit Log page
   - **Then** I see an "Access Denied" error message

4. **AC4: Data Accuracy**
   - **Given** an audit event was created for a batch approval
   - **When** I view the audit log
   - **Then** the event displays the correct user, timestamp, and action details

5. **AC5: Export Functionality**
   - **Given** I have filtered the audit log
   - **When** I click the "Export CSV" button
   - **Then** a CSV file downloads with all displayed audit events

## Technical Specifications

### API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/audit-log` | GET | Retrieve audit events (with filters) |
| `/api/audit-log/export` | POST | Generate CSV export |

### Database Queries

- Query audit_events table with optional filters (user_id, date_range, action_type)
- Order by timestamp DESC (most recent first)
- Pagination: 50 events per page

### Security

- **Authentication**: Required (JWT token in Authorization header)
- **Authorization**: User must have `view_audit_log` permission
- **Rate Limiting**: Max 100 requests per minute per user

## Dependencies

### Technical Dependencies

- Authentication system (user must be logged in)
- Audit event logging system (REQ-001) must be functional
- User role/permission system

### User Story Dependencies

- **Depends On**: US-XXX-XXX (User authentication story)
- **Blocks**: US-001-002 (Advanced audit search story)

## Verification Plan

### Test Cases

| Test ID | Description | Expected Result | Tier |
|---------|-------------|----------------|------|
| TC-US-001-001 | Quality Manager views audit log | Audit events displayed | OQ |
| TC-US-001-002 | Operator attempts to view audit log | Access denied | OQ |
| TC-US-001-003 | Filter by date range | Only matching events shown | OQ |
| TC-US-001-004 | Export audit log as CSV | CSV file downloads | OQ |

### Evidence Required

- Screenshots of successful audit log access
- Test execution logs showing access control (deny for Operator)
- Sample CSV export file
- Performance metrics (page load time < 2 seconds)

## Implementation Notes for AI Agents

### Source Files

*Update this list as you implement the story*

- `src/pages/AuditLogPage.tsx` — Main UI component
- `src/api/auditLog.ts` — API client functions
- `src/components/AuditLogTable.tsx` — Data table component
- `src/components/AuditLogFilters.tsx` — Filter controls

### Test Files

- `tests/unit/auditLog.test.ts` — Unit tests for API functions
- `tests/integration/auditLogAPI.test.ts` — API endpoint tests
- `tests/e2e/auditLog.spec.ts` — End-to-end UI tests

### Traceability

- **Parent Requirement**: REQ-001 (Audit Trail)
- **Child Specifications**:
  - SPEC-001-001 (Audit Log UI Component)
  - SPEC-001-002 (Audit Log API)

## Open Questions

<!-- Track unresolved issues during story refinement -->

- [ ] **Question**: Should we support exporting to PDF in addition to CSV?
  - **Status**: Awaiting QA input

- [ ] **Question**: What is the maximum date range for queries (performance concern)?
  - **Status**: Testing with 1 year range

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | YYYY-MM-DD | Your Name | Initial draft |

---

**Story Status**: DRAFT
**Story Points**: [Optional: Fibonacci estimate for effort]
**Sprint**: [Optional: Sprint number if using Agile]
