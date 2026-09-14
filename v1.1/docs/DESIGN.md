---
name: Paper Setting v1.1 Design System
colors:
  surface: '#ffffff'
  surface-card: '#fffdfa'
  surface-elevated: '#ffffff'
  canvas: '#f4f0e6'
  canvas-soft: '#edf4ee'
  ink: '#18221c'
  ink-secondary: '#58655d'
  ink-muted: '#859188'
  primary: '#1c5d43'
  primary-hover: '#12402e'
  primary-container: '#edf4ee'
  agent-purple: '#5b4aa6'
  agent-purple-light: '#f3f0fd'
  outline: '#e2dcd0'
  outline-strong: '#c9c2b2'
  semantic-success: '#287a55'
  semantic-error: '#d9534f'
typography:
  display-title:
    fontFamily: Songti SC, Source Han Serif SC, Georgia, serif
    fontSize: 34px
    fontWeight: '700'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Songti SC, Source Han Serif SC, Georgia, serif
    fontSize: 26px
    fontWeight: '600'
    lineHeight: '1.3'
  headline-sm:
    fontFamily: Inter, -apple-system, PingFang SC, Microsoft YaHei, sans-serif
    fontSize: 18px
    fontWeight: '600'
    lineHeight: '1.4'
  body-md:
    fontFamily: Inter, -apple-system, PingFang SC, Microsoft YaHei, sans-serif
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: Inter, -apple-system, PingFang SC, Microsoft YaHei, sans-serif
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
  label-caps:
    fontFamily: Inter, -apple-system, PingFang SC, Microsoft YaHei, sans-serif
    fontSize: 11px
    fontWeight: '700'
    letterSpacing: '0.08em'
rounded:
  sm: 6px
  md: 12px
  lg: 16px
  xl: 20px
  pill: 32px
spacing:
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
---

# Paper Setting v1.1 论文排版工作台设计规范

## 1. 品牌理念与质感定位
本系统为面向学术论文的严谨、安全、一键自动化智能排版平台。
- **视觉风格**：融合宋体传统纸墨温润感（Warm Paper Canvas ）与现代学术翡翠绿（Emerald ）。
- **隐私原则**：纯单机本地沙箱处理，零网络上传，0 Token 离线纯算。
- **双视图架构**：
  1. **极简排版向导 (默认)**：4 步闭环（上传文稿 -> 目标规范 -> 本地排版 -> 导出成品）。
  2. **详细与 Agent 智排**：攻坚复杂格式，支持 NLP 规范自动推导、段落级 OOXML 差异审计与 AI 盲审质检。

## 2. 核心交互模式 (Motion-Inspired)
- **Sliding Indicator Segmented Control**：顶部带有果冻物理弹簧缓动（）的滑块指示器。
- **Radial Gauge Progress Ring**：排版处理阶段的环形动态仪表盘，带实时离线绿点脉冲。
- **3D Document Mockup**：排版前后视觉对比看板，支持鼠标跟随微倾斜（Tilt Effect）与排版前后（Before vs After）无缝切页。
