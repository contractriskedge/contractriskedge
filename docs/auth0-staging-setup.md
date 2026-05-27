# Auth0 Staging Environment Setup

## Why This Matters Now

Your system now:
- Auto-assigns reviews to reviewers
- Escalates workflows through approval chains
- Replays events via WebSocket on reconnect
- Persists operational state with governance audit trails

**The dev auth bypass is no longer acceptable.**

Every automation action (auto-assignment, escalation, recovery) runs with
system-level credentials. Without real Auth0 validation, you cannot:

- Test RBAC enforcement for different reviewer roles
- Validate that escalation permissions are correctly scoped
- Ensure WebSocket replay events respect tenant isolation
- Verify that auto-assignment respects role boundaries

---

## 1. Create an Auth0 Staging Tenant

### Step 1: Sign up / log in to Auth0

Go to https://auth0.com and create an account if you don't have one.

### Step 2: Create a new tenant

1. Click **Create Tenant**
2. Name it something like `contract-risk-staging`
3. Select **Development** environment type
4. Choose region closest to your deployment

### Step 3: Configure Application

1. Go to **Applications → Applications**
2. Click **Create Application**
3. Name: `ContractRiskEdge Staging`
4. Type: **Single Page Application** (for frontend)
5. Click **Create**

### Step 4: Configure Application Settings

```
Allowed Callback URLs:
    http://localhost:3000/api/auth/callback
    https://staging.contractriskedge.com/api/auth/callback

Allowed Logout URLs:
    http://localhost:3000
    https://staging.contractriskedge.com

Allowed Web Origins:
    http://localhost:3000
    https://staging.contractriskedge.com

Allowed Origins (CORS):
    http://localhost:3000
    https://staging.contractriskedge.com
```

### Step 5: Create a Machine-to-Machine Application (for backend)

1. Go to **Applications → Applications**
2. Click **Create Application**
3. Name: `ContractRiskEdge Backend (Staging)`
4. Type: **Machine to Machine**
5. Click **Create**
6. Select the API you'll create in the next section

---

## 2. Configure Auth0 API

### Step 1: Create API

1. Go to **Applications → APIs**
2. Click **Create API**
3. Name: `ContractRiskEdge API`
4. Identifier: `https://api.contractriskedge.com` (this is your `AUTH0_AUDIENCE`)
5. Signing Algorithm: `RS256`

### Step 2: Define Permissions

Add these permissions to the API. These map to `Permissions` in
`backend/app/kernel/security/permissions.py`:

```
contracts:read
contracts:write
contracts:delete
contracts:approve
ai:analyze
ai:view
ai:manage
workflows:read
workflows:write
workflows:approve
workflows:escalate
vendors:read
vendors:write
audit:read
audit:export
users:read
users:write
users:delete
admin:tenant
reviews:export
notifications:manage
benchmarks:read
benchmarks:write
benchmarks:export
benchmarks:seed
benchmarks:admin
```

### Step 3: Define Roles

Create roles in Auth0 that match `Roles` in
`backend/app/kernel/security/roles.py`:

| Role | Permissions |
|------|-------------|
| `tenant_admin` | All permissions |
| `legal_reviewer` | `contracts:read`, `contracts:approve`, `ai:view`, `workflows:read`, `workflows:write`, `workflows:approve`, `workflows:escalate`, `audit:read`, `reviews:export`, `benchmarks:read` |
| `reviewer` | `contracts:read`, `ai:view`, `workflows:read`, `workflows:write` |
| `procurement` | `contracts:read`, `contracts:write`, `workflows:read` |
| `security` | `contracts:read`, `ai:view`, `workflows:read` |
| `viewer` | `contracts:read` |
| `auditor` | `contracts:read`, `audit:read`, `audit:export` |
| `developer` | `contracts:read`, `contracts:write`, `ai:analyze`, `ai:view`, `workflows:read`, `workflows:write`, `audit:read`, `reviews:export`, `benchmarks:read`, `benchmarks:write` |

