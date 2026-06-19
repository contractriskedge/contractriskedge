"""Create 4 test users for Permission Matrix testing and generate JWT tokens."""
import asyncio, json, hmac, hashlib, time
from base64 import urlsafe_b64encode
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import select, text

DATABASE_URL = "postgresql+asyncpg://dev_user:dev_password@localhost:5432/contract_risk_dev"
DEV_JWT_SECRET = "dev-local-jwt-secret-do-not-use-in-production"
DEV_TENANT_ID = "00000000-0000-4000-8000-000000000001"

TEST_USERS = [
    {"user_id": "test-admin-1",    "email": "admin@test.cre",     "name": "Test Admin",    "role": "admin"},
    {"user_id": "test-reviewer-1", "email": "reviewer@test.cre",  "name": "Test Reviewer", "role": "reviewer"},
    {"user_id": "test-legal-1",    "email": "legal@test.cre",     "name": "Test Legal",    "role": "legal_ops"},
    {"user_id": "test-viewer-1",   "email": "viewer@test.cre",    "name": "Test Viewer",   "role": "viewer"},
]

JWT_ROLE_MAP = {
    "admin":       "tenant_admin",
    "reviewer":    "reviewer",
    "legal_ops":   "legal_reviewer",
    "viewer":      "viewer",
}

ROLE_PERMISSIONS = {
    "tenant_admin":   ["*"],
    "reviewer":       ["contracts:read", "ai:view", "workflows:read", "workflows:write", "reviews:export", "benchmarks:read"],
    "legal_reviewer": ["contracts:read", "contracts:approve", "ai:view", "workflows:read", "workflows:write", "workflows:approve", "workflows:escalate", "audit:read", "reviews:export", "benchmarks:read"],
    "viewer":         ["contracts:read", "ai:view", "workflows:read", "audit:read"],
}

