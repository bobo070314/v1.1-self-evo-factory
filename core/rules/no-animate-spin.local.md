---
name: no-animate-spin
event: all
enabled: true
action: block
conditions:
  - field: command
    operator: contains
    value: 旋转动画
  - field: command
    operator: contains
    value: 加载图标
---
禁止生成带旋转动画的加载组件。
检测到用户请求包含"旋转动画"+"加载图标"关键词组合。
要求使用 pulse/fade 类静态动画替代。