### Step 4: Add Role-Based Claims to Access Token

Go to **Actions → Flows → Login** and create a new action:

```javascript
/**
 * Add custom claims to the access token for RBAC.
 * This action runs on every login and adds tenant_id + role
 * to the access token so the backend can enforce permissions.
 */
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://api.contractriskedge.com/';

  // Add tenant_id from app_metadata (set during user provisioning)
  const tenantId = event.user.app_metadata?.tenant_id || 'default';
  api.accessToken.setCustomClaim(`${namespace}tenant_id`, tenantId);

  // Add role from Auth0 role assignment
  const roles = event.authorization?.roles || [];
  const primaryRole = roles[0]?.toLowerCase().replace(/\s+/g, '_') || 'viewer';
  api.accessToken.setCustomClaim(`${namespace}role`, primaryRole);

  // Copy permissions from the role
  const permissions = event.authorization?.permissions || [];
  api.accessToken.setCustomClaim(`${namespace}permissions`, permissions);
};
```

---

## 3. Configure Backend Environment

### Staging `.env` file

Create `backend/.env.staging`:

```bash
# ── Environment ─────────────────────────────────────────────────
ENVIRONMENT=staging

# ── Database ────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://user:password@staging-db:5432/contract_risk_staging

# ── Auth0 ───────────────────────────────────────────────────────
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.contractriskedge.com
AUTH0_ISSUER=https://your-tenant.us.auth0.com/

# ── Secrets ─────────────────────────────────────────────────────
SECRET_KEY=<generate-a-unique-secret>
DEV_JWT_SECRET=<not-used-in-staging>
DEV_AUTH_BYPASS=false

# ── Dev Identity (not used when bypass is off) ──────────────────
DEV_USER_ID=dev-user
DEV_TENANT_ID=00000000-0000-4000-8000-000000000001
```

### Generate secrets

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 4. Frontend Auth Integration

### Install Auth0 React SDK

```bash
cd frontend
npm install @auth0/auth0-react
```

### Configure Auth0 Provider

```tsx
// frontend/src/app/providers.tsx
import { Auth0Provider } from '@auth0/auth0-react';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  return (
    <Auth0Provider
      domain={process.env.NEXT_PUBLIC_AUTH0_DOMAIN!}
      clientId={process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID!}
      authorizationParams={{
        audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
        redirect_uri: typeof window !== 'undefined'
          ? `${window.location.origin}/api/auth/callback`
          : undefined,
        scope: 'openid profile email',
      }}
      cacheLocation="localstorage"
      useRefreshTokens={true}
    >
      {children}
    </Auth0Provider>
  );
}
```

### Get Access Token for API Calls

```tsx
// frontend/src/lib/api.ts
import { useAuth0 } from '@auth0/auth0-react';

export function useApi() {
  const { getAccessTokenSilently } = useAuth0();

  const apiFetch = async (url: string, options: RequestInit = {}) => {
    const token = await getAccessTokenSilently();

    const response = await fetch(url, {
      ...options,
      headers: {
        ...options.headers,
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    if (response.status === 401) {
      // Token expired or invalid — Auth0 SDK handles refresh automatically
      throw new Error('Authentication failed');
    }

    return response.json();
  };

  return { apiFetch };
}
```

### WebSocket Auth with Token

