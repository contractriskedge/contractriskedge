# ContractRiskEdge — SRE Readiness & Operational Framework
# =============================================================================
# Service Level Objectives, Indicators, Error Budgets, and Escalation Paths.
# =============================================================================

# ══════════════════════════════════════════════════════════════════════════════
# 1. SERVICE LEVEL INDICATORS (SLIs)
# ══════════════════════════════════════════════════════════════════════════════

## AI Execution SLIs
# - AI execution success rate: % of AI executions that complete without error
# - AI execution latency (p50/p95/p99): Time from request to response
# - AI provider availability: % of provider calls that succeed
# - Replay consistency score: % of replays with drift < 0.15
# - Guardrail pass rate: % of executions passing all guardrails

## API SLIs
# - API request success rate: % of HTTP 2xx responses
# - API latency (p50/p95/p99): Time from request to response
# - API error rate: % of HTTP 5xx responses
# - API rate limit utilization: % of allowed rate used

## Workflow SLIs
# - Workflow completion rate: % of workflows that complete successfully
# - Workflow SLA compliance: % of workflows completed within SLA
# - Review assignment SLA compliance: % of reviews assigned within SLA window

## Data SLIs
# - Vector search latency (p50/p95/p99): Time for ANN query
# - Embedding generation success rate: % of chunks successfully embedded
# - Audit chain integrity: % of audit chains without violations

## Queue SLIs
# - Queue processing rate: Jobs processed per minute
# - Queue backlog: Number of pending jobs
# - Dead-letter rate: % of jobs moved to DLQ

# ══════════════════════════════════════════════════════════════════════════════
# 2. SERVICE LEVEL OBJECTIVES (SLOs)
# ══════════════════════════════════════════════════════════════════════════════

## Critical SLOs (99.9% — Enterprise Pilot)
# - AI execution success rate: >= 99.9%
# - API request success rate: >= 99.9%
# - Audit chain integrity: 100% (no violations)
# - Tenant isolation: 100% (no cross-tenant data leaks)

## High SLOs (99.5% — Professional)
# - AI execution latency p95: <= 15s
# - API latency p95: <= 2s
# - Workflow completion rate: >= 99.5%
# - Replay consistency score: >= 0.95

## Standard SLOs (99.0% — Standard)
# - Vector search latency p95: <= 500ms
# - Embedding success rate: >= 99.0%
# - Queue processing rate: >= 100 jobs/min
# - Guardrail pass rate: >= 95%

# ══════════════════════════════════════════════════════════════════════════════
# 3. ERROR BUDGETS
# ══════════════════════════════════════════════════════════════════════════════

## Monthly Error Budget Calculation
# Error Budget = (1 - SLO) * total_requests_per_month
#
# Example (99.9% SLO, 100k requests/month):
# Error Budget = (1 - 0.999) * 100000 = 100 errors/month
#
# When error budget is exhausted:
# - Freeze all non-critical deployments
# - Focus exclusively on reliability improvements
# - Require CTO approval for any production changes

## Error Budget Policy
# - 100-50% remaining: Normal operations, any deployment allowed
# - 50-20% remaining: Deployments require peer review + canary
# - 20-0% remaining: Only critical bug fixes, all changes require approval
# - 0% (exhausted): Deployment freeze, incident review required

# ══════════════════════════════════════════════════════════════════════════════
# 4. OPERATIONAL SEVERITY MATRIX
# ══════════════════════════════════════════════════════════════════════════════

## P1 — Critical (Response: 15min, Resolution: 2h)
# Definition: Complete platform outage or data breach
# Examples:
#   - Cross-tenant data leak detected
#   - Complete AI execution failure (>95% error rate)
#   - Audit chain integrity violation
#   - Data loss or corruption
#   - Security breach
# Response: Immediate incident response, page on-call engineer
# Escalation: Engineering lead → CTO

## P2 — High (Response: 30min, Resolution: 4h)
# Definition: Major feature degradation, no workaround
# Examples:
#   - AI provider circuit breaker open (all executions failing)
#   - Replay consistency score drops below 0.80
#   - Queue backlog > 10,000 jobs
#   - Workflow SLA breach rate > 10%
#   - Vector search latency p95 > 5s
# Response: Page on-call engineer, notify team lead
# Escalation: On-call engineer → Engineering lead

## P3 — Medium (Response: 2h, Resolution: 24h)
# Definition: Partial degradation, workaround available
# Examples:
#   - Single provider degraded (fallback working)
#   - Replay drift detected (score 0.80-0.95)
#   - Config drift detected
#   - Stale embedding percentage > 20%
#   - Queue backlog 1,000-10,000 jobs
# Response: Create ticket, investigate during business hours
# Escalation: Team lead → Engineering manager

## P4 — Low (Response: 24h, Resolution: Next sprint)
# Definition: Minor issues, no user impact
# Examples:
#   - Single tenant quota approaching limit
#   - Orphan config keys detected
#   - Minor dashboard metric discrepancy
#   - Documentation outdated
# Response: Log ticket, address in next sprint
# Escalation: Normal sprint planning

# ══════════════════════════════════════════════════════════════════════════════
# 5. ESCALATION PATHS
# ══════════════════════════════════════════════════════════════════════════════

## On-Call Rotation
# - Primary: 1 engineer (24h shift, Mon-Sun)
# - Secondary: 1 engineer (backup, same shift)
# - Tertiary: Engineering lead (escalation only)

## Escalation Chain
# Level 1: Primary on-call engineer
#   - Acknowledges within 15min (P1) or 30min (P2)
#   - Diagnoses and resolves or escalates
#
# Level 2: Secondary on-call engineer
#   - Engaged if primary does not acknowledge
#   - Assists with diagnosis and resolution
#
# Level 3: Engineering lead
#   - Engaged for P1 incidents or unresolved P2 after 1h
#   - Coordinates cross-team response
#
# Level 4: CTO
#   - Engaged for P1 incidents > 2h
#   - Makes go/no-go decisions for emergency changes

## Communication Channels
# - P1: Slack + PagerDuty + Phone call
# - P2: Slack + PagerDuty
# - P3: Slack notification
# - P4: Jira ticket

# ══════════════════════════════════════════════════════════════════════════════
# 6. OPERATIONAL RUNBOOKS INDEX
# ══════════════════════════════════════════════════════════════════════════════

# See runbooks/README.md for detailed recovery procedures:
#
# 1. Provider Outage Recovery
# 2. Replay Corruption Recovery
# 3. Tenant Isolation Incident
# 4. Audit Verification Failure
# 5. Vector DB Rebuild
# 6. Stuck Workflow Recovery
# 7. Deployment Rollback
# 8. Configuration Drift Resolution
# 9. Event Bus Failure
# 10. Queue Poison Message Cleanup

# ══════════════════════════════════════════════════════════════════════════════
# 7. ON-CALL CHECKLIST
# ══════════════════════════════════════════════════════════════════════════════

## Start of Shift
# [ ] Verify all dashboards are accessible
# [ ] Check active alerts and acknowledge any firing
# [ ] Review recent deployments
# [ ] Check queue depths across all queues
# [ ] Verify provider health
# [ ] Confirm DR validation suite passed

## During Shift
# [ ] Respond to alerts within SLO
# [ ] Document all incidents in incident log
# [ ] Update runbooks with any new findings
# [ ] Communicate status to stakeholders for P1/P2

## End of Shift
# [ ] Transfer active incidents to incoming on-call
# [ ] Update incident status
# [ ] Document any ongoing investigations
# [ ] Verify all critical alerts are acknowledged
