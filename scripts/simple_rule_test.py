#!/usr/bin/env python3
"""简化版规则测试"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_rules_basic():
    """基础规则功能测试"""
    print("Testing basic rules functionality...")
    
    try:
        # 测试规则加载
        from core.rules_orchestrator import RulesOrchestrator
        from core.rules.config_loader import load_rules
        
        # 创建规则目录
        rules_dir = "core/rules"
        if not os.path.exists(rules_dir):
            os.makedirs(rules_dir)
            
        # 加载规则
        rules = load_rules(rules_dir)
        print(f"Loaded {len(rules)} rules from {rules_dir}")
        
        # 创建规则编排器
        ro = RulesOrchestrator()
        health = ro.health()
        print(f"Rules orchestrator health: {health}")
        
        # 测试规则检查
        test_code = "function MyComponent() { return (<div className=\"animate-spin\">Loading...</div>); }"
        result = ro.check_output(test_code)
        print(f"Rule check result: {result}")
        
        # 测试一个正常代码
        normal_code = "function MyComponent() { return (<div>Hello World</div>); }"
        normal_result = ro.check_output(normal_code)
        print(f"Normal code result: {normal_result}")
        
        print("✅ Basic rules test completed")
        return True
        
    except Exception as e:
        print(f"❌ Error in basic test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_rule_file():
    """测试规则文件是否正确创建"""
    print("\nTesting rule file creation...")
    
    try:
        rule_file = "core/rules/no-animate-spin.local.md"
        if os.path.exists(rule_file):
            with open(rule_file, 'r', encoding='utf-8') as f:
                content = f.read()
                print("✅ Rule file exists and readable")
                print(f"File size: {len(content)} characters")
                if "禁止动画旋转组件" in content:
                    print("✅ Rule file contains expected content")
                    return True
                else:
                    print("❌ Rule file missing expected content")
                    return False
        else:
            print("❌ Rule file does not exist")
            return False
            
    except Exception as e:
        print(f"❌ Error testing rule file: {e}")
        return False

def main():
    print("🧪 Simple rule test...\n")
    
    tests = [
        test_rule_file,
        test_rules_basic,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All simple tests passed!")
        return 0
    else:
        print("⚠️ Some tests had issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())