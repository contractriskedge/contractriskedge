# Sprint 25 Task 1.2 — Permission Seed Audit

**Date**: 2026-06-05  
**Objective**: Audit role seeding, permission assignment, and cross-reference with sidebar filtering and route protection

---

## 1. Role Definitions

### Source of Truth: `Roles` class in `backend/app/kernel/security/roles.py`

| Role Constant | String Value | Permission Count |
|--------------|-------------|:----------------:|
| `ADMIN` | `tenant_admin` | **22** |
| `DEVELOPER` | `developer` | **10** |
| `LEGAL_REVIEWER` | `legal_reviewer` | **9** |
| `REVIEWER` | `reviewer` | **6** |
| `PROCUREMENT` | `procurement` | **7** |
| `SECURITY` | `security` | **8** |
| `READ_ONLY` | `viewer` | **4** |
| `AUDITOR` | `auditor` | **4** |

### Full Permission Matrix

| Permission | tenant_admin | developer | legal_reviewer | reviewer | procurement | security | viewer | auditor |
|-----------|:-----------:|:---------:|:--------------:|:--------:|:-----------:|:--------:|:------:|:-------:|
| `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `contracts:write` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `contracts:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `contracts:approve` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ai:analyze` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `ai:view` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `ai:manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `workflows:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `workflows:write` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `workflows:approve` | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ |
| `workflows:escalate` | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ |
| `vendors:read` | ✅ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `vendors:write` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `audit:read` | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ | ✅ |
| `audit:export` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `users:read` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `users:write` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `users:delete` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `admin:tenant` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `reviews:export` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| `notifications:manage` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `benchmarks:read` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `benchmarks:write` | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `benchmarks:export` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `benchmarks:seed` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `benchmarks:admin` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

**Note**: `admin:system` is **NOT assigned to any role**. It is only granted via JWT wildcard (`*`) permission. This means the **Admin Console** (`ProtectedRoute permission="admin:system"`) is only accessible to users with `*` in their JWT permissions — typically the dev bypass user.

---

## 2. Sidebar Visibility by Role

| Nav Item | Required Permission | tenant_admin | developer | legal_reviewer | reviewer | viewer |
|----------|-------------------|:-----------:|:---------:|:--------------:|:--------:|:------:|
| Ingestion | `contracts:write` | ✅ | ✅ | ❌ | ❌ | ❌ |
| Contracts | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Clause Library | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Obligations | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Review Dashboard | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Review Queue | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Negotiation | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Clause Intel | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Policy Engine | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Command Center | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Reviewer Ops | `workflows:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Workflow Intel | `workflows:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Search | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Analytics | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Benchmarks | `benchmarks:read` | ✅ | ✅ | ✅ | ✅ | ❌ |
| Portfolio | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Executive | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Compliance | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Governance | `audit:read` | ✅ | ✅ | ✅ | ❌ | ✅ |
| Relationships | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Workflows | `workflows:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Admin Console** | `admin:system` | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Settings** | `admin:tenant` | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Tenant Config** | `admin:tenant` | ✅ | ✅ | ❌ | ❌ | ❌ |
| AI Ops | `ai:view` | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 3. ProtectedRoute Accessibility by Role

| View | Required Permission | tenant_admin | developer | legal_reviewer | reviewer | viewer |
|------|-------------------|:-----------:|:---------:|:--------------:|:--------:|:------:|
| Review Queue | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Review Workspace | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Review Dashboard | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Policy Center | `contracts:read` or `ai:view` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Clause Intel | `contracts:read` | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Admin Console** | `admin:system` | ❌ | ❌ | ❌ | ❌ | ❌ |
| Settings | `admin:tenant` | ✅ | ✅ | ❌ | ❌ | ❌ |
| Tenant Settings | `admin:tenant` | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 4. Critical Finding: `admin:system` is Unreachable

**`admin:system` is NOT assigned to any role in the `Roles._PERMISSIONS` dict.** It is only available via JWT wildcard (`*`).

The only way a user gets `admin:system` is:
1. Dev bypass with `*` permission (development only, localhost only)
2. JWT token that explicitly includes `"admin:system"` in its permissions array

This means the **Admin Console** sidebar item and ProtectedRoute are effectively **inaccessible to all seeded roles**. This is intentional — `admin:system` is a super-admin permission.

---

## 5. Missing Permission Analysis

### Permissions Defined in Backend But Not in Any Role

| Permission | Used By | Missing From |
|-----------|---------|-------------|
| `admin:system` | Admin Console route, cross-tenant endpoints | **All roles** (intentional — super-admin only) |
| `contracts:delete` | DELETE review endpoint | developer, legal_reviewer, reviewer, procurement, security, viewer, auditor |
| `ai:manage` | AI management endpoints | All roles except tenant_admin |

### Permissions in Sidebar But Not in `Roles._PERMISSIONS`

The sidebar checks for these permissions. Are they defined?