```tsx
// frontend/src/lib/websocket.ts
export class RealtimeClient {
  private ws: WebSocket | null = null;
  private lastSequenceId: number = 0;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 10;

  async connect(getToken: () => Promise<string>) {
    const token = await getToken();
    this.ws = new WebSocket(`/api/v1/ws/events`);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;

      // Send auth token
      this.ws!.send(JSON.stringify({
        type: 'auth',
        token,
        // Request replay of missed events on reconnect
        last_sequence_id: this.lastSequenceId,
      }));

      // Subscribe to relevant topics
      this.ws!.send(JSON.stringify({
        type: 'subscribe',
        topics: [
          'review.*',
          'notification.*',
          'recovery.*',
          'job.*',
        ],
      }));
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      // Track sequence ID for replay
      if (msg.sequence_id) {
        this.lastSequenceId = msg.sequence_id;
        localStorage.setItem('ws_last_sequence', String(msg.sequence_id));
      }

      // Acknowledge delivery
      if (msg.event_id) {
        this.ws?.send(JSON.stringify({
          type: 'ack',
          event_id: msg.event_id,
        }));
      }

      // Dispatch to handlers
      this.handleMessage(msg);
    };

    this.ws.onclose = () => {
      // Reconnect with exponential backoff
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      this.reconnectAttempts++;
      setTimeout(() => this.connect(getToken), delay);
    };
  }
}
```

---

## 5. Testing Auth in Staging

### Verify Token Acquisition

```bash
# Get a test token using Auth0's OAuth flow
curl -X POST https://your-tenant.us.auth0.com/oauth/token \
  -H 'Content-Type: application/json' \
  -d '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.contractriskedge.com",
    "grant_type": "client_credentials"
  }'

# Test the token against the API
curl -H 'Authorization: Bearer TOKEN' \
  http://localhost:8000/api/v1/health
```

### Verify RBAC Enforcement

```bash
# Test with viewer role — should FAIL for write operations
curl -H 'Authorization: Bearer VIEWER_TOKEN' \
  -X POST http://localhost:8000/api/v1/reviews \
  -H 'Content-Type: application/json' \
  -d '{}'
# Expected: 403 Forbidden

# Test with admin role — should SUCCEED
curl -H 'Authorization: Bearer ADMIN_TOKEN' \
  http://localhost:8000/api/v1/reviews
# Expected: 200 OK
```

### Verify WebSocket Auth

```bash
# Use wscat to test WebSocket auth
npm install -g wscat

wscat -c ws://localhost:8000/api/v1/ws/events

# Send auth message
> {"type": "auth", "token": "YOUR_TOKEN"}

# Verify connected response
< {"type": "connected", "data": {"tenant_id": "...", ...}}

# Test subscription
> {"type": "subscribe", "topics": ["review.*", "notification.*"]}
< {"type": "subscribed", "data": {"topics": ["review.*", "notification.*"]}}

# Test replay on reconnect (simulate disconnect by closing and reconnecting)
# Store the last sequence_id, then reconnect with:
> {"type": "auth", "token": "YOUR_TOKEN", "last_sequence_id": 42}
< {"type": "replay_start", "data": {"count": 5, ...}}
< ... replayed events ...
< {"type": "replay_complete", "data": {"count": 5}}
```

---

## 6. Environment Configuration Summary

| Variable | Development | Staging | Production |
|----------|------------|---------|------------|
| `ENVIRONMENT` | `development` | `staging` | `production` |
| `AUTH0_DOMAIN` | Optional | Required | Required |
| `AUTH0_AUDIENCE` | Optional | Required | Required |
| `DEV_JWT_SECRET` | Required | Not used | Not used |
| `DEV_AUTH_BYPASS` | `true` (local) | `false` | `false` |
| `SECRET_KEY` | Required | Required | Required |

---

## 7. Migration Checklist

- [ ] Auth0 staging tenant created
- [ ] API defined with all permissions
- [ ] Roles created with correct permission sets
- [ ] Login action added for custom claims
- [ ] Backend `.env.staging` configured
- [ ] Frontend Auth0 provider configured
- [ ] Token refresh flow tested
- [ ] WebSocket auth tested
- [ ] RBAC enforcement verified
- [ ] Dev bypass disabled in staging
- [ ] Auto-assignment tested with real JWT
- [ ] Escalation flow tested with real JWT
- [ ] Event replay tested with real JWT
- [ ] All integration tests pass with real auth
