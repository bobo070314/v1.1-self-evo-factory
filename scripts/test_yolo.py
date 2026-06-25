#!/usr/bin/env python3
"""Test YOLO classifier with dangerous code sample."""
import json, sys
sys.path.insert(0, r'D:\bobo\projects\v1.1-self-evo-factory\core')
from yolo_classifier import classify

dangerous_code = """
import os, pickle, subprocess
API_KEY = 'sk-proj-abc123xyz456verylongkey789'
pwd = 'admin123'
def login():
    user = request.form['username']
    sql = f"SELECT * FROM users WHERE name = '{user}'"
    os.system('rm -rf /home/' + user)
    result = pickle.loads(request.data)
    subprocess.run(user, shell=True)
    document.getElementById('output').innerHTML = user
    return '<div dangerouslySetInnerHTML={{__html: user}} />'
"""

result = classify(dangerous_code)
print(result['summary'])
print(f"Passed: {result['passed']}")
print(f"Severity: {result['severity_counts']}")
for f in result['failures']:
    print(f"  [{f['level']}] {f['id']}: {f['message']}")
sys.exit(0 if result['passed'] else 1)
