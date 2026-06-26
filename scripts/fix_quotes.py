#!/usr/bin/env python3
"""修复规则加载中的引号问题"""

import os
import re

def fix_extract_frontmatter():
    """修复 extract_frontmatter 函数中的引号处理问题"""
    
    # 读取文件
    file_path = 'core/rules/config_loader.py'
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定位 extract_frontmatter 函数
    func_pattern = r'def extract_frontmatter\(content: str\) -> tuple:.*?return frontmatter, body'
    
    # 修复函数中的引号处理逻辑
    replacement = '''def extract_frontmatter(content: str) -> tuple:
    """Extract YAML-like frontmatter (--- ... ---) and body from markdown."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw = parts[1]
    body = parts[2].strip()

    # Simple key-value parser (no nested YAML)
    frontmatter = {}
    current_key = None
    current_list = []
    current_dict = {}
    in_list = False
    in_dict_item = False

    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        if indent == 0 and ":" in line and not s.startswith("-"):
            # Finalize previous list/dict
            if in_list and current_key:
                if in_dict_item and current_dict:
                    current_list.append(current_dict)
                    current_dict = {}
                frontmatter[current_key] = current_list
                in_list = False
                in_dict_item = False
                current_list = []
            # New top-level key
            k, v = s.split(":", 1)
            k = k.strip()
            v = v.strip()
            if not v:
                current_key = k
                in_list = True
            else:
                if v.lower() == "true":
                    v = True
                elif v.lower() == "false":
                    v = False
                # Remove surrounding quotes from string values
                if v.startswith('"') and v.endswith('"'):
                    v = v[1:-1]
                frontmatter[k] = v

        elif s.startswith("-") and in_list:
            if in_dict_item and current_dict:
                current_list.append(current_dict)
                current_dict = {}
            item = s[1:].strip()
            if ":" in item and "," in item:
                # Inline dict: - field: command, operator: regex_match
                d = {}
                for part in item.split(","):
                    if ":" in part:
                        k, v = part.split(":", 1)
                        d[k.strip()] = v.strip().strip('"').strip("'")
                current_list.append(d)
                in_dict_item = False
            elif ":" in item:
                in_dict_item = True
                k, v = item.split(":", 1)
                current_dict = {k.strip(): v.strip().strip('"').strip("'")}
            else:
                # Clean quotes from list items
                cleaned_item = item.strip('"').strip("'")
                current_list.append(cleaned_item)
                in_dict_item = False

        elif indent > 2 and in_dict_item and ":" in line:
            k, v = s.split(":", 1)
            cleaned_v = v.strip().strip('"').strip("'")
            current_dict[k.strip()] = cleaned_v

    if in_list and current_key:
        if in_dict_item and current_dict:
            current_list.append(current_dict)
        frontmatter[current_key] = current_list

    return frontmatter, body'''

    # 执行替换
    new_content = re.sub(func_pattern, replacement, content, flags=re.DOTALL)
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ 已修复 extract_frontmatter 函数中的引号处理问题")

if __name__ == "__main__":
    fix_extract_frontmatter()