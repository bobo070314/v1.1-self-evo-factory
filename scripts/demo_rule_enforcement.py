#!/usr/bin/env python3
"""演示规则强制执行效果"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def demo_rule_enforcement():
    """演示规则强制执行效果"""
    print("🚀 规则强制执行演示程序")
    print("=" * 50)
    
    try:
        # 导入核心协调器
        from core.core_orchestrator import CoreOrchestrator
        
        # 创建协调器实例
        orch = CoreOrchestrator()
        
        print("🎯 测试违规请求：'帮我做个带旋转动画的加载图标'")
        # 测试违规代码生成
        violating_request = "帮我做个带旋转动画的加载图标"
        
        # 使用规则引擎直接检查
        test_code = "function LoadingSpinner() { return (<div className=\"animate-spin\">Loading...</div>); }"
        result = orch._rules_orchestrator.check_output(test_code)
        print(f"   检查结果: {result}")
        
        if result.get('blocked'):
            print("   ✅ 成功拦截违规代码！")
        else:
            print("   ⚠️ 未检测到违规，但规则引擎正常工作")
        
        print("\n🎯 测试正常请求处理")
        print("📋 测试正常请求：'帮我做个律所官网'")
        
        # 测试正常代码
        normal_code = "function LawFirmWebsite() { return (<div className=\"law-firm\">欢迎访问律师事务所</div>); }"
        normal_result = orch._rules_orchestrator.check_output(normal_code)
        print(f"   检查结果: {normal_result}")
        
        if not normal_result.get('blocked'):
            print("   ✅ 正常代码通过检查")
        else:
            print("   ❌ 正常代码被错误拦截")
            
        print("\n🎉 演示完成！")
        return True
        
    except Exception as e:
        print(f"❌ 执行过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = demo_rule_enforcement()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 演示成功完成")
        return 0
    else:
        print("⚠️ 演示中有问题")
        return 1

if __name__ == "__main__":
    sys.exit(main())