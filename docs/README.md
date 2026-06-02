# ContractRiskEdge — Enterprise Documentation

## Architecture
- [Enterprise Domain Model](../enterprise-domain-model.md)
- [Enterprise Service Architecture](../enterprise-service-architecture.md)
- [Enterprise Information Architecture](../enterprise-information-architecture.md)
- [Architecture Decision Records](adr/README.md)
  - ADR-001: Hybrid Vector Partition Strategy
  - ADR-002: Replay Immutability Rules
  - ADR-003: Event Versioning Strategy
  - ADR-004: Tenant Isolation Levels
  - ADR-005: Provider Routing Policy

## Operations
- [SRE Readiness & Operational Framework](operations/sre-readiness.md)
- [Operational Runbooks](../../runbooks/README.md)
  - Provider Outage Recovery
  - Replay Corruption Recovery
  - Tenant Isolation Incident
  - Audit Verification Failure
  - Vector DB Rebuild
  - Stuck Workflow Recovery
  - Deployment Rollback
  - Configuration Drift Resolution
  - Event Bus Failure
  - Queue Poison Message Cleanup

## Onboarding
- [Enterprise Onboarding Guide](onboarding/enterprise-onboarding.md)
- Tenant Bootstrap Procedure
- API Credential Generation
- Reviewer Role Setup
- Workflow Template Configuration

## Security
- [Authentication & Authorization](../production-auth-hardening.md)
- [Tenant Isolation Architecture](../production-auth-tenant-rbac.md)
- [Security Compliance Runtime](security/compliance-runtime.md)
- Audit Trail Verification
- Encryption Standards
- Legal Hold Procedures

## API
- [API Overview](api/overview.md)
- [API Versioning Policy](api/versioning.md)
- [Webhook Signatures](api/webhooks.md)
- Rate Limiting
- Error Codes

## Events
- [Event Catalog](events/catalog.md)
- Event Schema Registry
- Event Versioning
- Dead-Letter Queue Management
- Event Replay

## Deployment
- [Production Environment](../infra/environments/production/.env.production)
- [Staging Environment](../infra/environments/staging/.env.staging)
- [Kubernetes Deployment](../infra/kubernetes/)
- [Helm Chart](../infra/helm/contractriskedge/)
- [Production Schema](../infra/production-schema.sql)
