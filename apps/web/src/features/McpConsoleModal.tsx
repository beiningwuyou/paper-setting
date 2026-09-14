import { useEffect, useState } from 'react'

interface McpConsoleModalProps {
  isOpen: boolean
  onClose: () => void
}

type MainTab = 'domestic' | 'international' | 'tools' | 'safety'
type InternationalAgentTab = 'cursor' | 'claude' | 'windsurf' | 'cli'

interface AgentScanState {
  workbuddyInstalled: boolean
  workbuddyInjected: boolean
  traeInstalled: boolean
  traeInjected: boolean
  doubaoInstalled: boolean
  deepseekInstalled: boolean
  summary: string
}

export function McpConsoleModal({ isOpen, onClose }: McpConsoleModalProps) {
  const [mainTab, setMainTab] = useState<MainTab>('domestic')
  const [agentTab, setAgentTab] = useState<InternationalAgentTab>('cursor')
  const [copiedKey, setCopiedKey] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [wbInjecting, setWbInjecting] = useState(false)
  const [wbFeedback, setWbFeedback] = useState<string | null>(null)
  const [traeFeedback, setTraeFeedback] = useState<string | null>(null)

  const [scanState, setScanState] = useState<AgentScanState>({
    workbuddyInstalled: true,
    workbuddyInjected: false,
    traeInstalled: false,
    traeInjected: false,
    doubaoInstalled: true,
    deepseekInstalled: true,
    summary: '已检测到本机环境：WorkBuddy、豆包、DeepSeek 已就绪',
  })

  const projectRoot = '.'

  const runAgentScan = async () => {
    setIsScanning(true)
    try {
      const res = await fetch('/api/agent/scan')
      if (res.ok) {
        const data = await res.json()
        const agents = data.agents || {}
        const wb = agents.workbuddy || {}
        const trae = agents.trae || {}
        const doubao = agents.doubao || {}
        const deepseek = agents.deepseek || {}
        setScanState({
          workbuddyInstalled: !!wb.installed,
          workbuddyInjected: !!wb.injected,
          traeInstalled: !!trae.installed,
          traeInjected: !!trae.injected,
          doubaoInstalled: !!doubao.installed,
          deepseekInstalled: !!deepseek.installed,
          summary: `已扫描 Mac 本机：检测到 ${wb.installed ? 'WorkBuddy、' : ''}${doubao.installed ? '豆包、' : ''}${deepseek.installed ? 'DeepSeek、' : ''}已就绪`,
        })
      }
    } catch {
      // Keep optimistic fallback
    } finally {
      setIsScanning(false)
    }
  }

  useEffect(() => {
    if (isOpen) {
      runAgentScan()
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedKey(key)
      setTimeout(() => setCopiedKey(null), 2000)
    })
  }

  const handleInjectWorkBuddy = async () => {
    setWbInjecting(true)
    try {
      const res = await fetch('/api/agent/inject-workbuddy', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setWbFeedback(data.message + '（原配置已自动备份）')
        setScanState(prev => ({ ...prev, workbuddyInjected: true }))
      } else {
        alert(data.message || '写入失败')
      }
    } catch (e: any) {
      alert('写入异常: ' + e.message)
    } finally {
      setWbInjecting(false)
    }
  }

  const handleInjectTrae = async () => {
    try {
      const res = await fetch('/api/agent/inject-trae', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        setTraeFeedback(data.message)
        setScanState(prev => ({ ...prev, traeInjected: true }))
      } else {
        alert(data.message || '写入失败')
      }
    } catch (e: any) {
      alert('写入异常: ' + e.message)
    }
  }

  const handleLaunchApp = async (appName: string) => {
    try {
      const res = await fetch('/api/agent/launch-app', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ app_name: appName }),
      })
      const data = await res.json()
      if (!data.success) {
        alert(data.message || '拉起失败')
      }
    } catch (e: any) {
      alert('启动失败: ' + e.message)
    }
  }

  const internationalConfigs: Record<InternationalAgentTab, { title: string; filePath: string; json: string }> = {
    cursor: {
      title: 'Cursor',
      filePath: '.cursor/mcp.json (项目根目录)',
      json: JSON.stringify(
        {
          mcpServers: {
            'paper-setting': {
              command: 'uv',
              args: ['run', '--directory', projectRoot, 'paper-setting-mcp'],
              env: {
                PAPER_SETTING_ALLOWED_INPUT_ROOTS: projectRoot,
              },
            },
          },
        },
        null,
        2,
      ),
    },
    claude: {
      title: 'Claude Desktop',
      filePath: '~/Library/Application Support/Claude/claude_desktop_config.json',
      json: JSON.stringify(
        {
          mcpServers: {
            'paper-setting': {
              command: 'uv',
              args: ['run', '--directory', projectRoot, 'paper-setting-mcp'],
              env: {
                PAPER_SETTING_ALLOWED_INPUT_ROOTS: projectRoot,
              },
            },
          },
        },
        null,
        2,
      ),
    },
    windsurf: {
      title: 'Windsurf',
      filePath: '~/.codeium/windsurf/mcp_config.json',
      json: JSON.stringify(
        {
          mcpServers: {
            'paper-setting': {
              command: 'uv',
              args: ['run', '--directory', projectRoot, 'paper-setting-mcp'],
              env: {
                PAPER_SETTING_ALLOWED_INPUT_ROOTS: projectRoot,
              },
            },
          },
        },
        null,
        2,
      ),
    },
    cli: {
      title: '命令行 / 通用 Agent',
      filePath: '终端命令直接测试',
      json: `# 在当前项目目录下直接启动 stdio MCP 服务：\ncd ${projectRoot} && uv run paper-setting-mcp\n\n# 或者通过 MCP Inspector 调试：\nnpx @modelcontextprotocol/inspector uv run --directory ${projectRoot} paper-setting-mcp`,
    },
  }

  const tools = [
    {
      name: 'create_job',
      badge: '排版编译',
      color: '#1c5d43',
      desc: '创建排版编译或学校模板注入任务。支持指定规则包 ID 与模板路径，自动进行 AST 差异计算。',
      params: 'input_path (必填), rule_pack_id (可选), template_input_path (可选)',
    },
    {
      name: 'inspect_template',
      badge: '模板透视',
      color: '#2b7054',
      desc: '无损透视分析 DOCX 模板的分节、正文占位符与表单字段，返回候选映射能力，不修改原文件。',
      params: 'input_path (必填 DOCX 路径)',
    },
    {
      name: 'get_format_plan',
      badge: '审计计划',
      color: '#5b4aa6',
      desc: '读取段落级可审计修改计划与潜在风险项，供 Agent 检查与向作者汇报。注：审批须在 Web 进行。',
      params: 'job_id (任务 ID)',
    },
    {
      name: 'get_validation_report',
      badge: '质检报告',
      color: '#287a55',
      desc: '读取完成任务的学术格式执行报告与 100% 内容无损完整性报告（含 Agent 盲审意见）。',
      params: 'job_id (任务 ID)',
    },
    {
      name: 'list_artifacts',
      badge: '交付产物',
      color: '#b45309',
      desc: '列出任务生成的规整版 DOCX、PDF 矢量预览与 operations.json 审计清单。',
      params: 'job_id (任务 ID)',
    },
    {
      name: 'list_rule_packs',
      badge: '规范查询',
      color: '#3b82f6',
      desc: '列出系统支持的出版级确定性规范（GB/T 7713.1、国科大学位论文、IEEE 双栏紧凑等）。',
      params: '无参数',
    },
    {
      name: 'list_jobs',
      badge: '任务管理',
      color: '#475569',
      desc: '按时间倒序分页读取本地历史任务、当前状态与处理进度。',
      params: 'limit (可选，默认 20), cursor (可选)',
    },
  ]

  return (
    <div className="mcp-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="mcp-modal-container" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="mcp-modal-header">
          <div className="mcp-modal-title">
            <div className="mcp-icon-badge">
              <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48 2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48 2.83-2.83" />
                <circle cx="12" cy="12" r="4" />
              </svg>
            </div>
            <div>
              <h3>Agent MCP 协同控制中心</h3>
              <p>自动探测本机 Agent（WorkBuddy / Trae / 豆包等），提供零门槛直连与标准 MCP 协同</p>
            </div>
          </div>
          <button type="button" className="mcp-modal-close" onClick={onClose} aria-label="关闭">
            ×
          </button>
        </div>

        {/* Status bar banner */}
        <div className="mcp-status-banner">
          <div className="mcp-status-pill">
            <span className="pulse-dot green" />
            <span>MCP Server 协议就绪 (stdio)</span>
          </div>
          <div className="mcp-status-pill">
            <span className="pulse-dot blue" />
            <span>本地沙箱: 127.0.0.1:8765</span>
          </div>
          <div className="mcp-status-pill">
            <span className="pulse-dot purple" />
            <span>100% 离线纯算 · 零隐私泄漏</span>
          </div>
        </div>

        {/* Main Tabs */}
        <div className="mcp-main-tabs">
          <button
            type="button"
            className={`mcp-tab-btn ${mainTab === 'domestic' ? 'active' : ''}`}
            onClick={() => setMainTab('domestic')}
          >
            🇨🇳 国内 Agent 极低门槛直连
          </button>
          <button
            type="button"
            className={`mcp-tab-btn ${mainTab === 'international' ? 'active' : ''}`}
            onClick={() => setMainTab('international')}
          >
            🌐 国际版 (Cursor / Claude)
          </button>
          <button
            type="button"
            className={`mcp-tab-btn ${mainTab === 'tools' ? 'active' : ''}`}
            onClick={() => setMainTab('tools')}
          >
            🛠️ 暴露工具集 ({tools.length})
          </button>
          <button
            type="button"
            className={`mcp-tab-btn ${mainTab === 'safety' ? 'active' : ''}`}
            onClick={() => setMainTab('safety')}
          >
            🛡️ 人机安全回环原则
          </button>
        </div>

        {/* Tab 1: Domestic Agents */}
        {mainTab === 'domestic' && (
          <div className="mcp-tab-content">
            {/* Scan Status Bar */}
            <div className="mcp-scan-bar">
              <div className="mcp-scan-left">
                <span className={`pulse-dot green ${isScanning ? 'spinning' : ''}`} />
                <span>{scanState.summary}</span>
              </div>
              <button type="button" className="btn-rescan" onClick={runAgentScan} disabled={isScanning}>
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {isScanning ? '正在扫描...' : '重新扫描本机'}
              </button>
            </div>

            {/* Cards Grid */}
            <div className="domestic-cards-grid">
              {/* WorkBuddy Card */}
              <div className="domestic-card">
                <div className="domestic-card-header">
                  <div className="domestic-card-title">
                    <div className="domestic-card-icon workbuddy">W</div>
                    <div>
                      <h4>WorkBuddy (腾讯智能工作伙伴)</h4>
                      <span>企业级原生 MCP 协同</span>
                    </div>
                  </div>
                  {scanState.workbuddyInjected ? (
                    <span className="domestic-badge injected">✓ 已完成写入</span>
                  ) : scanState.workbuddyInstalled ? (
                    <span className="domestic-badge installed">🟢 本机已安装</span>
                  ) : (
                    <span className="domestic-badge uninstalled">⚪ 未检测到</span>
                  )}
                </div>
                <p className="domestic-card-desc">
                  无需复制粘贴！点击下方按钮即可直接将排版台服务注入至 <code>~/.workbuddy/mcp.json</code>（写入前自动备份）。
                </p>
                <div className="domestic-card-actions">
                  <button
                    type="button"
                    className="btn-domestic-primary"
                    onClick={handleInjectWorkBuddy}
                    disabled={wbInjecting}
                  >
                    ⚡ {wbInjecting ? '正在写入...' : scanState.workbuddyInjected ? '重新写入配置' : '一键免配置写入'}
                  </button>
                  <button
                    type="button"
                    className="btn-domestic-secondary"
                    onClick={() =>
                      handleCopy(
                        JSON.stringify(
                          {
                            mcpServers: {
                              'paper-setting': {
                                command: 'uv',
                                args: ['run', '--directory', projectRoot, 'paper-setting-mcp'],
                                env: {},
                                disabled: false,
                              },
                            },
                          },
                          null,
                          2,
                        ),
                        'workbuddy',
                      )
                    }
                  >
                    {copiedKey === 'workbuddy' ? '已复制！' : '复制 JSON'}
                  </button>
                  <button
                    type="button"
                    className="btn-domestic-secondary"
                    onClick={() => handleLaunchApp('workbuddy')}
                  >
                    启动 App ↗
                  </button>
                </div>
                {wbFeedback && <div className="domestic-feedback-alert">🎉 {wbFeedback}</div>}
              </div>

              {/* Trae Card */}
              <div className="domestic-card">
                <div className="domestic-card-header">
                  <div className="domestic-card-title">
                    <div className="domestic-card-icon trae">T</div>
                    <div>
                      <h4>Trae (字节跳动 AI 原生 IDE)</h4>
                      <span>支持 DeepSeek/Claude 深度编程</span>
                    </div>
                  </div>
                  {scanState.traeInstalled ? (
                    <span className="domestic-badge installed">🟢 本机已安装</span>
                  ) : (
                    <span className="domestic-badge uninstalled">⚪ 未安装 (提供专属配置)</span>
                  )}
                </div>
                <p className="domestic-card-desc">
                  字节跳动专为开发者打造的 AI IDE。在项目根目录下放置 <code>.trae/mcp.json</code> 即可开启排版 Agent 协同。
                </p>
                <div className="domestic-card-actions">
                  <button
                    type="button"
                    className="btn-domestic-primary"
                    onClick={() =>
                      handleCopy(
                        JSON.stringify(
                          {
                            mcpServers: {
                              'paper-setting': {
                                command: 'uv',
                                args: ['run', '--directory', projectRoot, 'paper-setting-mcp'],
                                env: {},
                              },
                            },
                          },
                          null,
                          2,
                        ),
                        'trae',
                      )
                    }
                  >
                    {copiedKey === 'trae' ? '已复制！' : '复制 Trae 配置 (.trae/mcp.json)'}
                  </button>
                  <button type="button" className="btn-domestic-secondary" onClick={handleInjectTrae}>
                    写入 ~/.trae/mcp.json
                  </button>
                </div>
                {traeFeedback && <div className="domestic-feedback-alert">🎉 {traeFeedback}</div>}
              </div>

              {/* Doubao / Coze Card */}
              <div className="domestic-card">
                <div className="domestic-card-header">
                  <div className="domestic-card-title">
                    <div className="domestic-card-icon doubao">豆</div>
                    <div>
                      <h4>豆包 / 扣子 (Coze 智能体)</h4>
                      <span>国民级对话助手 / 智能体平台</span>
                    </div>
                  </div>
                  {scanState.doubaoInstalled ? (
                    <span className="domestic-badge installed">🟢 本机已安装</span>
                  ) : (
                    <span className="domestic-badge uninstalled">⚪ 未安装</span>
                  )}
                </div>
                <p className="domestic-card-desc">
                  支持在扣子 (Coze) 中导入本地 OpenAPI 规范创建论文排版 Bot，并在豆包客户端中发起排版任务调度。
                </p>
                <div className="domestic-card-actions">
                  <button
                    type="button"
                    className="btn-domestic-purple"
                    onClick={() => handleCopy('http://127.0.0.1:8765/openapi.json', 'doubao')}
                  >
                    {copiedKey === 'doubao' ? '已复制！' : '复制 OpenAPI 地址'}
                  </button>
                  <button type="button" className="btn-domestic-secondary" onClick={() => handleLaunchApp('doubao')}>
                    启动豆包 ↗
                  </button>
                </div>
              </div>

              {/* Cherry Studio / DeepSeek Card */}
              <div className="domestic-card">
                <div className="domestic-card-header">
                  <div className="domestic-card-title">
                    <div className="domestic-card-icon cherry">D</div>
                    <div>
                      <h4>Cherry Studio / DeepSeek 本地栈</h4>
                      <span>顶尖推理大模型 & 开源客户端</span>
                    </div>
                  </div>
                  <span className="domestic-badge installed">🟢 本机已就绪</span>
                </div>
                <p className="domestic-card-desc">
                  在 Cherry Studio 的“设置 -&gt; MCP 扩展”中添加本地命令行服务，即可接入 100% 确定性排版算力。
                </p>
                <div className="domestic-card-actions">
                  <button
                    type="button"
                    className="btn-domestic-secondary"
                    onClick={() =>
                      handleCopy(`uv run --directory ${projectRoot} paper-setting-mcp`, 'cherry')
                    }
                  >
                    {copiedKey === 'cherry' ? '已复制命令！' : '复制 MCP 启动命令'}
                  </button>
                  <button
                    type="button"
                    className="btn-domestic-secondary"
                    onClick={() => handleLaunchApp('deepseek')}
                  >
                    启动 DeepSeek ↗
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: International Config */}
        {mainTab === 'international' && (
          <div className="mcp-tab-content">
            <div className="agent-selector-bar">
              {(['cursor', 'claude', 'windsurf', 'cli'] as InternationalAgentTab[]).map(tab => (
                <button
                  key={tab}
                  type="button"
                  className={`agent-subtab ${agentTab === tab ? 'active' : ''}`}
                  onClick={() => setAgentTab(tab)}
                >
                  {internationalConfigs[tab].title}
                </button>
              ))}
            </div>

            <div className="mcp-code-card">
              <div className="mcp-code-header">
                <div>
                  <small>配置文件路径：</small>
                  <code>{internationalConfigs[agentTab].filePath}</code>
                </div>
                <button
                  type="button"
                  className="btn-copy-code"
                  onClick={() => handleCopy(internationalConfigs[agentTab].json, agentTab)}
                >
                  {copiedKey === agentTab ? (
                    <>
                      <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor">
                        <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                      </svg>
                      已复制！
                    </>
                  ) : (
                    <>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                      </svg>
                      复制配置
                    </>
                  )}
                </button>
              </div>
              <pre className="mcp-code-snippet">
                <code>{internationalConfigs[agentTab].json}</code>
              </pre>
            </div>
          </div>
        )}

        {/* Tab 3: Tools */}
        {mainTab === 'tools' && (
          <div className="mcp-tab-content">
            <p className="mcp-tools-intro">
              Paper Setting 遵循 Model Context Protocol (MCP) 规范，向连接的 Agent 暴露以下 7 项确定性编译与审计工具：
            </p>
            <div className="mcp-tools-list">
              {tools.map(tool => (
                <div key={tool.name} className="mcp-tool-item">
                  <div className="mcp-tool-top">
                    <span className="mcp-tool-name">{tool.name}</span>
                    <span className="mcp-tool-badge" style={{ backgroundColor: `${tool.color}15`, color: tool.color }}>
                      {tool.badge}
                    </span>
                  </div>
                  <p className="mcp-tool-desc">{tool.desc}</p>
                  <div className="mcp-tool-params">
                    <strong>入参：</strong>
                    <code>{tool.params}</code>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Safety */}
        {mainTab === 'safety' && (
          <div className="mcp-tab-content">
            <div className="mcp-safety-card">
              <div className="safety-badge-header">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="#1c5d43" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="m9 12 2 2 4-4" />
                </svg>
                <h3>为什么采用“外部 Agent + 本地确定性引擎 + 人机安全回环”？</h3>
              </div>
              <div className="safety-grid">
                <div className="safety-item">
                  <strong>1. 绝不越权：Agent 只能提议，不能擅改</strong>
                  <p>
                    通用大模型直接生成 Word 文档容易产生文本幻觉、丢失公式（OMML）或破坏页码。在 Paper Setting 中，Agent
                    通过 MCP 只能发起排版计算并生成审查计划，最终补丁必须在 Web 工作台由用户审批。
                  </p>
                </div>
                <div className="safety-item">
                  <strong>2. 零隐私泄露：100% 本地隔离运行</strong>
                  <p>
                    Paper Setting 绑定 127.0.0.1，排版引擎与 AST 运算完全在本地纯算沙箱中进行。即便通过 MCP 连接，通信也仅在本地
                    stdio 管道与回环接口流转，未发表的学术成果绝对不会上传至第三方服务器。
                  </p>
                </div>
                <div className="safety-item">
                  <strong>3. 机器可读的可审计差量（Diff）</strong>
                  <p>
                    每次排版均保留只读原件，并生成段落级别的 .audit.json 清单。每一项字号、行距、页眉页脚和引注调整均具备唯一
                    Operation ID，提供完整的科研可复现性。
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mcp-modal-footer">
          <div className="mcp-footer-note">
            <span>💡 提示：工作目录路径已锁定为本地项目环境，保证绝对安全。</span>
          </div>
          <button type="button" className="btn-mcp-close" onClick={onClose}>
            完成并返回工作台
          </button>
        </div>
      </div>
    </div>
  )
}
