---
# GxP Technical Specification
# Specifications describe HOW the system is implemented (technical design).
# Name this file: .gxp/specs/SPEC-{US}-{NNN}-short-description.md
# Example: SPEC-001-001-audit-log-ui.md (first spec for US-001-001)

# Unique GxP identifier (format: SPEC-{US}-{NNN})
# First segment matches parent user story, second is spec number
gxp_id: SPEC-001-001

# Short, descriptive title (technical component name)
title: "Technical Component or Module Name"

# Parent user story this spec implements (REQUIRED)
parent_id: US-001-001

# Verification tier (when this specification is tested)
# IQ = Installation Qualification (deployment, config, infrastructure)
# OQ = Operational Qualification (functional testing under test conditions)
# PQ = Performance Qualification (production-like performance validation)
verification_tier: OQ

# Design approach (technical implementation strategy)
design_approach: |
  Describe HOW you will implement this specification.

  Include:
  - Technical approach (architecture, patterns, algorithms)
  - Key design decisions and rationale
  - Libraries/frameworks used
  - Database schema changes (if applicable)
  - API design (if applicable)

  Example: "Implement an AuditLogTable React component using TanStack Table
  for data grid functionality. Component fetches audit events from the
  /api/audit-log endpoint using React Query for caching. Filtering is
  handled client-side for date ranges < 30 days, server-side for larger ranges."

# Source files implementing this specification
# Update this list as you write code
source_files:
  - "src/components/AuditLogTable.tsx"
  - "src/hooks/useAuditLog.ts"
  - "src/api/auditLog.ts"

# Test files verifying this specification
# Update this list as you write tests
test_files:
  - "tests/unit/AuditLogTable.test.tsx"
  - "tests/integration/auditLogAPI.test.ts"
  - "tests/e2e/auditLog.spec.ts"

# Current validation status
# DRAFT       = Being designed, not yet coded
# IMPLEMENTED = Code written, tests passing
# REVIEWED    = Code reviewed, approved for merge
# VALIDATED   = Passed verification testing (OQ/PQ)
# DEPRECATED  = No longer in use
validation_status: DRAFT

---

# SPEC-{US}-{NNN}: {Title}

## Overview

This specification describes the implementation of [component/module name]
to satisfy user story [US-XXX-XXX] and requirement [REQ-XXX].

**Component Type**: [React Component / API Endpoint / Database Schema / Service / Utility]

**Purpose**: [One sentence describing what this component does]

## Technical Design

### Architecture

<!-- Describe how this component fits into the overall system -->

```
┌─────────────────────────────────────────────┐
│          AuditLogPage (Parent)             │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │   AuditLogFilters (Sibling)           │ │
│  │   - Date range picker                 │ │
│  │   - User dropdown                     │ │
│  │   - Action type filter                │ │
│  └───────────────────────────────────────┘ │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │   AuditLogTable (THIS COMPONENT)      │ │
│  │   - Displays audit events             │ │
│  │   - Pagination                        │ │
│  │   - Sorting                           │ │
│  └───────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
              │
              ▼ (API call)
    GET /api/audit-log?filters=...
              │
              ▼
    ┌──────────────────────┐
    │   Express API        │
    │   - auditLogRouter   │
    └──────────────────────┘
              │
              ▼ (Database query)
    ┌──────────────────────┐
    │   PostgreSQL         │
    │   audit_events table │
    └──────────────────────┘
```

### Implementation Details

#### Component Interface (for React components)

```typescript
interface AuditLogTableProps {
  filters: AuditLogFilters;
  onExport: () => void;
}

interface AuditLogFilters {
  dateRange?: { start: Date; end: Date };
  userId?: string;
  actionType?: ActionType;
}

type ActionType = 'CREATE' | 'UPDATE' | 'DELETE' | 'APPROVE' | 'REJECT';
```

#### API Specification (for backend endpoints)

**Endpoint**: `GET /api/audit-log`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| startDate | ISO 8601 | No | Filter events after this date |
| endDate | ISO 8601 | No | Filter events before this date |
| userId | UUID | No | Filter events by user |
| actionType | Enum | No | Filter by action type |
| page | Integer | No | Page number (default: 1) |
| limit | Integer | No | Events per page (default: 50, max: 200) |

**Response Format**:
```json
{
  "data": [
    {
      "id": "uuid",
      "timestamp": "2025-02-07T14:23:15.123Z",
      "userId": "uuid",
      "userName": "John Smith",
      "actionType": "APPROVE",
      "entityType": "BatchRecord",
      "entityId": "12345",
      "changes": {
        "status": { "from": "Pending", "to": "Approved" }
      }
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 342,
    "totalPages": 7
  }
}
```

**Error Responses**:
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: User lacks `view_audit_log` permission
- `400 Bad Request`: Invalid query parameters

#### Database Schema (if applicable)

