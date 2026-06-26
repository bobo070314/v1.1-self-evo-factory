#!/usr/bin/env python3
"""测试重构后的 yolo_classifier 和 global_compliance 模块"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_yolo_classifier():
    """测试 yolo_classifier 的重构"""
    print("Testing yolo_classifier...")
    
    # Import the module
    try:
        from core.yolo_classifier import classify
        print("✓ yolo_classifier imported successfully")
        
        # Test basic functionality
        result = classify("print('hello')")
        print(f"✓ classify() works: {result['passed']}")
        
        # Test with a simple security issue
        result = classify("os.system('ls')")
        print(f"✓ classify() with security issue: {result['passed']}")
        
        print("✓ yolo_classifier tests passed")
        return True
    except Exception as e:
        print(f"✗ yolo_classifier test failed: {e}")
        return False

def test_global_compliance():
    """测试 global_compliance 的重构"""
    print("\nTesting global_compliance...")
    
    try:
        from core.global_compliance import run_security_scan
        print("✓ global_compliance imported successfully")
        
        # Test basic functionality
        result = run_security_scan("print('hello')")
        print(f"✓ run_security_scan() works: {result['passed']}")
        
        print("✓ global_compliance tests passed")
        return True
    except Exception as e:
        print(f"✗ global_compliance test failed: {e}")
        return False

def test_imports():
    """测试导入是否正确"""
    print("\nTesting imports...")
    
    try:
        # Test that the old imports are no longer present
        import core.yolo_classifier
        import core.global_compliance
        
        # Check that the old import is removed from global_compliance
        with open('core/global_compliance.py', 'r') as f:
            content = f.read()
            
        if 'from yolo_classifier import classify as yolo_classify' in content:
            print("✗ Old import still present in global_compliance.py")
            return False
        else:
            print("✓ Old imports correctly removed from global_compliance.py")
            
        print("✓ All import tests passed")
        return True
    except Exception as e:
        print(f"✗ Import test failed: {e}")
        return False

def main():
    """主测试函数"""
    print("Running refactor verification tests...\n")
    
    tests = [
        test_imports,
        test_yolo_classifier,
        test_global_compliance
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())