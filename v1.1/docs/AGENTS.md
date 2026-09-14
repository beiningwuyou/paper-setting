# Paper Setting v1.1 Agent Instructions

本文档是 `v1.1/` 子工程的专属开发与维护指引。任何在此目录下工作的 Agent 必须严格遵守以下规范。

---

## 1. 核心定位与双视图原则 (Dual-View Architecture)

v1.1 采用明确的“双视图”架构，面向学术论文排版的二元需求：

1. **默认视图：极简排版 (Minimalist Local Engine)**
   - **定位**：解决 90% 的常规论文格式排版（字号、字体、行距、页边距、标题分级、首行缩进）。
   - **隐私绝对红线**：
     - **100% 纯本地离线纯算**，严禁向任何外网或云端大模型发送用户论文内容。
     - **0 Token 消耗**，纯确定性规则引擎执行，彻底消除未发表论文的查重与泄密焦虑。
   - **交互流**：4 步极简向导（1 上传初稿 $\rightarrow$ 2 选定规范 $\rightarrow$ 3 本地秒级编译 $\rightarrow$ 4 导出成品 DOCX）。
   - **自动化**：一键安全自动批准合规计划，无繁琐确认弹窗打扰。

2. **手动视图：详细与 Agent 智排 (Detailed & Agent-Assisted)**
   - **定位**：攻坚 10% 的复杂疑难格式排版（非标规范红头文件、正文引注转脚注、图表公式交叉引用域代码、附录编号冲突）。
   - **专家能力**：
     - 规范智能推导：根据用户输入文本提取结构化规则包。
     - 深度 OOXML 攻坚：引注转真脚注、`REF`/`SEQ` 域代码动态更新、OMML 公式居中对齐。
     - 交互式段落级 Diff 对比器：修改前 vs 修改后，逐项撤销/授权。
     - AI 盲审二次质检报告：输出学术规范问题与修复建议清单。

---

## 2. 工程目录结构规范

```text
v1.1/
├── AGENTS.md                  # 本工程规范文档
├── PRD.md                     # 产品需求文档
├── ARCHITECTURE_AND_SPECS.md  # 架构技术规范
├── DESIGN.md                  # 设计系统规范
├── README.md                  # 使用与部署说明
├── pyproject.toml             # v1.1 依赖与元数据
├── run.py                     # 一键启动 MVP 脚本 (兼顾命令行与 Web)
├── server/                    # 本地排版后端服务
│   ├── app.py                 # FastAPI 应用入口与 REST 路由
│   ├── engine.py              # 核心排版编译引擎适配层 (基于 paper_setting_core)
│   ├── agent_service.py       # 详细模式 Agent 服务 (规则提取、深层重构、AI 质检)
│   └── presets.py             # 规范预设库 (国标 GB/T 7713.1, 学位论文, 经管模板等)
├── web/                       # 现代化高保真工作台
│   ├── index.html             # 工作台入口 (支持独立 SPA 或静态托管)
│   ├── app.js                 # 双视图 FSM 状态机、Radial Gauge、X-Ray 对比、API 联动
│   └── style.css              # Editorial Minimal 设计规范样式
├── tests/                     # 自动化测试套件
│   ├── test_minimal_flow.py   # 极简离线排版流程测试
│   ├── test_agent_features.py # 详细模式 Agent 规则提取与质检测试
│   └── test_api_endpoints.py  # REST 接口端点测试
└── storage/                   # 本地沙箱会话与生成的 DOCX 成果目录 (.gitignore)
```

---

## 3. 设计规范与视觉契约 (Editorial Tactile Minimal)

依据 `DESIGN.md` 与 Stitch 设计原型：
- **基调色彩**：
  - 画布底色：温暖纸墨色 `--bg-app: #f4f0e6`，渐变背景辅以轻微漫反射。
  - 卡片表面：细腻暖白纸张 `--surface-card: #fffdfa`，边框 `--border-subtle: #e2dcd0`。
  - 品牌翡翠墨绿：`--brand-emerald: #1c5d43`（悬停 `--brand-emerald-hover: #12402e`）。
  - Agent 智能紫色：`--agent-purple: #5b4aa6`（淡紫容器 `--agent-purple-light: #f3f0fd`）。
- **动效体系**：
  - 顶部模式切换：Sliding Indicator 物理弹簧缓动 (`cubic-bezier(0.16, 1, 0.3, 1)`)。
  - 阶段 3 进度展示：SVG Radial Gauge 环形动态进度仪表盘 + 离线绿点脉冲。
  - 阶段 4 成果交付：交互式 X-Ray 透视比对滑块（Before vs After 实时滑动切页）与轻量 Canvas 礼花粒子动效。

---

## 4. 运行与验证指令

- **运行全量 v1.1 测试套件**：
  ```bash
  .venv/bin/pytest v1.1/tests/ -v
  ```
- **启动 v1.1 本地可运行 MVP 服务**：
  ```bash
  .venv/bin/python v1.1/run.py
  ```
- **根工程回归测试**：
  ```bash
  python3 scripts/check.py
  ```
