import sys
sys.path.insert(0, '.')

# Test that yolo_classifier is properly updated
from core.yolo_classifier import classify
print('yolo_classifier imported')

# Test that global_compliance is properly updated  
from core.global_compliance import run_security_scan
print('global_compliance imported')

# Test basic functionality
result = classify('print("hello")')
print('classify() works:', result['passed'])

result = run_security_scan('print("hello")')
print('run_security_scan() works:', result['passed'])

print('All basic tests passed')