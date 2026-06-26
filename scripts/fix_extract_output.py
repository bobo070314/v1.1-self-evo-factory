#!/usr/bin/env python3
"""修复 _extract_output 函数"""

import re

def fix_extract_output():
    with open('core/core_orchestrator.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the _extract_output function
    pattern = r'def _extract_output\(text: str\) -> str:\s*.*?"""[^"]*"""(?:\s*[^"]*?)?\s*if not text:\s*return ""\s*import re\s*m = re\.search\(r\'\\\\\[OUTPUT\\\\\](.*?)\\\\\[/OUTPUT\\\\\]\', text, re\.DOTALL \| re\.IGNORECASE\)\s*if m:\s*return m\.group\(1\)\.strip()\s*# 没标签但很短——可能只吐了结果\s*if len\(text\) < 100:\s*return text\.strip()\s*return ""\s*# 长文本无标签视为无效'
    
    # Replace it with corrected version
    replacement = '''def _extract_output(text: str) -> str:
    """精准提取 [OUTPUT]...[/OUTPUT] 块，无标签时返回空"""
    if not text:
        return ""
    import re
    m = re.search(r'\\[OUTPUT\\](.*?)\\[/OUTPUT\\]', text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return ""   # 无标签时直接返回空，不回退到原始文本'''
    
    # First, let's try a simpler replacement
    lines = content.split('\n')
    in_function = False
    function_start = -1
    
    for i, line in enumerate(lines):
        if 'def _extract_output' in line:
            in_function = True
            function_start = i
        elif in_function and line.strip() == 'return ""   # 长文本无标签视为无效':
            # Found the end of function
            lines[i] = '    return ""   # 无标签时直接返回空，不回退到原始文本'
            break
        elif in_function and line.strip() == 'return ""   # 没标签但很短——可能只吐了结果':
            lines[i] = '    return ""   # 无标签时直接返回空，不回退到原始文本'
    
    # Write back
    with open('core/core_orchestrator.py', 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

if __name__ == '__main__':
    fix_extract_output()