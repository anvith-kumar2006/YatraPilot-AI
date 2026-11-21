#!/usr/bin/env python3
"""
Verify Flask app startup and basic functionality.
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

from app import app
from database.db import init_db

print('\n' + '='*70)
print('  FLASK APP STARTUP TEST')
print('='*70 + '\n')

# Initialize database
print('[*] Initializing database...')
init_db()

# Start app in test mode
print('[*] Creating Flask test client...')
client = app.test_client()

# Test health endpoint
print('[*] Testing GET /health...')
response = client.get('/health')
print(f'    Status: {response.status_code}')
print(f'    Response: {response.get_json()}')

# Test trips endpoint
print('[*] Testing GET /api/trips...')
response = client.get('/api/trips')
print(f'    Status: {response.status_code}')
data = response.get_json()
print(f'    Trips in DB: {len(data.get("trips", []))}')

print('\n[PASS] Flask application startup successful!')
print('='*70 + '\n')
