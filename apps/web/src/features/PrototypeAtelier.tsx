import { useState, useRef, useEffect } from 'react'

interface PrototypeAtelierProps {
  onBackToWorkflow?: () => void
}

export function PrototypeAtelier({ onBackToWorkflow }: PrototypeAtelierProps) {
  const [activeTab, setActiveTab] = useState<'stage' | 'xray' | 'rules' | 'audit'>('xray')
  const [xrayPos, setXrayPos] = useState(52) // percentage 0-100
  const [isDraggingXray, setIsDraggingXray] = useState(false)
  const [activeRuleHighlight, setActiveRuleHighlight] = useState<string | null>('body')
  const [activeFormulaModal, setActiveFormulaModal] = useState(false)
  const [paperZoom, setPaperZoom] = useState(100)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)

  // Handle drag for X-Ray slider
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingXray || !containerRef.current) return
      const rect = containerRef.current.getBoundingClientRect()
      const clientX = e.clientX - rect.left
      const percentage = Math.max(5, Math.min(95, (clientX / rect.width) * 100))
      setXrayPos(percentage)
    }

    const handleMouseUp = () => setIsDraggingXray(false)

    if (isDraggingXray) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDraggingXray])

  return (
    <div className="atelier-root">
      {/* 顶部高端工具栏 */}
      <header className="atelier-header">
        <div className="atelier-brand">
          <div className="brand-badge-wrapper">
            <span className="brand-dot pulse" />
            <span className="brand-title">Paper Setting · 交互原型实验室</span>
            <span className="brand-pill">Atelier v2.4</span>
          </div>
          <span className="atelier-subtitle">高质感物理拟物手稿舞台与 X-Ray 格式透视比对引擎</span>
        </div>

        {/* 核心四个界面的切换胶囊 */}
        <nav className="atelier-nav-tabs" aria-label="原型视窗选择">
          <button
            type="button"
            className={`tab-pill ${activeTab === 'stage' ? 'active' : ''}`}
            onClick={() => setActiveTab('stage')}
          >
            <i>📄</i>
            <span>① A4 拟物手稿舞台</span>
          </button>
          <button
            type="button"
            className={`tab-pill ${activeTab === 'xray' ? 'active' : ''}`}
            onClick={() => setActiveTab('xray')}
          >
            <i>⚡</i>
            <span>② X-Ray 格式透视帘幕</span>
            <span className="hot-tag">Hot</span>
          </button>
          <button
            type="button"
            className={`tab-pill ${activeTab === 'rules' ? 'active' : ''}`}
            onClick={() => setActiveTab('rules')}
          >
            <i>🔬</i>
            <span>③ 规则演变与引线溯源</span>
          </button>
          <button
            type="button"
            className={`tab-pill ${activeTab === 'audit' ? 'active' : ''}`}
            onClick={() => setActiveTab('audit')}
          >
            <i>🛡️</i>
            <span>④ 双重质量门禁报告</span>
          </button>
        </nav>

        {/* 右侧全局操作区 */}
        <div className="atelier-actions">
          <div className="zoom-controller">
            <button
              type="button"
              className="zoom-btn"
              onClick={() => setPaperZoom(z => Math.max(70, z - 10))}
              title="缩小"
            >
              −
            </button>
            <span className="zoom-value">{paperZoom}%</span>
            <button
              type="button"
              className="zoom-btn"
              onClick={() => setPaperZoom(z => Math.min(130, z + 10))}
              title="放大"
            >
              +
            </button>
          </div>
          {onBackToWorkflow && (
            <button type="button" className="action-btn back-btn" onClick={onBackToWorkflow}>
              ← 返回主排版流水线
            </button>
          )}
        </div>
      </header>

      {/* 主展示画布 */}
      <main className="atelier-canvas">
        {/* ======================= 模式 1: A4 拟物手稿舞台 ======================= */}
        {activeTab === 'stage' && (
          <div className="stage-view-wrapper">
            <div className="stage-sidebar-left">
              <div className="bento-panel">
                <div className="panel-title">
                  <span>结构透视树 (AST Outline)</span>
                  <span className="pill-badge">896 段落</span>
                </div>
                <div className="ast-tree">
                  <div className="tree-node heading">
                    <span className="node-icon">H1</span>
                    <span className="node-text">第 1 章 绪论与研究背景</span>
                    <span className="node-status pass">✓</span>
                  </div>
                  <div className="tree-node sub">
                    <span className="node-icon">H2</span>
                    <span className="node-text">1.1 中文学位论文排版现状</span>
                    <span className="node-status pass">✓</span>
                  </div>
                  <div className="tree-node body active">
                    <span className="node-icon">¶</span>
                    <span className="node-text">正文：现存排版痛点与规范分析</span>
                    <span className="node-status pass">1.5倍</span>
                  </div>
                  <div className="tree-node formula" onClick={() => setActiveFormulaModal(true)}>
                    <span className="node-icon">∑</span>
                    <span className="node-text">公式 1-1 (牛顿第二定律)</span>
                    <span className="node-status warn">🔒 锁定</span>
                  </div>
                  <div className="tree-node table">
                    <span className="node-icon">田</span>
                    <span className="node-text">表 1-1 各高校排版边距对比</span>
                    <span className="node-status pass">三线表</span>
                  </div>
                  <div className="tree-node sub">
                    <span className="node-icon">H2</span>
                    <span className="node-text">1.2 论文编译架构设计目标</span>
                    <span className="node-status pass">✓</span>
                  </div>
                </div>
              </div>

              <div className="bento-panel warning-box">
                <div className="panel-title">
                  <span className="amber-text">高危对象锁定中</span>
                  <span className="warn-badge">18 处公式</span>
                </div>
                <p className="panel-desc">
                  OpenXML 字节保护已开启。公式内部 XML 拓扑结构只读保护，字偶间距与希腊字符集已锁定。
                </p>
                <button
                  type="button"
                  className="examine-btn"
                  onClick={() => setActiveFormulaModal(true)}
                >
                  查看公式安全隔离舱 ➔
                </button>
              </div>
            </div>

            {/* A4 虚拟手稿容器 */}
            <div className="stage-paper-center">
              <div
                className="a4-sheet-container"
                style={{ transform: `scale(${paperZoom / 100})` }}
              >
                {/* 顶栏标尺刻度 */}
                <div className="paper-ruler-h">
                  <div className="ruler-margin-guide left" style={{ width: '30mm' }}>
                    <span>左边距 30mm</span>
                  </div>
                  <div className="ruler-ticks-track" />
                  <div className="ruler-margin-guide right" style={{ width: '25mm' }}>
                    <span>右边距 25mm</span>
                  </div>
                </div>

                {/* 真实 A4 纸张页面 */}
                <article className="a4-page-sheet">
                  {/* 页眉区 */}
                  <div className="a4-header-zone">
                    <span className="header-text">清华大学硕士学位论文</span>
                    <span className="header-chap">第 1 章 绪论</span>
                    <div className="header-rule" />
                  </div>

                  {/* 标题 */}
                  <div className="doc-h1">
                    <h1 className="h1-text">第 1 章 绪 论</h1>
                    <span className="style-inspector-chip">黑体 · 三号 · 居中 · 段前12pt</span>
                  </div>

                  {/* 二级标题 */}
                  <div className="doc-h2">
                    <h2 className="h2-text">1.1 学位论文格式规范与排版自动化挑战</h2>
                    <span className="style-inspector-chip">黑体 · 四号 · 居左 · 段前6pt</span>
                  </div>

                  {/* 正文段落 1 */}
                  <p
                    className={`doc-body-p ${hoveredNode === 'p1' ? 'inspected' : ''}`}
                    onMouseEnter={() => setHoveredNode('p1')}
                    onMouseLeave={() => setHoveredNode(null)}
                  >
                    研究生学位论文是研究生科研成果与学术素养的综合呈现。随着我国高校研究生招生规模的逐年递增，学位论文的质量把控要求愈发严格。全国各大高校对于学位论文的排版规范具有高度严格的细则要求，涵盖了页面边距、中英文字体分流、多倍与固定行距、三线表规范、动态编号目录及页眉页脚奇偶分节等繁冗细节。
                    {hoveredNode === 'p1' && (
                      <span className="floating-probe">
                        <i>[正文] 宋体/Times New Roman · 小四(12pt) · 首行缩进2字符 · 1.5倍行距</i>
                      </span>
                    )}
                  </p>

                  {/* 公式展示 */}
                  <div
                    className="doc-formula-box"
                    onClick={() => setActiveFormulaModal(true)}
                    title="点击打开公式安全隔离舱"
                  >
                    <div className="formula-content">
                      <span className="formula-math">
                        {'E = mc² + ∫₀^∞ [ħω / (e^(ħω/k_B T) - 1)] dω'}
                      </span>
                      <span className="formula-num">(1-1)</span>
                    </div>
                    <span className="formula-protect-badge">🔒 OMML 结构锁定 · Cambria Math</span>
                  </div>

                  {/* 正文段落 2 */}
                  <p className="doc-body-p">
                    传统排版主要依赖人工在文字处理软件中逐项调整，不仅繁琐耗时，且容易因宏定义失效或样式链式污染导致版式崩坏。基于大语言模型与确定性排版引擎的分层协同机制，可以在规避大模型格式幻觉的同时，实现长文档毫秒级的严谨规范对齐。
                  </p>

                  {/* 三线表规范 */}
                  <div className="doc-table-wrapper">
                    <div className="table-caption">表 1-1 各高校学位论文典型格式参数对照表</div>
                    <table className="three-line-table">
                      <thead>
                        <tr>
                          <th>高校分类</th>
                          <th>正文字体要求</th>
                          <th>行距模式</th>
                          <th>分节页码规范</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>工科重点高校 A</td>
                          <td>宋体 / Times New Roman (小四)</td>
                          <td>固定值 20 磅</td>
                          <td>前置页罗马/正文阿拉伯</td>
                        </tr>
                        <tr>
                          <td>综合类重点高校 B</td>
                          <td>宋体 (小四) / Arial (12pt)</td>
                          <td>多倍行距 1.5 倍</td>
                          <td>每章独立重启页眉</td>
                        </tr>
                        <tr>
                          <td>理工重点高校 C</td>
                          <td>仿宋 (小四) / Cambria (12pt)</td>
                          <td>最小值 22 磅</td>
                          <td>奇偶页眉不同</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* 页脚区 */}
                  <div className="a4-footer-zone">
                    <div className="footer-rule" />
                    <span className="page-number">- 1 -</span>
                  </div>
                </article>
              </div>
            </div>

            {/* 右侧属性检查面板 */}
            <div className="stage-sidebar-right">
              <div className="bento-panel">
                <div className="panel-title">
                  <span>实时排版参数监视</span>
                  <span className="active-pill">对齐中</span>
                </div>
                <div className="param-grid">
                  <div className="param-cell">
                    <span className="param-label">中文字体</span>
                    <strong className="param-value">宋体 (SimSun)</strong>
                  </div>
                  <div className="param-cell">
                    <span className="param-label">西文字体</span>
                    <strong className="param-value">Times New Roman</strong>
                  </div>
                  <div className="param-cell">
                    <span className="param-label">字号 / 磅值</span>
                    <strong className="param-value">小四 (12.0 pt)</strong>
                  </div>
                  <div className="param-cell">
                    <span className="param-label">行距模式</span>
                    <strong className="param-value highlight">1.5 倍 (multiple)</strong>
                  </div>
                  <div className="param-cell">
                    <span className="param-label">首行缩进</span>
                    <strong className="param-value">2.0 字符 (24.0 pt)</strong>
                  </div>
                  <div className="param-cell">
                    <span className="param-label">段前 / 段后</span>
                    <strong className="param-value">0.0 pt / 0.0 pt</strong>
                  </div>
                </div>
              </div>

              <div className="bento-panel">
                <div className="panel-title">
                  <span>OpenXML 差异推演</span>
                  <span className="pill-badge">v1.02</span>
                </div>
                <div className="xml-preview-code">
                  <code>
                    &lt;w:pPr&gt;<br />
                    &nbsp;&nbsp;&lt;w:spacing w:line=&quot;360&quot; w:lineRule=&quot;auto&quot;/&gt;<br />
                    &nbsp;&nbsp;&lt;w:ind w:firstLineChars=&quot;200&quot;/&gt;<br />
                    &nbsp;&nbsp;&lt;w:jc w:val=&quot;both&quot;/&gt;<br />
                    &lt;/w:pPr&gt;
                  </code>
                </div>
                <div className="safety-guarantee">
                  <span className="shield-icon">🛡️</span>
                  <span>确定性算子直接修改 AST 树，不改变文本字符</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======================= 模式 2: X-Ray 格式透视比对帘幕 (作品集杀手锏) ======================= */}
        {activeTab === 'xray' && (
          <div className="xray-workbench" ref={containerRef}>
            {/* 顶栏操作提示 */}
            <div className="xray-control-banner">
              <div className="banner-left">
                <span className="drag-hint-badge">↔ 按住鼠标左右拖动帘幕</span>
                <span className="banner-text">
                  实时对比「左侧：原始杂乱手稿」与「右侧：确定性编译终稿」
                </span>
              </div>
              <div className="banner-right">
                <span className="split-readout">当前透视位点: {Math.round(xrayPos)}%</span>
                <button
                  type="button"
                  className="quick-split-btn"
                  onClick={() => setXrayPos(50)}
                >
                  对半重置 (50%)
                </button>
              </div>
            </div>

            {/* 双层透视画卷 */}
            <div className="xray-stage-viewport">
              <div className="xray-sheet-frame">
                {/* 底层：标准排版终稿 (右侧/基底) */}
                <div className="sheet-layer clean-version">
                  <div className="layer-tag success-tag">确定性编译终稿 (Compiled Standard ✓)</div>

                  <div className="a4-header-zone">
                    <span className="header-text">清华大学硕士学位论文</span>
                    <span className="header-chap">第 1 章 绪论</span>
                    <div className="header-rule" />
                  </div>

                  <h1 className="clean-h1">第 1 章 绪 论</h1>
                  <h2 className="clean-h2">1.1 学位论文格式规范与排版自动化挑战</h2>

                  <p className="clean-p">
                    研究生学位论文是研究生科研成果与学术素养的综合呈现。随着我国高校研究生招生规模的逐年递增，学位论文的质量把控要求愈发严格。各大高校对于学位论文排版具有高度严苛细则要求，涵盖页面边距、中英文字体分流、多倍与固定行距、三线表规范、动态编号目录及页眉页脚奇偶分节等繁冗细节。
                  </p>

                  <div className="clean-formula-block">
                    <div className="math-expr">
                      {'∇ × E⃗ = -∂B⃗/∂t,   ∇ · D⃗ = ρ'}
                    </div>
                    <span className="clean-formula-tag">(1-1)</span>
                  </div>

                  <p className="clean-p">
                    传统排版主要依赖人工逐项调整，不仅耗时数日，且容易因样式链式污染导致版式崩坏。基于大语言模型与确定性排版引擎的分层协同机制，可以在彻底规避大模型格式幻觉的同时，实现长文档毫秒级的严谨规范对齐。
                  </p>

                  <div className="clean-table-block">
                    <div className="table-caption">表 1-1 国标三线表规范对齐效果</div>
                    <table className="three-line-table">
                      <thead>
                        <tr>
                          <th>指标项</th>
                          <th>人工排版</th>
                          <th>确定性排版台</th>
                          <th>改进幅度</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td>平均耗时</td>
                          <td>3~5 个工作日</td>
                          <td>1.42 秒</td>
                          <td>提速 99.8%</td>
                        </tr>
                        <tr>
                          <td>公式损坏率</td>
                          <td>约 14.5%</td>
                          <td>0.0% (零损坏)</td>
                          <td>绝对保全</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  <div className="a4-footer-zone">
                    <div className="footer-rule" />
                    <span className="page-number">- 1 -</span>
                  </div>
                </div>

                {/* 顶层：原始乱码手稿 (左侧/由 CSS clip-path 裁切) */}
                <div
                  className="sheet-layer raw-version"
                  style={{ clipPath: `polygon(0 0, ${xrayPos}% 0, ${xrayPos}% 100%, 0 100%)` }}
                >
                  <div className="layer-tag warning-tag">原始乱七八糟手稿 (Raw Manuscript ⚠)</div>

                  <div className="a4-header-zone raw-header">
                    <span className="raw-header-text">清华大学论文（无下划线、字体缺失）</span>
                  </div>

                  {/* 凌乱标题 */}
                  <h1 className="raw-h1">第一章 绪论 (字号偏小、宋体未加粗、行距单倍)</h1>
                  <h2 className="raw-h2">1.1 学位论文格式规范（西文全角混杂）</h2>

                  {/* 凌乱正文 */}
                  <p className="raw-p">
                    研究生学位论文是研究生科研成果与学术素养的综合呈现。随着我国高校研究生招生规模的逐年递增，学位论文的质量把控要求愈发严格。各大高校对于学位论文排版具有高度严苛细则要求，涵盖页面边距、中英文字体分流、多倍与固定行距、三线表规范、动态编号目录及页眉页脚奇偶分节等繁冗细节。
                    <span className="raw-lint-tag">⚠ 缺少首行缩进 · 单倍行距过密 · 仿宋乱入</span>
                  </p>

                  {/* 变形公式 */}
                  <div className="raw-formula-block">
                    <div className="raw-math">E=mc2 + ∫ \hbar \omega ... (公式基线歪斜、西文字体未统一)</div>
                    <span className="raw-lint-tag formula">⚠ 公式未居中 · 缺少右对齐编号</span>
                  </div>

                  <p className="raw-p">
                    传统排版主要依赖人工逐项调整，不仅耗时数日，且容易因样式链式污染导致版式崩坏。基于大语言模型与确定性排版引擎的分层协同机制，可以在彻底规避大模型格式幻觉的同时，实现长文档毫秒级的严谨规范对齐。
                  </p>

                  {/* 粗黑全框线丑陋表格 */}
                  <div className="raw-table-block">
                    <div className="raw-caption">表格1: 人工与系统对比 (非标准表头)</div>
                    <table className="ugly-grid-table">
                      <tbody>
                        <tr>
                          <td>指标项</td>
                          <td>人工排版</td>
                          <td>确定性排版台</td>
                          <td>改进幅度</td>
                        </tr>
                        <tr>
                          <td>平均耗时</td>
                          <td>3~5天</td>
                          <td>1.42s</td>
                          <td>快</td>
                        </tr>
                        <tr>
                          <td>公式损坏</td>
                          <td>经常丢</td>
                          <td>0</td>
                          <td>好</td>
                        </tr>
                      </tbody>
                    </table>
                    <span className="raw-lint-tag table">⚠ 丑陋粗黑全框线 · 缺少表头规范</span>
                  </div>

                  <div className="a4-footer-zone raw-footer">
                    <span className="raw-page">第 1 页 (未居中、字体宋体)</span>
                  </div>
                </div>

                {/* 可拖动物理滑块分割线 */}
                <div
                  className="xray-divider"
                  style={{ left: `${xrayPos}%` }}
                  onMouseDown={() => setIsDraggingXray(true)}
                >
                  <div className="divider-line" />
                  <div className="divider-handle">
                    <span className="handle-chevron">◀</span>
                    <span className="handle-dot" />
                    <span className="handle-chevron">▶</span>
                  </div>
                  <div className="divider-beacon" />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======================= 模式 3: 规则演变与引线溯源 ======================= */}
        {activeTab === 'rules' && (
          <div className="rules-laboratory-view">
            {/* 左侧：高校红头规范原文卡片 */}
            <div className="rules-source-card">
              <div className="card-badge">
                <span className="badge-source">高校红头文件规范 · 自然语言原文</span>
                <span className="badge-meta">清华大学研究生排版规范 (2024年版)</span>
              </div>
              <div className="source-prose-box">
                <p className="prose-line">
                  <strong>一、页面规格与版心要求：</strong>
                </p>
                <p
                  className={`prose-line selectable ${activeRuleHighlight === 'margin' ? 'highlighted' : ''}`}
                  onClick={() => setActiveRuleHighlight('margin')}
                >
                  论文一律采用国际标准 A4 纸张双面印刷。版芯上下边距各为 2.5 厘米，左边距为 3.0 厘米，右边距为 2.5 厘米。页眉距边界 1.5 厘米，页脚距边界 1.75 厘米。
                </p>
                <p className="prose-line">
                  <strong>二、文稿字体与段落行距：</strong>
                </p>
                <p
                  className={`prose-line selectable ${activeRuleHighlight === 'body' ? 'highlighted' : ''}`}
                  onClick={() => setActiveRuleHighlight('body')}
                >
                  正文采用小四号宋体字，西文字体及数字均采用 Times New Roman。首行缩进 2 字符，段落行距采用 1.5 倍多倍行距。段前段后均不设间距。两端对齐。
                </p>
                <p
                  className={`prose-line selectable ${activeRuleHighlight === 'heading1' ? 'highlighted' : ''}`}
                  onClick={() => setActiveRuleHighlight('heading1')}
                >
                  第一级标题（章标题）采用三号黑体字，加粗，居中排版。段前空 12 磅，段后空 6 磅。每章必须另起一页排版（段前分页）。
                </p>
                <p
                  className={`prose-line selectable ${activeRuleHighlight === 'notes' ? 'highlighted' : ''}`}
                  onClick={() => setActiveRuleHighlight('notes')}
                >
                  全篇引文与注释一律采用页下脚注，文末不列参考文献区。脚注编号采用带圈数字，且每页重新从 1 开始编号。
                </p>
              </div>
            </div>

            {/* 中间：光纤引线与处理管道 */}
            <div className="rules-pipe-column">
              <div className="pipe-beacon-box">
                <div className="pipe-arrow">➔ ➔ ➔</div>
                <span className="pipe-label">LLM 概率抽取</span>
                <span className="pipe-sub">提取置信度 0.99</span>
                <div className="laser-trace-line" />
              </div>
            </div>

            {/* 右侧：结构化 RulePack 属性舱 */}
            <div className="rules-spec-card">
              <div className="card-badge">
                <span className="badge-target">标准化 RulePack JSON 规则契约</span>
                <span className="badge-version">Schema v2.1 (确定性编译就绪)</span>
              </div>

              <div className="rulepack-item-grid">
                <div
                  className={`rule-spec-item ${activeRuleHighlight === 'margin' ? 'focused' : ''}`}
                  onClick={() => setActiveRuleHighlight('margin')}
                >
                  <div className="spec-header">
                    <span className="spec-key">page_setup</span>
                    <span className="spec-tag">页面边距</span>
                  </div>
                  <div className="spec-body">
                    <code>
                      margin_top_mm: 25.0<br />
                      margin_bottom_mm: 25.0<br />
                      margin_left_mm: 30.0<br />
                      margin_right_mm: 25.0
                    </code>
                  </div>
                  <span className="trace-anchor">已锚定原文证据 ✓</span>
                </div>

                <div
                  className={`rule-spec-item ${activeRuleHighlight === 'body' ? 'focused' : ''}`}
                  onClick={() => setActiveRuleHighlight('body')}
                >
                  <div className="spec-header">
                    <span className="spec-key">roles.body</span>
                    <span className="spec-tag">正文段落</span>
                  </div>
                  <div className="spec-body">
                    <code>
                      east_asia_font: &quot;宋体&quot;<br />
                      latin_font: &quot;Times New Roman&quot;<br />
                      font_size_pt: 12.0 (小四)<br />
                      line_spacing: 1.5 (multiple)<br />
                      first_line_indent_pt: 24.0 (2字符)
                    </code>
                  </div>
                  <span className="trace-anchor">已锚定原文证据 ✓</span>
                </div>

                <div
                  className={`rule-spec-item ${activeRuleHighlight === 'heading1' ? 'focused' : ''}`}
                  onClick={() => setActiveRuleHighlight('heading1')}
                >
                  <div className="spec-header">
                    <span className="spec-key">roles.heading_1</span>
                    <span className="spec-tag">一级标题</span>
                  </div>
                  <div className="spec-body">
                    <code>
                      east_asia_font: &quot;黑体&quot;<br />
                      font_size_pt: 16.0 (三号加粗)<br />
                      alignment: &quot;center&quot;<br />
                      page_break_before: true
                    </code>
                  </div>
                  <span className="trace-anchor">已锚定原文证据 ✓</span>
                </div>

                <div
                  className={`rule-spec-item ${activeRuleHighlight === 'notes' ? 'focused' : ''}`}
                  onClick={() => setActiveRuleHighlight('notes')}
                >
                  <div className="spec-header">
                    <span className="spec-key">advanced.notes</span>
                    <span className="spec-tag">深层脚注转换</span>
                  </div>
                  <div className="spec-body">
                    <code>
                      convert_endnotes: true<br />
                      numbering_restart: &quot;per_page&quot;<br />
                      number_format: &quot;circled_decimal&quot;<br />
                      delete_bibliography: true
                    </code>
                  </div>
                  <span className="trace-anchor">已锚定原文证据 ✓</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ======================= 模式 4: 双重质量门禁报告 ======================= */}
        {activeTab === 'audit' && (
          <div className="audit-terminal-view">
            {/* 顶栏四联 KPI 看板 (MotionSites 风格) */}
            <div className="kpi-bento-row">
              <div className="kpi-card emerald-glow">
                <div className="kpi-title">格式合规达标率</div>
                <div className="kpi-number">99.4%</div>
                <div className="kpi-meta">428 / 430 项规则原子通过</div>
              </div>
              <div className="kpi-card teal-glow">
                <div className="kpi-title">文本一致性校验</div>
                <div className="kpi-number">100.0%</div>
                <div className="kpi-meta">64,280 / 64,280 字符精准一致 (零损耗)</div>
              </div>
              <div className="kpi-card amber-glow">
                <div className="kpi-title">嵌入部件保全率</div>
                <div className="kpi-number">18/18 公式</div>
                <div className="kpi-meta">14/14 图片 · 3/3 复杂表格拓扑保全</div>
              </div>
              <div className="kpi-card purple-glow">
                <div className="kpi-title">原子编译吞吐性能</div>
                <div className="kpi-number">1.42s</div>
                <div className="kpi-meta">内存快速 Patch · 120 页/秒吞吐</div>
              </div>
            </div>

            {/* 双栏审计报告 */}
            <div className="audit-details-split">
              {/* 左侧：确定性证书 */}
              <div className="certificate-card">
                <div className="cert-header">
                  <div className="cert-seal">合格</div>
                  <div className="cert-title-group">
                    <h3>学位论文排版合格评议证书</h3>
                    <span className="cert-id">防伪哈希: 7f2a890c-33b1-49e8-b80c</span>
                  </div>
                </div>

                <div className="cert-items-list">
                  <div className="cert-row">
                    <span className="row-check">✓</span>
                    <span className="row-label">A4 页面边距与版心尺寸校验</span>
                    <span className="row-value">符合 GB/T 7714-2015</span>
                  </div>
                  <div className="cert-row">
                    <span className="row-check">✓</span>
                    <span className="row-label">中西文字体分流与字号继承</span>
                    <span className="row-value">宋体 + Times New Roman</span>
                  </div>
                  <div className="cert-row">
                    <span className="row-check">✓</span>
                    <span className="row-label">段落多倍行距精确换算</span>
                    <span className="row-value">1.5 倍 (360 dxa)</span>
                  </div>
                  <div className="cert-row">
                    <span className="row-check">✓</span>
                    <span className="row-label">分节与页码重启验证</span>
                    <span className="row-value">前置 Roman / 正文 Arabic</span>
                  </div>
                  <div className="cert-row">
                    <span className="row-check">✓</span>
                    <span className="row-label">Word 可重开性与部件哈希自检</span>
                    <span className="row-value">Pass (零损坏风险)</span>
                  </div>
                </div>

                <div className="cert-footer">
                  <span>签发机构: 本地学术排版沙箱引擎 (Local Loopback)</span>
                  <button type="button" className="download-cert-btn">
                    下载 HTML 审计证明 ⭳
                  </button>
                </div>
              </div>

              {/* 右侧：只读 Agent 质检清单 */}
              <div className="agent-qa-card">
                <div className="qa-header">
                  <span className="qa-badge">AI 质检 Agent 二次学术复核</span>
                  <span className="qa-meta">只读权限 · 不动文档 · 仅提建议</span>
                </div>

                <div className="qa-finding-box warning">
                  <div className="finding-title">
                    <span>⚠ 交叉引用错位预警 (Cross-Reference Discrepancy)</span>
                    <span className="page-pill">第 14 页</span>
                  </div>
                  <p className="finding-text">
                    正文第 14 页第 2 段提及“...详细收敛曲线见表 2-3...”，但其后紧邻的表格题注编号实际为“表 2-4 (各模型收敛对比)”。
                  </p>
                  <div className="finding-action">
                    <strong>建议：</strong>
                    检查第 13 页是否遗留了已删表格，或在工作台中启用「自动交叉引用 SEQ 域」。
                  </div>
                </div>

                <div className="qa-finding-box info">
                  <div className="finding-title">
                    <span>ℹ 参考文献规范性建议</span>
                    <span className="page-pill">第 62 页</span>
                  </div>
                  <p className="finding-text">
                    参考文献 [12] “Vaswani A, et al. Attention is all you need” 缺少出版刊物卷号或页码范围。
                  </p>
                  <div className="finding-action">
                    <strong>建议：</strong>已保留原文本，建议在盲审前补齐期刊卷期。
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ======================= OMML 公式透明安全舱 (弹窗) ======================= */}
      {activeFormulaModal && (
        <div className="modal-backdrop" onClick={() => setActiveFormulaModal(false)}>
          <div className="capsule-modal" onClick={e => e.stopPropagation()}>
            <div className="capsule-header">
              <div className="capsule-title">
                <span className="shield-icon">🛡️</span>
                <h3>OMML 数学公式安全隔离舱 (OpenXML Security Capsule)</h3>
              </div>
              <button
                type="button"
                className="close-modal-btn"
                onClick={() => setActiveFormulaModal(false)}
              >
                ✕
              </button>
            </div>

            <div className="capsule-body">
              <div className="capsule-alert">
                <strong>为什么严禁大语言模型直接重写此公式？</strong>
                <p>
                  公式内部由 Office OpenXML 的 <code>&lt;m:oMath&gt;</code>、<code>&lt;m:rad&gt;</code>、<code>&lt;m:f&gt;</code> 树状节点严格组织。LLM 端到端生成会导致上下标位置断裂、希腊符号变成问号。排版台采取确定性锁定，仅统一公式外部西文字体为 Cambria Math，内部拓扑一字不改。
                </p>
              </div>

              <div className="capsule-xml-box">
                <div className="xml-tag">锁定 OpenXML 拓扑结构：</div>
                <pre>
{`<m:oMathPara>
  <m:oMath>
    <m:r>
      <m:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></m:rPr>
      <m:t>E</m:t>
    </m:r>
    <m:r><m:t>=</m:t></m:r>
    <m:r><m:t>m</m:t></m:r>
    <m:sSup>
      <m:e><m:r><m:t>c</m:t></m:r></m:e>
      <m:sup><m:r><m:t>2</m:t></m:r></m:sup>
    </m:sSup>
  </m:oMath>
</m:oMathPara>`}
                </pre>
              </div>

              <div className="capsule-status-row">
                <span className="status-item">✓ 拓扑完整性: 100% 吻合</span>
                <span className="status-item">✓ 基线对齐: 居中</span>
                <span className="status-item">✓ 右侧编号域: (1-1)</span>
              </div>
            </div>

            <div className="capsule-footer">
              <button
                type="button"
                className="primary-confirm-btn"
                onClick={() => setActiveFormulaModal(false)}
              >
                已知晓并保持安全锁定
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
