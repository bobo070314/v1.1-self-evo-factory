#!/usr/bin/env python3
"""快速规则测试"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def test_simple_rule():
    """测试简单规则功能"""
    print("🔧 测试规则系统功能")
    
    try:
        # 直接测试规则引擎
        from core.rules_orchestrator import RulesOrchestrator
        from core.rules.config_loader import load_rules
        
        # 加载规则
        rules = load_rules('core/rules')
        print(f"✅ 成功加载 {len(rules)} 个规则")
        
        # 创建规则编排器
        ro = RulesOrchestrator()
        health = ro.health()
        print(f"✅ 规则编排器健康状态: {health}")
        
        # 测试一个具体的规则
        test_code = "function Component() { return <div className=\"animate-spin\">Loading</div>; }"
        result = ro.check_output(test_code)
        print(f"🔍 检查违规代码结果: {result}")
        
        # 测试正常代码
        normal_code = "function Component() { return <div>Hello World</div>; }"
        normal_result = ro.check_output(normal_code)
        print(f"✅ 检查正常代码结果: {normal_result}")
        
        # 验证规则是否正确加载
        print("\n📋 已加载的规则:")
        for i, rule in enumerate(rules[:5]):  # 显示前5个
            print(f"  {i+1}. {rule.name} (event: {rule.event}, action: {rule.action})")
            
        if len(rules) > 5:
            print(f"  ... 还有 {len(rules)-5} 个规则")
            
        return True
        
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("🚀 快速规则系统测试")
    print("=" * 40)
    
    success = test_simple_rule()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 测试完成！系统功能正常。")
        return 0
    else:
        print("⚠️ 测试发现问题。")
        return 1

if __name__ == "__main__":
    sys.exit(main())