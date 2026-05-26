-- =============================================================================
-- Development Seed Data for AI Contract Risk Analyzer
-- =============================================================================
-- This script populates the database with sample data for local development
-- and testing. Includes a demo tenant, users, and sample contracts.
-- =============================================================================

-- ── Demo Tenant ─────────────────────────────────────────────────────────────

INSERT INTO tenants (tenant_id, name, domain, plan, max_users, max_documents, features)
VALUES (
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'Demo Corp',
    'demo.contractriskanalyzer.com',
    'enterprise',
    50,
    10000,
    ARRAY['ocr', 'redline', 'benchmarks', 'audit_trail', 'webhooks']
);

-- ── Demo Users ──────────────────────────────────────────────────────────────

INSERT INTO users (user_id, email, name, tenant_id, role, permissions)
VALUES
    ('auth0|demo_admin', 'admin@demo.contractriskanalyzer.com', 'Alice Admin',
     'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'admin',
     ARRAY['read:contracts', 'write:contracts', 'delete:contracts', 'read:risks', 'write:risks', 'read:audit']),
    ('auth0|demo_analyst', 'analyst@demo.contractriskanalyzer.com', 'Bob Analyst',
     'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'analyst',
     ARRAY['read:contracts', 'write:contracts', 'read:risks', 'write:risks']),
    ('auth0|demo_viewer', 'viewer@demo.contractriskanalyzer.com', 'Carol Viewer',
     'a1b2c3d4-e5f6-7890-abcd-ef1234567890', 'viewer',
     ARRAY['read:contracts', 'read:risks']);

-- ── Sample Contracts ────────────────────────────────────────────────────────

INSERT INTO contracts (contract_id, tenant_id, user_id, filename, content_type, file_size, status, contract_type, total_pages, total_clauses, total_chunks, tags, metadata)
VALUES
    ('c0000001-0000-0000-0000-000000000001', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'Master_Service_Agreement_2026.pdf', 'application/pdf',
     245760, 'ready', 'master_service_agreement', 12, 45, 89,
     ARRAY['msa', '2026', 'enterprise'],
     '{"vendor": "TechSolutions Inc.", "value_usd": 500000, "effective_date": "2026-01-15"}'::JSONB),

    ('c0000002-0000-0000-0000-000000000002', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'NDA_Standard.pdf', 'application/pdf',
     102400, 'ready', 'nda', 3, 8, 15,
     ARRAY['nda', 'standard'],
     '{"party": "DataPartner LLC", "effective_date": "2026-02-01"}'::JSONB),

    ('c0000003-0000-0000-0000-000000000003', 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_analyst', 'Software_License_Agreement.docx',
     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
     184320, 'processing', 'license', 8, 22, 40,
     ARRAY['license', 'software'],
     '{"vendor": "CloudSoft Inc.", "license_type": "perpetual", "effective_date": "2026-03-01"}'::JSONB);

-- ── Sample Ingestion Jobs ───────────────────────────────────────────────────

INSERT INTO ingestion_jobs (job_id, document_id, tenant_id, user_id, filename, content_type, status, progress)
VALUES
    (gen_random_uuid(),
     'c0000001-0000-0000-0000-000000000001',
     'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'Master_Service_Agreement_2026.pdf', 'application/pdf',
     'DONE', 100.0),

    (gen_random_uuid(),
     'c0000002-0000-0000-0000-000000000002',
     'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'NDA_Standard.pdf', 'application/pdf',
     'DONE', 100.0),

    (gen_random_uuid(),
     'c0000003-0000-0000-0000-000000000003',
     'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_analyst', 'Software_License_Agreement.docx',
     'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
     'PROCESSING', 45.0);

-- ── Sample Audit Logs ───────────────────────────────────────────────────────

INSERT INTO audit_logs (audit_id, tenant_id, user_id, action, resource_type, resource_id, details, created_at)
VALUES
    (gen_random_uuid(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'document.upload', 'contract',
     'c0000001-0000-0000-0000-000000000001',
     '{"filename": "Master_Service_Agreement_2026.pdf", "size": 245760}'::JSONB,
     NOW() - INTERVAL '2 days'),

    (gen_random_uuid(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'document.upload', 'contract',
     'c0000002-0000-0000-0000-000000000002',
     '{"filename": "NDA_Standard.pdf", "size": 102400}'::JSONB,
     NOW() - INTERVAL '1 day'),

    (gen_random_uuid(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_analyst', 'document.upload', 'contract',
     'c0000003-0000-0000-0000-000000000003',
     '{"filename": "Software_License_Agreement.docx", "size": 184320}'::JSONB,
     NOW() - INTERVAL '6 hours'),

    (gen_random_uuid(), 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
     'auth0|demo_admin', 'risk.analyze', 'risk_report',
     gen_random_uuid(),
     '{"contract_id": "c0000001-0000-0000-0000-000000000001", "categories": ["indemnification", "liability_limitation"]}'::JSONB,
     NOW() - INTERVAL '12 hours');

-- ── Sample Contract Relationships (Sprint 10) ───────────────────────────────

INSERT INTO contract_relationships (relationship_id, parent_contract_id, child_contract_id, relationship_type, effective_date, notes)
VALUES
    (gen_random_uuid(),
     'c0000001-0000-0000-0000-000000000001',
     'c0000002-0000-0000-0000-000000000002',
     'child',
     '2026-02-01',
     'NDA executed under MSA umbrella'),

    (gen_random_uuid(),
     'c0000001-0000-0000-0000-000000000001',
     'c0000003-0000-0000-0000-000000000003',
     'child',
     '2026-03-01',
     'Software license agreement under MSA');
