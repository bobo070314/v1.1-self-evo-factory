#!/usr/bin/env python3
"""调试规则加载问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

def debug_rule_loading():
    """调试规则加载过程"""
    print("🔍 调试规则加载过程")
    print("=" * 40)
    
    try:
        # 直接测试规则加载器
        from core.rules.config_loader import load_rules, extract_frontmatter
        
        print("1. 测试规则目录结构:")
        rules_dir = 'core/rules'
        files = [f for f in os.listdir(rules_dir) if f.endswith('.local.md')]
        print(f"   发现 {len(files)} 个规则文件")
        for f in files[:3]:  # 只显示前3个
            print(f"   - {f}")
            
        print("\n2. 测试单个文件解析:")
        test_file = 'core/rules/no-animate-spin.local.md'
        if os.path.exists(test_file):
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            print(f"   文件大小: {len(content)} 字符")
            frontmatter, body = extract_frontmatter(content)
            print(f"   提取的frontmatter: {frontmatter}")
            print(f"   提取的body长度: {len(body)}")
            
            # 用更简单的测试
            print("\n3. 测试现有规则文件:")
            for i, fname in enumerate(files[:3]):
                filepath = os.path.join(rules_dir, fname)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                frontmatter, body = extract_frontmatter(content)
                print(f"   {fname}: frontmatter={frontmatter}")
                if i >= 2:  # 只显示前3个
                    break
                    
        print("\n4. 测试加载函数:")
        rules = load_rules(rules_dir)
        print(f"   load_rules() 返回 {len(rules)} 个规则")
        
        # 手动检查规则加载的逻辑
        print("\n5. 手动验证加载过程:")
        pattern = os.path.join(rules_dir, "*.local.md")
        import glob
        files = glob.glob(pattern)
        print(f"   glob 找到 {len(files)} 个文件")
        
        for i, fp in enumerate(files[:3]):
            print(f"   文件 {i+1}: {os.path.basename(fp)}")
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                frontmatter, body = extract_frontmatter(content)
                print(f"     frontmatter: {frontmatter}")
                if not frontmatter:
                    print(f"     ⚠️  前端数据为空")
                else:
                    print(f"     ✅ 前端数据有效")
            except Exception as e:
                print(f"     ❌ 读取错误: {e}")
                
        return True
        
    except Exception as e:
        print(f"❌ 调试出错: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = debug_rule_loading()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ 调试完成")
        return 0
    else:
        print("⚠️ 调试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())