def generate_jwt(sub, email, role, permissions, tenant_id):
    now = int(time.time())
    payload = {
        "sub": sub,
        "email": email,
        "tenant_id": tenant_id,
        "role": role,
        "permissions": permissions,
        "iat": now,
        "exp": now + 3600,
    }
    header = {"alg": "HS256", "typ": "JWT"}
    def b64(data):
        return urlsafe_b64encode(data).rstrip(b"=").decode()
    h = b64(json.dumps(header).encode())
    p = b64(json.dumps(payload).encode())
    sig = b64(hmac.new(DEV_JWT_SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{sig}"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with AsyncSession(engine) as session:
        print("=" * 70)
        print("CREATING TEST USERS")
        print("=" * 70)
        
        for u in TEST_USERS:
            # Check if user exists
            result = await session.execute(
                text("SELECT user_id FROM admin_users WHERE user_id = :uid"),
                {"uid": u["user_id"]}
            )
            existing = result.fetchone()
            if existing:
                print(f"  [{u['role']:10s}] {u['user_id']} already exists, skipping.")
                continue

            await session.execute(
                text("""
                    INSERT INTO admin_users (user_id, tenant_id, email, name, role, is_active)
                    VALUES (:uid, :tid, :email, :name, :role, TRUE)
                """),
                {
                    "uid": u["user_id"],
                    "tid": DEV_TENANT_ID,
                    "email": u["email"],
                    "name": u["name"],
                    "role": u["role"],
                }
            )
            await session.flush()
            print(f"  [{u['role']:10s}] Created: {u['user_id']} ({u['email']})")

        # ── Enable email redirect to dev inbox ────────────────────
        # All notification emails will be sent to contractriskedge@gmail.com
        # instead of individual user emails. This is controlled by the
        # email_redirect_enabled and email_redirect_to columns in tenant_settings.
        result = await session.execute(
            text("SELECT settings_id FROM tenant_settings WHERE tenant_id = :tid"),
            {"tid": DEV_TENANT_ID},
        )
        existing_settings = result.fetchone()
        if existing_settings:
            await session.execute(
                text("""
                    UPDATE tenant_settings
                    SET email_redirect_enabled = TRUE,
                        email_redirect_to = 'contractriskedge@gmail.com',
                        updated_at = NOW()
                    WHERE tenant_id = :tid
                """),
                {"tid": DEV_TENANT_ID},
            )
            print(f"  {'─' * 50}")
            print(f"  Email redirect ENABLED → contractriskedge@gmail.com")
        else:
            print(f"  {'─' * 50}")
            print(f"  NOTE: tenant_settings not found for tenant {DEV_TENANT_ID}")
            print(f"  Email redirect NOT configured — run migrations first.")

        await session.commit()
        
        # Print tokens
        print("\n" + "=" * 70)
        print("JWT TOKENS FOR PERMISSION TESTING")
        print("=" * 70)
        print("\nCopy these Authorization headers for API testing.\n")
        
        tokens = {}
        for u in TEST_USERS:
            jwt_role = JWT_ROLE_MAP[u["role"]]
            perms = ROLE_PERMISSIONS[jwt_role]
            token = generate_jwt(u["user_id"], u["email"], jwt_role, perms, DEV_TENANT_ID)
            tokens[u["role"]] = token
            print(f"{'─' * 70}")
            print(f"  ROLE:     {u['role'].upper():15s}  (JWT: {jwt_role})")
            print(f"  USER:     {u['name']:30s}  <{u['email']}>")
            print(f"  USER ID:  {u['user_id']}")
            print(f"  TOKEN:    {token[:80]}...")
            print(f"  curl -H 'Authorization: Bearer {token[:80]}...'")
            print()
        
        # Also generate a token for the existing dev-user (admin)
        dev_token = generate_jwt("dev-user", "dev@localhost", "tenant_admin", ["*"], DEV_TENANT_ID)
        tokens["dev-admin"] = dev_token
        print(f"{'─' * 70}")
        print(f"  ROLE:     DEV-ADMIN (existing dev-user)")
        print(f"  TOKEN:    {dev_token[:80]}...")
        
        # ── Permission Validation Tests ────────────────────────────
        print("\n" + "=" * 70)
        print("PERMISSION VALIDATION — Expected Results")
        print("=" * 70)
        
        tests = [
            # (role, endpoint, method, expected_status, description)
            ("admin",    "GET",    "/api/v1/reviews?page_size=1",               200, "List reviews"),
            ("admin",    "POST",   "/api/v1/playbooks/",                        422, "Create playbook (422=body validation, auth passed)"),
            ("admin",    "POST",   "/api/v1/playbooks/4152923b-ac84-4a91-b63f-871b10277ac4/publish", 200, "Publish playbook"),
            
            ("reviewer", "GET",    "/api/v1/reviews?page_size=1",               200, "List reviews"),
            ("reviewer", "POST",   "/api/v1/playbooks/",                        403, "Create playbook (blocked)"),
            ("reviewer", "POST",   "/api/v1/playbooks/4152923b-ac84-4a91-b63f-871b10277ac4/publish", 403, "Publish playbook (blocked)"),
            ("reviewer", "POST",   "/api/v1/reviews/some-id/findings/finding-id/resolve", 404, "Resolve finding (404=not found, auth passed)"),
            
            ("legal",    "GET",    "/api/v1/reviews?page_size=1",               200, "List reviews"),
            ("legal",    "POST",   "/api/v1/playbooks/",                        403, "Create playbook (blocked)"),
            ("legal",    "POST",   "/api/v1/reviews/some-id/approve",           404, "Approve review (404=not found, auth passed)"),
            ("legal",    "GET",    "/api/v1/playbooks/audit?page_size=5",       200, "View audit"),
            
            ("viewer",   "GET",    "/api/v1/reviews?page_size=1",               200, "List reviews"),
            ("viewer",   "POST",   "/api/v1/playbooks/",                        403, "Create playbook (blocked)"),
            ("viewer",   "POST",   "/api/v1/reviews/some-id/approve",           403, "Approve review (blocked)"),
            ("viewer",   "POST",   "/api/v1/reviews/some-id/findings/finding-id/resolve", 403, "Resolve finding (blocked)"),
        ]
        
        print(f"\n{'ROLE':12s} {'METHOD':6s} {'ENDPOINT':60s} {'EXP':4s}  DESCRIPTION")
        print(f"{'─' * 110}")
        for role, method, endpoint, expected, desc in tests:
            print(f"{role:12s} {method:6s} {endpoint:60s} {expected:4d}  {desc}")

    await engine.dispose()

asyncio.run(main())