```sql
-- Audit events table
CREATE TABLE audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  user_id UUID NOT NULL REFERENCES users(id),
  action_type VARCHAR(20) NOT NULL CHECK (action_type IN ('CREATE', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT')),
  entity_type VARCHAR(100) NOT NULL,
  entity_id VARCHAR(255) NOT NULL,
  old_value JSONB,
  new_value JSONB,
  ip_address INET,
  user_agent TEXT,

  -- Immutability: prevent updates and deletes
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for query performance
CREATE INDEX idx_audit_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_user ON audit_events(user_id);
CREATE INDEX idx_audit_entity ON audit_events(entity_type, entity_id);

-- Prevent modification of audit records
CREATE RULE audit_no_update AS ON UPDATE TO audit_events DO INSTEAD NOTHING;
CREATE RULE audit_no_delete AS ON DELETE TO audit_events DO INSTEAD NOTHING;
```

### Key Design Decisions

1. **Decision**: Use TanStack Table instead of custom table component
   - **Rationale**: Provides built-in sorting, filtering, pagination with excellent performance
   - **Trade-off**: Larger bundle size, but better UX and less maintenance

2. **Decision**: Client-side filtering for small datasets, server-side for large
   - **Rationale**: Reduces API calls for typical use cases (< 1000 events)
   - **Implementation**: If result set > 1000 rows, fall back to server-side filtering

3. **Decision**: Store audit events in separate table (not in main entity tables)
   - **Rationale**: Simplifies querying, enables centralized audit log viewer
   - **Trade-off**: Requires trigger or application-level logging

### Dependencies

#### External Libraries

- `@tanstack/react-table`: ^8.10.0 (data grid)
- `react-query`: ^5.0.0 (API state management)
- `date-fns`: ^3.0.0 (date formatting)

#### Internal Dependencies

- `src/api/client.ts`: HTTP client with authentication
- `src/hooks/useAuth.ts`: User authentication state
- `src/utils/permissions.ts`: Permission checking utilities

## Test Strategy

### Unit Tests

**File**: `tests/unit/AuditLogTable.test.tsx`

Test cases:
- ✓ Renders audit events in table format
- ✓ Displays "No results" message when data is empty
- ✓ Formats timestamps in user's local timezone
- ✓ Handles pagination correctly (next/prev buttons)
- ✓ Sorts columns when header is clicked

**Coverage Target**: ≥ 80% line coverage

### Integration Tests

**File**: `tests/integration/auditLogAPI.test.ts`

Test cases:
- ✓ GET /api/audit-log returns 200 with valid auth token
- ✓ GET /api/audit-log returns 401 without auth token
- ✓ GET /api/audit-log returns 403 for unauthorized user
- ✓ Filtering by date range returns only matching events
- ✓ Pagination parameters work correctly (page, limit)
- ✓ Invalid query parameters return 400 error

**Coverage Target**: All API endpoints and error conditions

### End-to-End Tests

**File**: `tests/e2e/auditLog.spec.ts`

Test scenarios:
- ✓ Quality Manager logs in → navigates to Audit Log → sees events
- ✓ Operator logs in → attempts to access Audit Log → sees "Access Denied"
- ✓ User filters by date range → table updates with filtered results
- ✓ User exports audit log → CSV file downloads successfully
- ✓ User performs batch approval → audit event appears in log

**Test Environment**: Staging environment with test data

### Performance Tests (if PQ verification tier)

- **Load Test**: Simulate 100 concurrent users viewing audit log
- **Query Performance**: Audit log query completes in < 500ms (95th percentile)
- **Export Performance**: CSV export completes in < 5 seconds for 10,000 rows

## Validation Evidence

<!-- Generated during testing, linked to evidence packages -->

### Evidence Package Reference

- **Package ID**: `OQ-SPEC-001-001-20250207T142315Z`
- **Location**: `.gxp/evidence/OQ-SPEC-001-001-20250207T142315Z/`
- **Contents**:
  - Unit test results (JUnit XML)
  - Integration test results
  - E2E test screenshots
  - Code coverage report (HTML)
  - Git commit hash and diff

### Test Execution Results

| Test Suite | Tests Run | Passed | Failed | Coverage |
|------------|-----------|--------|--------|----------|
| Unit Tests | 12 | 12 | 0 | 85% |
| Integration Tests | 8 | 8 | 0 | N/A |
| E2E Tests | 5 | 5 | 0 | N/A |

**Overall Result**: ✅ **PASS**

## Implementation Checklist

- [ ] Component/module implemented in source files
- [ ] Unit tests written and passing (≥ 80% coverage)
- [ ] Integration tests written and passing
- [ ] E2E tests written and passing
- [ ] Code reviewed and approved
- [ ] Documentation updated (JSDoc comments, README)
- [ ] Evidence package generated
- [ ] Traceability verified (links to US and REQ)

## Traceability

- **Parent User Story**: US-001-001 (View Audit Log)
- **Grandparent Requirement**: REQ-001 (Audit Trail)
- **Related Specifications**:
  - SPEC-001-002 (Audit Log API Backend)
  - SPEC-001-003 (Audit Event Database Schema)

## Change History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1.0 | YYYY-MM-DD | Your Name | Initial design |
| 0.2.0 | YYYY-MM-DD | Your Name | Added unit tests, updated source files |
| 1.0.0 | YYYY-MM-DD | QA Reviewer | Validated, approved for production |

---

**Specification Status**: DRAFT
**Reviewed By**: [Pending]
**Approved By**: [Pending]