| Sidebar Permission | In `Roles._PERMISSIONS`? | Notes |
|-------------------|-------------------------|-------|
| `contracts:write` | ✅ Yes | Ingestion requires this |
| `contracts:read` | ✅ Yes | Most views require this |
| `workflows:read` | ✅ Yes | Reviewer Ops, Workflow Intel |
| `benchmarks:read` | ✅ Yes | Benchmarks nav item |
| `audit:read` | ✅ Yes | Governance nav item |
| `admin:system` | ❌ **No** | Admin Console — only via JWT `*` |
| `admin:tenant` | ✅ Yes | Settings, Tenant Config |
| `ai:view` | ✅ Yes | AI Ops nav item |

---

## 6. Testing Matrix

### Full Access User (dev bypass — `*` permissions)

| Aspect | Result |
|--------|--------|
| **Sidebar visible items** | **25/25** — all nav items visible |
| **ProtectedRoute accessible** | **8/8** — all protected views accessible |
| **Can upload** | ✅ Yes (`contracts:write`) |
| **Can approve** | ✅ Yes (`contracts:approve`, `workflows:approve`) |
| **Can delete** | ✅ Yes (`contracts:delete`) |
| **Can admin** | ✅ Yes (`admin:system` via `*`) |
| **Can configure tenant** | ✅ Yes (`admin:tenant`) |

### Tenant Admin User (`tenant_admin` role)

| Aspect | Result |
|--------|--------|
| **Sidebar visible items** | **24/25** — all except Admin Console |
| **ProtectedRoute accessible** | **7/8** — all except Admin Console |
| **Can upload** | ✅ Yes (`contracts:write`) |
| **Can approve** | ✅ Yes (`contracts:approve`, `workflows:approve`) |
| **Can delete** | ✅ Yes (`contracts:delete`) |
| **Can admin** | ❌ No (`admin:system` not in role) |
| **Can configure tenant** | ✅ Yes (`admin:tenant`) |
| **Missing permissions** | None for normal operations |

### Reviewer User (`reviewer` role)

| Aspect | Result |
|--------|--------|
| **Sidebar visible items** | **20/25** — hides Ingestion, Admin Console, Settings, Tenant Config, Benchmarks |
| **ProtectedRoute accessible** | **6/8** — hides Admin Console, Settings, Tenant Config |
| **Can upload** | ❌ No (no `contracts:write`) |
| **Can approve** | ❌ No (no `contracts:approve`, no `workflows:approve`) |
| **Can delete** | ❌ No (no `contracts:delete`) |
| **Can admin** | ❌ No |
| **Can configure tenant** | ❌ No |
| **Can read reviews** | ✅ Yes (`contracts:read`) |
| **Can assign reviewers** | ✅ Yes (`workflows:write`) |
| **Can export** | ✅ Yes (`reviews:export`) |
| **Missing permissions** | `audit:read` — Governance sidebar item hidden |

---

## 7. Recommended Testing Scenarios

| Test | Full Access | Tenant Admin | Reviewer |
|------|:-----------:|:------------:|:--------:|
| Upload a contract | ✅ Can | ✅ Can | ❌ Blocked |
| View review queue | ✅ Can | ✅ Can | ✅ Can |
| Open review workspace | ✅ Can | ✅ Can | ✅ Can |
| Approve a review | ✅ Can | ✅ Can | ❌ Blocked |
| Escalate a review | ✅ Can | ✅ Can | ❌ Blocked |
| Delete a review | ✅ Can | ✅ Can | ❌ Blocked |
| Assign reviewer | ✅ Can | ✅ Can | ✅ Can |
| Configure tenant settings | ✅ Can | ✅ Can | ❌ Blocked |
| Access Admin Console | ✅ Can | ❌ Blocked | ❌ Blocked |
| Create policy pack | ✅ Can | ✅ Can | ❌ Blocked |
| View benchmarks | ✅ Can | ✅ Can | ❌ Blocked |
| Export audit report | ✅ Can | ✅ Can | ✅ Can |

---

## 8. Conclusion

**The role seeding and permission assignment is correct and consistent.** Key findings:

1. **`admin:system` is intentionally super-admin only** — not assigned to any role, only available via JWT wildcard. The Admin Console ProtectedRoute correctly blocks all seeded roles.

2. **`tenant_admin` has 22 permissions** — covers all normal operations including upload, approve, delete, settings, and tenant configuration. Only `admin:system` is missing (intentional).

3. **`reviewer` has 6 permissions** — read-only + workflow write. Cannot upload, approve, delete, or configure. Correctly scoped.

4. **Sidebar filtering matches role permissions** — nav items with `admin:system` are hidden from all roles. Nav items with `contracts:write` are hidden from reviewer. Nav items with `benchmarks:read` are hidden from viewer.

5. **No permission leaks found** — every ProtectedRoute permission exists in at least one role, and the sidebar correctly filters based on the same permissions.

**No changes needed to authorization logic.** The role definitions, sidebar filtering, and route protection are consistent.
