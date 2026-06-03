#!/usr/bin/env python3
"""Create dedicated test reviews for each queue state."""
import hashlib, hmac, json, time, urllib.request, urllib.error, sys
from base64 import urlsafe_b64encode
from sqlalchemy import create_engine, text

BASE_URL = 'http://localhost:3000'
API_URL = f'{BASE_URL}/api/v1'
DB_URL = 'postgresql+psycopg2://dev_user:dev_password@localhost:5432/contract_risk_dev'
DEV_JWT_SECRET = 'dev-local-jwt-secret-do-not-use-in-production'

h = urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=').decode()
p = urlsafe_b64encode(json.dumps({'sub':'dev-user','email':'dev@localhost','tenant_id':'00000000-0000-4000-8000-000000000001','role':'tenant_admin','permissions':['*'],'exp':int(time.time())+3600,'iat':int(time.time())}).encode()).rstrip(b'=').decode()
s = urlsafe_b64encode(hmac.new(DEV_JWT_SECRET.encode(),f'{h}.{p}'.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
token = f'{h}.{p}.{s}'

def api(method, path, body=None):
    url = f'{API_URL}{path}'
    req = urllib.request.Request(url, method=method)
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', 'application/json')
    try:
        r = urllib.request.urlopen(req, json.dumps(body).encode() if body else None)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, {'detail': str(e)}

def db(sql):
    with create_engine(DB_URL).connect() as c:
        return [dict(r._mapping) for r in c.execute(text(sql))]

def upload(content, filename):
    with open(f'/tmp/{filename}', 'w') as f:
        f.write(content)
    boundary = '----Boundary7MA4YW'
    with open(f'/tmp/{filename}', 'rb') as f:
        file_data = f.read()
    body = b''
    body += f'--{boundary}\r\n'.encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    body += b'Content-Type: text/plain\r\n\r\n'
    body += file_data + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    req = urllib.request.Request(f'{API_URL}/uploads', data=body, method='POST')
    req.add_header('Authorization', f'Bearer {token}')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    r = urllib.request.urlopen(req)
    resp = json.loads(r.read().decode())
    return resp['upload_id']

def wait_for_review(upload_id, timeout=120):
    for i in range(timeout):
        with create_engine(DB_URL).connect() as c:
            row = c.execute(text(f"SELECT review_id::text FROM contract_reviews WHERE upload_id='{upload_id}'")).fetchone()
            if row:
                return row[0]
        time.sleep(1)
    return None

# ── Check existing state ──
existing = db("SELECT review_id::text, status, workflow_stage FROM contract_reviews WHERE is_deleted=FALSE ORDER BY created_at DESC")
print("=== EXISTING REVIEWS ===")
for r in existing:
    print(f"  {r['review_id'][:12]}... status={r['status']:20s} stage={str(r['workflow_stage']):15s}")

# We need 4 reviews in specific states.
# Check if we already have exec_approval from earlier run
exec_review = [r for r in existing if r['status'] == 'exec_approval']
if exec_review:
    RID_EXEC = exec_review[0]['review_id']
    print(f"\nUsing existing exec_approval: {RID_EXEC[:12]}...")
else:
    print("\nERROR: No exec_approval review found. Run the lifecycle test first.")
    sys.exit(1)

# Create legal_approval review (separate from exec)
print("\n=== Creating LEGAL APPROVAL review ===")
uid = upload("LEASE AGREEMENT\n\n1. PREMISES: Office space at 123 Main St.\n2. TERM: 5 years.\n3. RENT: $10,000/month.\n4. SECURITY: $20,000 deposit.\n5. MAINTENANCE: Landlord responsible for structural repairs.\n6. INSURANCE: Tenant shall maintain liability insurance.\n", 'legal_test.txt')
print(f"  Upload: {uid[:12]}...")
RID_LEGAL = wait_for_review(uid)
if RID_LEGAL:
    print(f"  Review: {RID_LEGAL[:12]}...")
    api('POST', f'/reviews/{RID_LEGAL}/assign', {'assignee_id': 'legal@test.com', 'role': 'reviewer'})
    api('POST', f'/reviews/{RID_LEGAL}/status?status=legal_approval&reason=Legal+queue+test')
    r = db(f"SELECT status, workflow_stage FROM contract_reviews WHERE review_id::text='{RID_LEGAL}'")
    print(f"  Result: status={r[0]['status']} stage={r[0]['workflow_stage']}")

# Create compliance_review
print("\n=== Creating COMPLIANCE REVIEW ===")
uid = upload("DATA PROCESSING AGREEMENT\n\n1. DATA: Personal data processing as per Schedule 1.\n2. SECURITY: Encryption at rest and in transit.\n3. BREACH: Notification within 24 hours.\n4. AUDIT: Annual right to audit.\n5. SUB-PROCESSORS: Prior written consent required.\n", 'compliance_test.txt')
print(f"  Upload: {uid[:12]}...")
RID_COMP = wait_for_review(uid)
if RID_COMP:
    print(f"  Review: {RID_COMP[:12]}...")
    api('POST', f'/reviews/{RID_COMP}/assign', {'assignee_id': 'compliance@test.com', 'role': 'reviewer'})
    # Direct DB update for compliance_review
    with create_engine(DB_URL).connect() as c:
        c.execute(text(f"UPDATE contract_reviews SET status='compliance_review', workflow_stage='compliance', updated_at=NOW() WHERE review_id='{RID_COMP}'"))
        c.commit()
    r = db(f"SELECT status, workflow_stage FROM contract_reviews WHERE review_id::text='{RID_COMP}'")
    print(f"  Result: status={r[0]['status']} stage={r[0]['workflow_stage']}")

# Create escalated review
print("\n=== Creating ESCALATED review ===")
uid = upload("NDA WITH ESCALATION\n\nConfidentiality for merger talks.\n1. PARTIES: Buyer and Target Corp.\n2. CONFIDENTIALITY: 5 years.\n3. NON-COMPETE: 2 years.\n4. GOVERNING LAW: New York.\n", 'escalated_test.txt')
print(f"  Upload: {uid[:12]}...")
RID_ESC = wait_for_review(uid)
if RID_ESC:
    print(f"  Review: {RID_ESC[:12]}...")
    api('POST', f'/reviews/{RID_ESC}/assign', {'assignee_id': 'escalated@test.com', 'role': 'reviewer'})
    api('POST', f'/reviews/{RID_ESC}/status?status=escalated&reason=Escalated+queue+test')
    r = db(f"SELECT status, workflow_stage FROM contract_reviews WHERE review_id::text='{RID_ESC}'")
    print(f"  Result: status={r[0]['status']} stage={r[0]['workflow_stage']}")

print("\n=== FINAL TEST REVIEWS ===")
print(f"  Legal Test:      {RID_LEGAL}")
print(f"  Exec Test:       {RID_EXEC}")
print(f"  Compliance Test: {RID_COMP}")
print(f"  Escalated Test:  {RID_ESC}")
