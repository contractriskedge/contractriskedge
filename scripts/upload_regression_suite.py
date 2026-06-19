#!/usr/bin/env python3
"""Upload all 64 regression suite contracts via the API for a clean e2e test."""
import hashlib, hmac, json, os, sys, time, urllib.request, urllib.error
from base64 import urlsafe_b64encode
from datetime import datetime

API_URL = 'http://localhost:8000/api/v1'
DEV_JWT_SECRET = 'dev-local-jwt-secret-do-not-use-in-production'
REGRESSION_DIR = os.path.join(os.path.dirname(__file__), '..', 'SampleContracts', 'RegressionSuite')

h = urlsafe_b64encode(json.dumps({'alg':'HS256','typ':'JWT'}).encode()).rstrip(b'=').decode()
p = urlsafe_b64encode(json.dumps({'sub':'dev-user','email':'dev@localhost','tenant_id':'00000000-0000-4000-8000-000000000001','role':'tenant_admin','permissions':['*'],'exp':int(time.time())+7200,'iat':int(time.time())}).encode()).rstrip(b'=').decode()
s = urlsafe_b64encode(hmac.new(DEV_JWT_SECRET.encode(),f'{h}.{p}'.encode(),hashlib.sha256).digest()).rstrip(b'=').decode()
TOKEN = f'{h}.{p}.{s}'

def upload_file(filepath):
    filename = os.path.basename(filepath)
    boundary = '----Boundary7MA4YW'
    with open(filepath, 'rb') as f:
        file_data = f.read()
    body = b''
    body += f'--{boundary}\r\n'.encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    body += b'Content-Type: application/pdf\r\n\r\n'
    body += file_data + b'\r\n'
    body += f'--{boundary}--\r\n'.encode()
    req = urllib.request.Request(f'{API_URL}/uploads', data=body, method='POST')
    req.add_header('Authorization', f'Bearer {TOKEN}')
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    try:
        r = urllib.request.urlopen(req, timeout=60)
        resp = json.loads(r.read().decode())
        return r.status, resp.get('upload_id', '?')
    except urllib.error.HTTPError as e:
        return e.code, str(e.read())[:200]

# Collect all PDFs
files = []
for root, dirs, filenames in os.walk(REGRESSION_DIR):
    for fn in sorted(filenames):
        if fn.endswith('.pdf'):
            files.append(os.path.join(root, fn))

print(f'Found {len(files)} PDF files to upload')
print(f'Started: {datetime.utcnow().isoformat()}')
print('=' * 60)

success = 0
fail = 0
for i, fp in enumerate(files, 1):
    rel = os.path.relpath(fp, REGRESSION_DIR)
    status, upload_id = upload_file(fp)
    if status == 201 or status == 200:
        print(f'  [{i:2d}/{len(files)}] ✅ {upload_id[:12]}...  {rel}')
        success += 1
    else:
        print(f'  [{i:2d}/{len(files)}] ❌ HTTP {status}  {rel}')
        fail += 1
    # Small delay to avoid overwhelming the server
    if i % 10 == 0:
        time.sleep(1)

print('=' * 60)
print(f'Done: {success} succeeded, {fail} failed')
print(f'Finished: {datetime.utcnow().isoformat()}')
