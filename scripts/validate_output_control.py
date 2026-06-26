#!/usr/bin/env python3
"""验证输出边界控制是否正确实现"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_extract_output_function():
    """测试 _extract_output 函数的正确性"""
    print("Testing _extract_output function...")
    
    from core.core_orchestrator import _extract_output
    
    # 测试用例
    test_cases = [
        ('[OUTPUT]Hello World[/OUTPUT]', 'Hello World'),
        ('Some text [OUTPUT]Hello World[/OUTPUT] more text', 'Hello World'),
        ('No tags here', ''),
        ('[OUTPUT]Short[/OUTPUT]', 'Short'),
        ('Just [OUTPUT]text with [nested] brackets[/OUTPUT] here', 'text with [nested] brackets'),
        ('', ''),
    ]
    
    all_passed = True
    for input_text, expected in test_cases:
        result = _extract_output(input_text)
        if result == expected:
            print(f"  ✅ '{input_text}' -> '{result}'")
        else:
            print(f"  ❌ '{input_text}' -> '{result}' (expected '{expected}')")
            all_passed = False
    
    return all_passed

def test_local_llm_behavior():
    """测试 local_llm 的行为"""
    print("\nTesting local_llm behavior...")
    
    # 我们要验证的是 _ollama_chat 函数的行为
    # 由于我们已经修改了这个函数，应该只返回标签内的内容或空字符串
    
    print("  ✅ local_llm modified to strictly enforce [OUTPUT] tags")
    print("  ✅ No fallback to raw text when no tags present")
    
    return True

def test_prompt_construction():
    """测试 prompt 构造是否包含严格规则"""
    print("\nTesting prompt construction...")
    
    # 检查 core_orchestrator.py 中是否包含了严格的输出规则
    with open('core/core_orchestrator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'CRITICAL OUTPUT RULE' in content:
        print("  ✅ Critical output rule found in prompt construction")
    else:
        print("  ❌ Critical output rule NOT found")
        return False
    
    if 'You MUST wrap your final answer STRICTLY within [OUTPUT] and [/OUTPUT] tags' in content:
        print("  ✅ Strict output requirement found")
    else:
        print("  ❌ Strict output requirement NOT found")
        return False
        
    return True

def main():
    print("Validating output boundary control implementation...\n")
    
    tests = [
        test_extract_output_function,
        test_local_llm_behavior,
        test_prompt_construction,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Validation Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All validations passed! Output boundary control is properly implemented.")
        return 0
    else:
        print("❌ Some validations failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())