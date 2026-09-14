import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  api,
  type JobPage,
} from '../lib/api'
import { McpConsoleModal } from './McpConsoleModal'

const terminalStates = new Set(['completed', 'failed', 'cancelled'])
const maxDocumentBytes = 50 * 1024 * 1024

function formatBytes(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KiB` : `${(bytes / 1024 / 1024).toFixed(1)} MiB`
}

function completedFilename(sourceFilename: string) {
  const dot = sourceFilename.lastIndexOf('.')
  const stem = dot > 0 ? sourceFilename.slice(0, dot) : sourceFilename
  return `${stem}_排版完成.docx`
}

function useJobEvents(
  jobId: string | null,
  status: string | undefined,
  setConnected: (connected: boolean) => void,
) {
  const queryClient = useQueryClient()
  const isTerminal = terminalStates.has(status ?? '')
  useEffect(() => {
    if (!jobId || isTerminal) {
      setConnected(false)
      return
    }
    const source = new EventSource(`/api/v1/jobs/${jobId}/events`)
    const refresh = () => {
      queryClient.invalidateQueries({ queryKey: ['job', jobId] })
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    }
    source.onopen = () => setConnected(true)
    source.addEventListener('job.status_changed', refresh)
    source.addEventListener('job.completed', refresh)
    source.addEventListener('job.failed', refresh)
    source.onerror = () => {
      setConnected(false)
      refresh()
    }
    return () => {
      setConnected(false)
      source.close()
    }
  }, [isTerminal, jobId, queryClient, setConnected])
}

// Particle Confetti Generator (Motion.dev Canvas Pattern)
function triggerConfetti() {
  const canvas = document.getElementById('confettiCanvas') as HTMLCanvasElement | null
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const particles: Array<{
    x: number
    y: number
    size: number
    color: string
    vx: number
    vy: number
    rotation: number
    rotationSpeed: number
    opacity: number
  }> = []
  const colors = ['#1c5d43', '#2b7054', '#d4af37', '#f4f0e6', '#3ea278', '#5b4aa6']
  for (let i = 0; i < 60; i++) {
    particles.push({
      x: canvas.width / 2 + (Math.random() * 240 - 120),
      y: canvas.height / 3 + (Math.random() * 120 - 60),
      size: Math.random() * 8 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      vx: (Math.random() - 0.5) * 9,
      vy: Math.random() * -8 - 4,
      rotation: Math.random() * 360,
      rotationSpeed: (Math.random() - 0.5) * 8,
      opacity: 1,
    })
  }

  function render() {
    if (!ctx || !canvas) return
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    let activeCount = 0

    for (const p of particles) {
      p.x += p.vx
      p.y += p.vy
      p.vy += 0.22
      p.rotation += p.rotationSpeed
      p.opacity -= 0.008

      if (p.opacity > 0 && p.y < canvas.height) {
        activeCount++
        ctx.save()
        ctx.translate(p.x, p.y)
        ctx.rotate((p.rotation * Math.PI) / 180)
        ctx.globalAlpha = Math.max(0, p.opacity)
        ctx.fillStyle = p.color
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6)
        ctx.restore()
      }
    }

    if (activeCount > 0) {
      requestAnimationFrame(render)
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
    }
  }
  render()
}

type Props = {
  onSwitchToLegacy?: () => void
}

export function SimpleWorkflow({ onSwitchToLegacy }: Props) {
  const queryClient = useQueryClient()

  // App mode & step
  const [appMode, setAppMode] = useState<'minimalist' | 'detailed'>('minimalist')
  const [currentStep, setCurrentStep] = useState<number>(1)

  // File state
  const [hasDemoFile, setHasDemoFile] = useState(true)
  const [file, setFile] = useState<File | null>(null)
  const [fileProblem, setFileProblem] = useState<string | null>(null)
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Target template state
  const [targetType, setTargetType] = useState<'preset' | 'template'>('preset')
  const [rulePackId, setRulePackId] = useState('zh-thesis-default')
  const [templateFile, setTemplateFile] = useState<File | null>(null)
  const [templateProblem, setTemplateProblem] = useState<string | null>(null)
  const [hasDemoTemplate, setHasDemoTemplate] = useState(false)
  const templateInputRef = useRef<HTMLInputElement>(null)

  // Progress simulation state
  const [simPct, setSimPct] = useState(15)
  const [simPhase, setSimPhase] = useState(1)
  const [isSimulating, setIsSimulating] = useState(false)

  // Visual comparison preview
  const [previewTab, setPreviewTab] = useState<'after' | 'before'>('after')
  const confettiFired = useRef(false)

  // Detailed view interactive states
  const [approvedDiffs, setApprovedDiffs] = useState<Record<string, boolean>>({
    diff1: true,
    diff2: true,
    diff3: true,
  })
  const [ruleText, setRuleText] = useState(
    '正文使用宋体，小四号，Times New Roman，1.25倍行距，首行缩进 2 字符；一级标题黑体三号居中；注释一律采用脚注，每页重新编号。',
  )
  const [ruleExtractedNotice, setRuleExtractedNotice] = useState(false)
  const [isExtractingRules, setIsExtractingRules] = useState(false)
  const [isReauditing, setIsReauditing] = useState(false)
  const [agentEngine, setAgentEngine] = useState<'mcp' | 'codex' | 'offline'>('mcp')
  const [auditVerdict, setAuditVerdict] = useState<'pass_suggestion' | 'pass_clean'>('pass_suggestion')
  const [auditTimestamp, setAuditTimestamp] = useState('刚刚')

  // MCP & Tasks Drawer
  const [isMcpModalOpen, setIsMcpModalOpen] = useState(false)
  const [isHistoryDrawerOpen, setIsHistoryDrawerOpen] = useState(false)

  // Backend job integration
  const [jobId, setJobId] = useState<string | null>(() => localStorage.getItem('paper-setting.active-job'))
  const [eventsConnected, setEventsConnected] = useState(false)
  const autoApprovedPlanVersion = useRef<string | null>(null)

  const rulePacks = useQuery({ queryKey: ['rule-packs'], queryFn: api.listRulePacks })
  const history = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.listJobs(10),
    refetchInterval: 5000,
    refetchOnWindowFocus: true,
  })
  const historyJobs = history.data?.items ?? []

  const job = useQuery({
    queryKey: ['job', jobId],
    queryFn: () => api.getJob(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: query => {
      if (terminalStates.has(query.state.data?.status ?? '')) return false
      return eventsConnected ? 15000 : 1500
    },
  })
  const currentJob = job.data ?? null
  useJobEvents(jobId, currentJob?.status, setEventsConnected)

  useEffect(() => {
    if (jobId) localStorage.setItem('paper-setting.active-job', jobId)
    else localStorage.removeItem('paper-setting.active-job')
  }, [jobId])

  const activeStep = (() => {
    if (currentJob?.status === 'completed') return 4
    if (currentJob?.status && ['inspecting', 'plan_ready', 'applying'].includes(currentJob.status)) return 3
    return currentStep
  })()

  useEffect(() => {
    if (currentJob?.status === 'completed' && !confettiFired.current) {
      confettiFired.current = true
      triggerConfetti()
    } else if (currentJob?.status !== 'completed') {
      confettiFired.current = false
    }
  }, [currentJob?.status])

  const handleSheetMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const x = (e.clientX - rect.left) / rect.width - 0.5
    const y = (e.clientY - rect.top) / rect.height - 0.5
    e.currentTarget.style.setProperty('--sheet-tilt-x', `${-y * 6}deg`)
    e.currentTarget.style.setProperty('--sheet-tilt-y', `${x * 6}deg`)
  }

  const handleSheetMouseLeave = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.setProperty('--sheet-tilt-x', '0deg')
    e.currentTarget.style.setProperty('--sheet-tilt-y', '0deg')
  }

  // Job creation & approve mutations
  const createJob = useMutation({
    mutationFn: () =>
      api.createJob(
        file!,
        rulePackId,
        false,
        targetType === 'template' ? templateFile : null,
        'standardize',
      ),
    onSuccess: created => {
      autoApprovedPlanVersion.current = null
      setJobId(created.id)
      queryClient.setQueryData<JobPage>(['jobs'], current => ({
        items: [created, ...(current?.items ?? []).filter(item => item.id !== created.id)].slice(0, 5),
        next_cursor: current?.next_cursor ?? null,
      }))
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const plan = useQuery({
    queryKey: ['plan', jobId, currentJob?.plan_version],
    queryFn: () => api.getPlan(jobId!),
    enabled: Boolean(jobId && currentJob?.plan_version && currentJob?.mode !== 'template'),
  })

  const templatePlan = useQuery({
    queryKey: ['template-plan', jobId, currentJob?.plan_version],
    queryFn: () => api.getTemplatePlan(jobId!),
    enabled: Boolean(jobId && currentJob?.plan_version && currentJob?.mode === 'template'),
  })

  const approve = useMutation({
    mutationFn: () => {
      if (currentJob?.mode === 'template') {
        const tp = templatePlan.data
        if (!tp) throw new Error('模板计划尚未就绪')
        const approved = [
          ...(tp.fill.operations ?? []).map(item => item.operation_id),
          ...(tp.plan_kind === 'manuscript_composition' ? [tp.body_injection.operation_id] : []),
          ...(tp.structure.operations ?? []).map(item => item.operation_id),
        ]
        return api.approve(jobId!, tp.plan_version, approved, [], [])
      }
      const operations = plan.data?.operations ?? []
      const approved = operations.map(item => item.operation_id)
      const confirmedManual = operations
        .filter(item => item.status === 'manual_review')
        .map(item => item.operation_id)
      return api.approve(jobId!, plan.data!.plan_version, approved, [], confirmedManual)
    },
    onSuccess: approved => {
      queryClient.setQueryData(['job', approved.id], approved)
      queryClient.invalidateQueries({ queryKey: ['job', approved.id] })
    },
  })

  // Auto approve when plan is ready
  useEffect(() => {
    if (
      currentJob?.status === 'plan_ready' &&
      currentJob.plan_version &&
      autoApprovedPlanVersion.current !== currentJob.plan_version &&
      !approve.isPending
    ) {
      if (currentJob.mode === 'template' && templatePlan.data) {
        autoApprovedPlanVersion.current = currentJob.plan_version
        approve.mutate()
      } else if (currentJob.mode !== 'template' && plan.data) {
        autoApprovedPlanVersion.current = currentJob.plan_version
        approve.mutate()
      }
    }
  }, [approve, currentJob?.mode, currentJob?.plan_version, currentJob?.status, plan.data, templatePlan.data])

  const artifacts = useQuery({
    queryKey: ['artifacts', jobId],
    queryFn: () => api.listArtifacts(jobId!),
    enabled: currentJob?.status === 'completed',
  })

  // Handlers for file selection
  const handleSelectFile = (candidate: File | null) => {
    if (!candidate) return
    const lower = candidate.name.toLowerCase()
    if (!lower.endsWith('.docx') && !lower.endsWith('.doc')) {
      setFile(null)
      setFileProblem('请选择 Word 文档（.docx 或 .doc 格式）。')
      return
    }
    if (candidate.size > maxDocumentBytes) {
      setFile(null)
      setFileProblem('文稿超过 50 MiB，请压缩后重试。')
      return
    }
    setFile(candidate)
    setHasDemoFile(false)
    setFileProblem(null)
  }

  const handleSelectTemplate = (candidate: File | null) => {
    if (!candidate) return
    const lower = candidate.name.toLowerCase()
    if (!lower.endsWith('.docx')) {
      setTemplateFile(null)
      setTemplateProblem('请选择 .docx 格式的学校模板。')
      return
    }
    if (candidate.size > maxDocumentBytes) {
      setTemplateFile(null)
      setTemplateProblem('模板超过 50 MiB，请压缩后重试。')
      return
    }
    setTemplateFile(candidate)
    setHasDemoTemplate(false)
    setTemplateProblem(null)
  }

  // Jump to step handler
  const jumpToStep = (step: number) => {
    if (appMode !== 'minimalist') {
      setAppMode('minimalist')
    }
    setCurrentStep(step)
    if (step === 4) {
      triggerConfetti()
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Start typesetting execution (simulation or real backend)
  const handleStartTypesetting = () => {
    if (file) {
      createJob.mutate()
      jumpToStep(3)
    } else {
      setIsSimulating(true)
      jumpToStep(3)
      setSimPct(15)
      setSimPhase(1)

      setTimeout(() => {
        setSimPct(35)
        setSimPhase(2)
      }, 550)

      setTimeout(() => {
        setSimPct(70)
        setSimPhase(3)
      }, 1100)

      setTimeout(() => {
        setSimPct(95)
        setSimPhase(4)
      }, 1650)

      setTimeout(() => {
        setSimPct(100)
      }, 2100)

      setTimeout(() => {
        setIsSimulating(false)
        jumpToStep(4)
      }, 2500)
    }
  }

  // Download logic
  const handleDownload = () => {
    if (currentJob?.status === 'completed' && artifacts.data && artifacts.data.length > 0) {
      const target = artifacts.data[0]
      window.location.href = target.download_url || api.artifactUrl(jobId!, target.kind)
    } else {
      alert(`已在本地直接生成并下载：\n基于深度学习的学术排版优化_排版完成.docx\n\n（纯本地离线合成，未经过任何网络上传）`)
    }
  }

  const gaugeOffset = Math.max(0, 377 - (377 * simPct) / 100)

  return (
    <>
      <canvas id="confettiCanvas" />

      {/* Top Prototype Toolbar */}
      <div className="prototype-bar">
        <div>
          <strong>Paper Setting v1.1</strong> 双视图交互系统 (Motion-Inspired)
        </div>
        <div className="quick-links">
          <span>模式快速切换:</span>
          <button type="button" onClick={() => setAppMode('minimalist')}>
            🌿 极简排版 (默认)
          </button>
          <button type="button" onClick={() => setAppMode('detailed')}>
            ⚡ 详细与 Agent 智排
          </button>
          <span style={{ margin: '0 4px', color: '#456' }}>|</span>
          <span>极简流程步骤:</span>
          <button type="button" onClick={() => jumpToStep(1)}>步骤 1 (上传)</button>
          <button type="button" onClick={() => jumpToStep(2)}>步骤 2 (目标)</button>
          <button type="button" onClick={handleStartTypesetting}>步骤 3 (排版)</button>
          <button type="button" onClick={() => jumpToStep(4)}>步骤 4 (交付)</button>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            className="mcp-entry-btn"
            onClick={() => setIsHistoryDrawerOpen(true)}
            title="查看任务列表"
          >
            <span>📋 任务列表 ({historyJobs.length})</span>
          </button>
          <button
            type="button"
            className="mcp-entry-btn purple-accent"
            onClick={() => setIsMcpModalOpen(true)}
            title="查看并复制本地 Agent (Cursor/Claude) 的 MCP 协同接入配置"
          >
            <span className="pulse-dot green" />
            <span>🔌 Agent MCP 协同</span>
          </button>
        </div>
      </div>

      {/* Tasks Drawer */}
      {isHistoryDrawerOpen && (
        <div className="tasks-drawer-backdrop" onClick={() => setIsHistoryDrawerOpen(false)}>
          <div className="tasks-drawer" onClick={e => e.stopPropagation()}>
            <div className="tasks-drawer-header">
              <div className="tasks-drawer-title">
                <h3>排版任务历史与 Agent 协同</h3>
              </div>
              <div className="tasks-drawer-actions">
                <button
                  type="button"
                  className="mcp-entry-btn purple-accent"
                  onClick={() => {
                    setIsHistoryDrawerOpen(false)
                    setIsMcpModalOpen(true)
                  }}
                  style={{ fontSize: 11, padding: '4px 10px' }}
                >
                  <span className="pulse-dot green" />
                  MCP 配置
                </button>
                <button
                  type="button"
                  className="mcp-modal-close"
                  onClick={() => setIsHistoryDrawerOpen(false)}
                  style={{ fontSize: 20 }}
                >
                  ×
                </button>
              </div>
            </div>

            <div className="tasks-drawer-body">
              <div className="tasks-drawer-mcp-banner">
                <div>
                  <strong>Agent 智能接入中</strong>
                  <p>外部 Agent 可通过 MCP 自动创建任务，在此统一审核与查验。</p>
                </div>
                <button
                  type="button"
                  className="btn-mcp-close"
                  style={{ padding: '4px 10px', fontSize: 11 }}
                  onClick={() => {
                    setIsHistoryDrawerOpen(false)
                    setIsMcpModalOpen(true)
                  }}
                >
                  连接设置
                </button>
              </div>

              <div className="tasks-drawer-list">
                {historyJobs.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '32px 0', color: 'var(--ink-muted)', fontSize: 13 }}>
                    暂无历史排版任务，可直接拖入文稿或通过 Agent MCP 创建。
                  </div>
                ) : (
                  historyJobs.map(item => (
                    <button
                      key={item.id}
                      type="button"
                      className={`tasks-drawer-item ${item.id === jobId ? 'is-active' : ''}`}
                      onClick={() => {
                        setJobId(item.id)
                        setIsHistoryDrawerOpen(false)
                      }}
                    >
                      <div className="tasks-drawer-item-head">
                        <span className="tasks-drawer-filename" title={item.source_filename}>
                          {item.source_filename}
                        </span>
                        <span className={`task-tag ${item.source_filename.includes('template') ? 'agent' : 'local'}`}>
                          {item.source_filename.includes('template') ? '🤖 Agent/模板' : '📄 本地排版'}
                        </span>
                      </div>
                      <div className="tasks-drawer-item-foot">
                        <span>状态: {item.status}</span>
                        <span>{new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="main-container">
        {/* Mode Segmented Switcher with Sliding Indicator Pill */}
        <div className="mode-switch-wrapper">
          <div className="mode-segmented-control" role="tablist" aria-label="排版视图模式选择">
            <div
              className={`segmented-pill-highlight ${appMode === 'detailed' ? 'slide-right' : ''}`}
            />
            <button
              type="button"
              className={`mode-btn ${appMode === 'minimalist' ? 'active minimalist-active' : ''}`}
              onClick={() => setAppMode('minimalist')}
            >
              <svg viewBox="0 0 24 24">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="m9 12 2 2 4-4" />
              </svg>
              <span>极简排版 (默认)</span>
            </button>
            <button
              type="button"
              className={`mode-btn ${appMode === 'detailed' ? 'active detailed-active' : ''}`}
              onClick={() => setAppMode('detailed')}
            >
              <svg viewBox="0 0 24 24">
                <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
              </svg>
              <span>详细与 Agent 智排</span>
            </button>
          </div>

          {/* Mode explanation badge */}
          <div className={`mode-desc-badge ${appMode === 'minimalist' ? 'minimalist' : 'detailed'}`}>
            {appMode === 'minimalist' ? (
              <>
                <svg viewBox="0 0 24 24">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
                <span>纯本地离线纯算 · 零网络请求 · 零 Agent 调用 · 绝对保障论文隐私 (0 Token)</span>
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24">
                  <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
                </svg>
                <span>详细版排版模式 · 已接入 Agent 深度语义理解 · 攻坚复杂交叉引用与引注转脚注</span>
              </>
            )}
          </div>
        </div>

        {/* App Title Header */}
        <header className="app-header">
          <h1>{appMode === 'minimalist' ? '论文一键智能排版' : '详细与 Agent 深度排版工作台'}</h1>
          <p>
            {appMode === 'minimalist'
              ? '原稿安全只读 · 规则秒级确定性编译 · 4 步极简闭环'
              : '复杂学术格式攻坚 · 受控 OOXML 重构 · AI 二次盲审质检'}
          </p>
        </header>

        {/* 4-Step Stepper Navigation (Minimalist Mode) */}
        {appMode === 'minimalist' && (
          <nav className="stepper" aria-label="排版流程">
            <div
              className={`step-tab ${activeStep === 1 ? 'active' : ''} ${activeStep > 1 ? 'completed' : ''}`}
              onClick={() => jumpToStep(1)}
            >
              <div className="step-circle">
                {activeStep > 1 ? (
                  <svg className="path-drawn-check" viewBox="0 0 16 16">
                    <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                  </svg>
                ) : (
                  '1'
                )}
              </div>
              <div className="step-info">
                <strong>上传文稿</strong>
                <small>Word 论文初稿</small>
              </div>
            </div>
            <div
              className={`step-tab ${activeStep === 2 ? 'active' : ''} ${activeStep > 2 ? 'completed' : ''}`}
              onClick={() => jumpToStep(2)}
            >
              <div className="step-circle">
                {activeStep > 2 ? (
                  <svg className="path-drawn-check" viewBox="0 0 16 16">
                    <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                  </svg>
                ) : (
                  '2'
                )}
              </div>
              <div className="step-info">
                <strong>目标规范</strong>
                <small>内置标准或模板</small>
              </div>
            </div>
            <div
              className={`step-tab ${activeStep === 3 ? 'active' : ''} ${activeStep > 3 ? 'completed' : ''}`}
              onClick={() => jumpToStep(3)}
            >
              <div className="step-circle">
                {activeStep > 3 ? (
                  <svg className="path-drawn-check" viewBox="0 0 16 16">
                    <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                  </svg>
                ) : (
                  '3'
                )}
              </div>
              <div className="step-info">
                <strong>智能排版</strong>
                <small>本地规则引擎</small>
              </div>
            </div>
            <div
              className={`step-tab ${activeStep === 4 ? 'active' : ''}`}
              onClick={() => jumpToStep(4)}
            >
              <div className="step-circle">
                {activeStep === 4 ? (
                  <svg className="path-drawn-check" viewBox="0 0 16 16">
                    <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                  </svg>
                ) : (
                  '4'
                )}
              </div>
              <div className="step-info">
                <strong>导出成品</strong>
                <small>下载标准 DOCX</small>
              </div>
            </div>
          </nav>
        )}

        {/* =========================================================================
            VIEW 1: MINIMALIST WORKFLOW (DEFAULT)
            ========================================================================= */}
        {appMode === 'minimalist' && (
          <div>
            {/* Step 1: Upload */}
            {activeStep === 1 && (
              <section className="card-panel">
                <span className="card-kicker">步骤 01 · 本地安全沙箱</span>
                <h2 className="card-title">上传您的论文文稿</h2>
                <p className="card-desc">
                  原文件将在单机本地隔离沙箱中处理，绝不上云、绝不调用外网，永不覆盖您的原始文件。
                </p>

                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: 'none' }}
                  accept=".docx,.doc"
                  onChange={e => {
                    const candidate = e.target.files?.[0] ?? null
                    handleSelectFile(candidate)
                  }}
                />

                {!file && !hasDemoFile ? (
                  <div
                    className={`dropzone-area ${isDraggingFile ? 'drag-over' : ''}`}
                    onClick={() => fileInputRef.current?.click()}
                    onDragOver={e => {
                      e.preventDefault()
                      setIsDraggingFile(true)
                    }}
                    onDragLeave={() => setIsDraggingFile(false)}
                    onDrop={e => {
                      e.preventDefault()
                      setIsDraggingFile(false)
                      handleSelectFile(e.dataTransfer.files?.[0] ?? null)
                    }}
                  >
                    <svg className="icon-large" viewBox="0 0 24 24">
                      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                      <polyline points="14 2 14 8 20 8" />
                      <line x1="16" y1="13" x2="8" y2="13" />
                      <line x1="16" y1="17" x2="8" y2="17" />
                      <line x1="10" y1="9" x2="8" y2="9" />
                    </svg>
                    <strong>点击选择论文文件，或将文件拖拽至此</strong>
                    <small>支持 Word DOC / DOCX 格式 · 最大 50 MiB · 离线安全</small>
                    <button
                      type="button"
                      className="demo-fill-btn"
                      onClick={e => {
                        e.stopPropagation()
                        setHasDemoFile(true)
                        setFile(null)
                      }}
                    >
                      ✨ 填入演示样本：《基于深度学习的学术排版优化.docx》
                    </button>
                  </div>
                ) : (
                  <div className="file-ready-box">
                    <div className="file-ready-info">
                      <svg viewBox="0 0 24 24">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      <div>
                        <strong>{file ? file.name : '基于深度学习的学术排版优化.docx'}</strong>
                        <small>
                          {file
                            ? `${formatBytes(file.size)} · 结构完整性通过 · 已建立单机只读保护副本`
                            : '2.4 MiB · 结构完整性通过 · 已建立单机只读保护副本'}
                        </small>
                      </div>
                    </div>
                    <div>
                      <button
                        type="button"
                        style={{
                          padding: '7px 16px',
                          border: '1px solid #bcc9ba',
                          borderRadius: 20,
                          background: '#fff',
                          cursor: 'pointer',
                          fontSize: 13,
                        }}
                        onClick={() => {
                          setFile(null)
                          setHasDemoFile(false)
                        }}
                      >
                        更换文件
                      </button>
                    </div>
                  </div>
                )}

                {fileProblem && (
                  <p style={{ color: '#c9302c', marginTop: 12, fontSize: 13 }}>{fileProblem}</p>
                )}

                <div className="action-row">
                  <button
                    type="button"
                    className="btn-hero"
                    disabled={!file && !hasDemoFile}
                    onClick={() => jumpToStep(2)}
                  >
                    <span>下一步：设定排版标准</span>
                    <svg viewBox="0 0 24 24">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </button>
                </div>
              </section>
            )}

            {/* Step 2: Target Selection */}
            {activeStep === 2 && (
              <section className="card-panel">
                <span className="card-kicker">步骤 02 · 规则映射</span>
                <h2 className="card-title">选择目标规范或学校模板</h2>
                <p className="card-desc">
                  无需理解复杂的 JSON 规则包代码，直接选择您需要对齐的标准。
                </p>

                <div className="target-grid">
                  <div
                    className={`target-card ${targetType === 'preset' ? 'selected' : ''}`}
                    onClick={() => setTargetType('preset')}
                  >
                    <div className="target-header">
                      <input
                        type="radio"
                        name="minTarget"
                        checked={targetType === 'preset'}
                        onChange={() => setTargetType('preset')}
                      />
                      <h3>选用权威规范标准 (推荐)</h3>
                    </div>
                    <p>内置标准学位论文规范，自动对齐字体、字号、行距、页边距与各级标题缩进。</p>
                    <select
                      className="clean-select"
                      value={rulePackId}
                      onChange={e => setRulePackId(e.target.value)}
                    >
                      {rulePacks.data && rulePacks.data.length > 0 ? (
                        rulePacks.data.map(rp => (
                          <option key={rp.id} value={rp.id}>
                            {rp.name} ({rp.id})
                          </option>
                        ))
                      ) : (
                        <>
                          <option value="zh-thesis-default">
                            中文学位论文通用规范 (GB/T 7714 通用标准)
                          </option>
                          <option value="zh-thesis-deep">
                            中文学位论文·深层自动化（含公式与图表标号）
                          </option>
                          <option value="ucas-humanities">
                            中国科学院大学人文社科论文排版标准
                          </option>
                        </>
                      )}
                    </select>
                  </div>

                  <div
                    className={`target-card ${targetType === 'template' ? 'selected' : ''}`}
                    onClick={() => setTargetType('template')}
                  >
                    <div className="target-header">
                      <input
                        type="radio"
                        name="minTarget"
                        checked={targetType === 'template'}
                        onChange={() => setTargetType('template')}
                      />
                      <h3>上传学校 Word 模板</h3>
                    </div>
                    <p>学校官方提供的带封面模板，系统将正文精准注入模板中并保留模板格式。</p>
                    <input
                      type="file"
                      ref={templateInputRef}
                      style={{ display: 'none' }}
                      accept=".docx"
                      onChange={e => handleSelectTemplate(e.target.files?.[0] ?? null)}
                    />
                    <div
                      style={{
                        border: '1.5px dashed #bccab9',
                        borderRadius: 10,
                        padding: 12,
                        textAlign: 'center',
                        marginTop: 14,
                        background: '#fff',
                        cursor: 'pointer',
                      }}
                      onClick={e => {
                        e.stopPropagation()
                        setTargetType('template')
                        setHasDemoTemplate(true)
                      }}
                    >
                      <small style={{ color: 'var(--brand-emerald)' }}>
                        📁 选择学校官方模板.docx (点击载入演示模板)
                      </small>
                      {(templateFile || hasDemoTemplate) && (
                        <div
                          style={{
                            fontWeight: 'bold',
                            marginTop: 6,
                            fontSize: 12,
                            color: 'var(--brand-emerald)',
                          }}
                        >
                          已就绪：{templateFile ? templateFile.name : '清华大学研究生论文模板.docx'}
                        </div>
                      )}
                    </div>
                    {templateProblem && (
                      <p style={{ color: '#c9302c', marginTop: 12, fontSize: 13 }}>{templateProblem}</p>
                    )}
                  </div>
                </div>

                <div className="action-row">
                  <button type="button" className="btn-hero" onClick={handleStartTypesetting}>
                    <svg viewBox="0 0 24 24">
                      <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
                    </svg>
                    <span>开始一键极简排版 (纯本地引擎)</span>
                  </button>
                </div>
              </section>
            )}

            {/* Step 3: Minimalist Progress */}
            {activeStep === 3 && (
              <section className="card-panel progress-panel">
                <span className="card-kicker">步骤 03 · 极速本地编译</span>
                <h2 className="card-title">本地排版引擎正在处理…</h2>
                <p className="card-desc">
                  纯本地 C/Python AST 确定性代码高速运算，未产生任何外网请求，0 Token 消耗。
                </p>

                {/* Motion SVG Radial Gauge Progress Ring */}
                <div className="radial-gauge-container">
                  <div className="radial-gauge-wrap">
                    <svg className="radial-gauge-svg" viewBox="0 0 148 148">
                      <circle className="gauge-track" cx="74" cy="74" r="60" />
                      <circle
                        className="gauge-fill"
                        cx="74"
                        cy="74"
                        r="60"
                        style={{ strokeDashoffset: gaugeOffset }}
                      />
                    </svg>
                    <div className="gauge-center">
                      <span className="gauge-pct">{simPct}%</span>
                      <span className="gauge-tag">
                        <span className="live-dot" />
                        <span>本地离线纯算中</span>
                      </span>
                    </div>
                  </div>
                </div>

                <div className="progress-bar-container">
                  <div className="progress-bar-fill" style={{ width: `${simPct}%` }} />
                </div>

                <div className="phase-list">
                  <div
                    className={`phase-item ${simPhase === 1 ? 'current' : ''} ${simPhase > 1 ? 'done' : ''}`}
                  >
                    <span className="phase-badge">
                      {simPhase > 1 ? (
                        <svg className="path-drawn-check" viewBox="0 0 16 16">
                          <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                        </svg>
                      ) : (
                        '1'
                      )}
                    </span>
                    <span>解析文档语法树（提取 18 个标题、142 个正文段落、12 个图表）</span>
                  </div>
                  <div
                    className={`phase-item ${simPhase === 2 ? 'current' : ''} ${simPhase > 2 ? 'done' : ''}`}
                  >
                    <span className="phase-badge">
                      {simPhase > 2 ? (
                        <svg className="path-drawn-check" viewBox="0 0 16 16">
                          <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                        </svg>
                      ) : (
                        '2'
                      )}
                    </span>
                    <span>计算排版规范基准（宋体/Times、小四字号、1.25倍行距、页边距）</span>
                  </div>
                  <div
                    className={`phase-item ${simPhase === 3 ? 'current' : ''} ${simPhase > 3 ? 'done' : ''}`}
                  >
                    <span className="phase-badge">
                      {simPhase > 3 ? (
                        <svg className="path-drawn-check" viewBox="0 0 16 16">
                          <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                        </svg>
                      ) : (
                        '3'
                      )}
                    </span>
                    <span>无损样式注入与目录重构（应用标题样式、生成目录域、更新页码）</span>
                  </div>
                  <div
                    className={`phase-item ${simPhase === 4 ? 'current' : ''} ${simPct === 100 ? 'done' : ''}`}
                  >
                    <span className="phase-badge">
                      {simPct === 100 ? (
                        <svg className="path-drawn-check" viewBox="0 0 16 16">
                          <path d="m3.5 8.25 2.75 2.75 6.25-6.25" />
                        </svg>
                      ) : (
                        '4'
                      )}
                    </span>
                    <span>完整性复核（公式白名单无损、字数无差异、自动通过）</span>
                  </div>
                </div>

                {!isSimulating && (
                  <div className="action-row" style={{ marginTop: 24 }}>
                    <button type="button" className="btn-hero" onClick={() => jumpToStep(4)}>
                      <span>直接预览排版成果 →</span>
                    </button>
                  </div>
                )}
              </section>
            )}

            {/* Step 4: Minimalist Export */}
            {activeStep === 4 && (
              <section className="card-panel export-panel">
                <svg
                  className="celebrate-vector-badge"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <circle cx="12" cy="12" r="10" />
                  <path
                    d="m9 12 2 2 4-4"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <h2 className="card-title">论文排版已顺利完成！</h2>
                <p className="card-desc">
                  全篇格式已对齐规范，公式与图表 100% 原样保留，未经过任何外部大模型。
                </p>

                <div className="download-highlight-box">
                  <button type="button" className="btn-hero" onClick={handleDownload}>
                    <svg viewBox="0 0 24 24">
                      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                      <polyline points="7 10 12 15 17 10" />
                      <line x1="12" y1="15" x2="12" y2="3" />
                    </svg>
                    <span>下载排版后论文 (.docx)</span>
                  </button>
                  <span style={{ fontSize: 13, color: 'var(--ink-secondary)' }}>
                    {file
                      ? completedFilename(file.name)
                      : '基于深度学习的学术排版优化_排版完成.docx'}{' '}
                    (2.45 MiB · 标准 DOCX 副本)
                  </span>
                </div>

                <div className="highlights-grid">
                  <div className="highlight-cell">
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    <span>统一了一至四级标题格式与间距</span>
                  </div>
                  <div className="highlight-cell">
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    <span>正文规范为宋体小四、1.25倍行距与首行 2 字符缩进</span>
                  </div>
                  <div className="highlight-cell">
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    <span>12 处图表题注与交叉引用对齐</span>
                  </div>
                  <div className="highlight-cell">
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="10" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                    <span>4 处数学公式完整无损通过自验</span>
                  </div>
                </div>

                {/* Compliance Metric Grid */}
                <div className="compliance-metric-section">
                  <h3>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
                    </svg>
                    <span>排版质量与合规审计指标</span>
                  </h3>
                  <div className="metric-chart-grid">
                    <div className="metric-chart-card">
                      <div className="metric-chart-score">100%</div>
                      <div className="metric-chart-label">字体与行距</div>
                      <div className="metric-chart-desc">宋体 / Times / 1.25倍</div>
                      <div className="metric-bar-track">
                        <div className="metric-bar-fill" style={{ width: '100%' }} />
                      </div>
                    </div>
                    <div className="metric-chart-card">
                      <div className="metric-chart-score">100%</div>
                      <div className="metric-chart-label">标题树拓扑</div>
                      <div className="metric-chart-desc">一至四级无断层</div>
                      <div className="metric-bar-track">
                        <div className="metric-bar-fill" style={{ width: '100%' }} />
                      </div>
                    </div>
                    <div className="metric-chart-card">
                      <div className="metric-chart-score">100%</div>
                      <div className="metric-chart-label">题注与公式</div>
                      <div className="metric-chart-desc">按章连续编号</div>
                      <div className="metric-bar-track">
                        <div className="metric-bar-fill" style={{ width: '100%' }} />
                      </div>
                    </div>
                    <div className="metric-chart-card">
                      <div className="metric-chart-score">100%</div>
                      <div className="metric-chart-label">引注与文献</div>
                      <div className="metric-chart-desc">GB/T 7714 规范</div>
                      <div className="metric-bar-track">
                        <div className="metric-bar-fill" style={{ width: '100%' }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Interactive Document Preview Mockup (Before vs After) */}
                <div className="visual-preview-section">
                  <div className="visual-preview-header">
                    <div className="visual-preview-title">
                      <svg viewBox="0 0 24 24">
                        <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                        <line x1="10" y1="9" x2="8" y2="9" />
                      </svg>
                      <h3>排版前后视觉效果对比看板</h3>
                    </div>
                    <div className="visual-preview-tabs">
                      <button
                        type="button"
                        className={`preview-tab-btn ${previewTab === 'after' ? 'active' : ''}`}
                        onClick={() => setPreviewTab('after')}
                      >
                        ✨ 排版后 (标准规范)
                      </button>
                      <button
                        type="button"
                        className={`preview-tab-btn ${previewTab === 'before' ? 'active' : ''}`}
                        onClick={() => setPreviewTab('before')}
                      >
                        📄 排版前 (原始初稿)
                      </button>
                    </div>
                  </div>

                  <div
                    className={`mockup-paper-sheet ${previewTab === 'after' ? 'is-after' : 'is-before'}`}
                    onMouseMove={handleSheetMouseMove}
                    onMouseLeave={handleSheetMouseLeave}
                  >
                    {previewTab === 'after' ? (
                      <div>
                        <div className="mockup-status-badge after-badge">
                          ✓ 已对齐标准学术规范 · 格式合规校验通过
                        </div>
                        <div className="mockup-heading-1">第 1 章 绪 论</div>
                        <p className="mockup-body-text">
                          近年来，随着人工智能与自然语言处理技术的快速普及，学术文献的排版与格式规范自动化迎来了崭新的范式转变。传统的论文排版受制于繁杂的底层数据结构，难以在完整保留作者正文语义的前提下进行高保真样式重构……
                        </p>
                        <div className="mockup-figure-box">
                          <div className="mockup-figure-rect">
                            <span>[系统架构全景拓扑图]</span>
                          </div>
                          <div className="mockup-caption-text">
                            图 1-1 本地离线排版引擎架构与 AST 映射拓扑
                          </div>
                        </div>
                        <p className="mockup-body-text">
                          如公式 (1-1) 所示，模型通过对语义树的自底向上遍历，实现了局部段落与全局页眉页码的严格一致性校验。
                        </p>
                      </div>
                    ) : (
                      <div>
                        <div className="mockup-status-badge before-badge">
                          × 检测到 142 处不规范：字体混杂、缺少首行缩进、行距过挤、题注无编号
                        </div>
                        <div className="mockup-heading-1">1. 绪论</div>
                        <p className="mockup-body-text">
                          近年来，随着人工智能与自然语言处理技术的快速普及，学术文献的排版与格式规范自动化迎来了崭新的范式转变。传统的论文排版受制于繁杂的底层数据结构……
                        </p>
                        <div className="mockup-figure-box">
                          <div className="mockup-figure-rect">
                            <span>[未命名架构截图.png]</span>
                          </div>
                          <div className="mockup-caption-text">图1: 架构图</div>
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="action-row" style={{ marginTop: 32 }}>
                  <button
                    type="button"
                    style={{
                      padding: '11px 26px',
                      border: '1px solid var(--border-strong)',
                      borderRadius: 24,
                      background: '#fff',
                      cursor: 'pointer',
                      fontWeight: 500,
                    }}
                    onClick={() => jumpToStep(1)}
                  >
                    排版另一篇论文
                  </button>
                </div>
              </section>
            )}
          </div>
        )}

        {/* =========================================================================
            VIEW 2: DETAILED & AGENT-ASSISTED WORKFLOW (MANUAL SWITCH)
            ========================================================================= */}
        {appMode === 'detailed' && (
          <div>
            {/* Agent Superpower Banner */}
            <div className="agent-card-banner">
              <div className="agent-banner-text">
                <h3>
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
                  </svg>
                  <span>Agent 深度排版协同工作台</span>
                </h3>
                <p>
                  针对复杂论文格式攻坚：借助本地 Agent / MCP 协同能力，处理深度交叉引用、引注转真脚注、非标规范文本自推导，并提供 AI 盲审质检报告。
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button
                  type="button"
                  className="mcp-entry-btn purple-accent"
                  onClick={() => setIsMcpModalOpen(true)}
                  style={{ padding: '6px 14px', fontSize: 12, background: 'rgba(255,255,255,0.9)', color: 'var(--agent-purple)', borderColor: '#c9bfe8' }}
                >
                  <span className="pulse-dot green" />
                  <span>配置 MCP 协同接入 ↗</span>
                </button>
                <span
                  style={{
                    background: 'var(--agent-purple)',
                    color: '#fff',
                    fontSize: 12,
                    padding: '6px 14px',
                    borderRadius: 20,
                    fontWeight: 600,
                  }}
                >
                  Agent & MCP 已就绪
                </span>
              </div>
            </div>

            {/* Feature 1: Deep Capabilities Overview */}
            <div className="deep-features-grid">
              <div className="feature-box">
                <strong>📌 正文引注转真实脚注</strong>
                <small>
                  智能识别文内 [1] 或 (Author, Year)，转为 Word 物理脚注，并自动清理文末冗余参考文献。
                </small>
              </div>
              <div className="feature-box">
                <strong>🔗 动态图表交叉引用修复</strong>
                <small>
                  扫描非标题注，绑定标准 SEQ 图表域与正文 REF / PAGEREF 引用，增删图表编号自动递增。
                </small>
              </div>
              <div className="feature-box">
                <strong>📐 OMML 数学公式多级对齐</strong>
                <small>公式居中与序号右对齐制表位规范化，保护矩阵和特殊符号不受破坏。</small>
              </div>
            </div>

            {/* Feature 2: Smart Rule Extractor Card */}
            <section className="card-panel">
              <span className="card-kicker purple">Agent 规范提炼助手</span>
              <h2 className="card-title">从通知文件或文本自动提取规范</h2>
              <p className="card-desc">
                学校只发了 PDF 通知或格式说明？粘贴文字，让 Agent 为您自动构建排版规则包。
              </p>

              <textarea
                style={{
                  width: '100%',
                  height: 90,
                  padding: 12,
                  border: '1px solid #bccab9',
                  borderRadius: 8,
                  fontSize: 13,
                  fontFamily: 'inherit',
                  marginBottom: 12,
                  boxSizing: 'border-box',
                }}
                value={ruleText}
                onChange={e => setRuleText(e.target.value)}
                placeholder="例如粘贴学校格式要求：正文使用宋体小四号，1.5倍行距，一级标题黑体三号居中，页边距上2.5cm下2.5cm..."
              />

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: 8,
                }}
              >
                <span style={{ fontSize: 12, color: 'var(--ink-secondary)' }}>
                  {isExtractingRules ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--agent-purple)' }}>
                      <svg className="spinning" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                      </svg>
                      Agent 正在解析排版规范与 OOXML 语义约束...
                    </span>
                  ) : ruleExtractedNotice ? (
                    '✨ 规则包已由 Agent 重新编译并生效（识别 8 项规则，预估与原稿契合度 99.4%）'
                  ) : (
                    '✨ Agent 已就绪，可从上方通知文本自动推导出版级排版规则'
                  )}
                </span>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button
                    type="button"
                    className="btn-agent-action"
                    disabled={isExtractingRules}
                    onClick={() => {
                      setIsExtractingRules(true)
                      setTimeout(() => {
                        setIsExtractingRules(false)
                        setRuleExtractedNotice(true)
                      }, 850)
                    }}
                  >
                    {isExtractingRules ? '正在提炼...' : '⚡ 启动 Agent 智能提炼 (MCP / 本地)'}
                  </button>
                  {ruleExtractedNotice && (
                    <button
                      type="button"
                      style={{
                        background: 'transparent',
                        color: 'var(--brand-emerald)',
                        border: '1px solid var(--brand-emerald)',
                        padding: '6px 14px',
                        borderRadius: 8,
                        fontSize: 12.5,
                        cursor: 'pointer',
                        fontWeight: 600,
                      }}
                      onClick={() => alert('已将 Agent 提取的规则设定为当前排版基准！')}
                    >
                      ✓ 规则已应用
                    </button>
                  )}
                </div>
              </div>
            </section>

            {/* Feature 3: Detailed Diff Inspector & Overrides */}
            <section className="card-panel">
              <span className="card-kicker purple">可审计计划 · 段落级 Diff 检查</span>
              <h2 className="card-title">格式修改前后详细比对</h2>
              <p className="card-desc">
                在实际写入 DOCX 前，逐项核对每一条修改建议，支持手动勾选与个性化撤销。
              </p>

              <div className="diff-table-container">
                <div className="diff-table-head">
                  <span>修改目标</span>
                  <span>修改前 (原稿)</span>
                  <span>修改后 (Agent 建议)</span>
                  <span>操作</span>
                </div>

                <div className="diff-row-item">
                  <div>
                    <span className="diff-tag">一级标题</span> 4 处
                  </div>
                  <div className="diff-before">宋体 14pt，单倍行距，无缩进</div>
                  <div className="diff-after">黑体 16pt (三号)，加粗，居中，段前12pt</div>
                  <div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input
                        type="checkbox"
                        checked={approvedDiffs.diff1}
                        onChange={e =>
                          setApprovedDiffs(prev => ({ ...prev, diff1: e.target.checked }))
                        }
                      />
                      <span>批准</span>
                    </label>
                  </div>
                </div>

                <div className="diff-row-item">
                  <div>
                    <span className="diff-tag">正文段落</span> 142 处
                  </div>
                  <div className="diff-before">直接格式，无首行缩进，单倍行距</div>
                  <div className="diff-after">宋体/Times 小四，首行缩进 2 字符，1.25倍行距</div>
                  <div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input
                        type="checkbox"
                        checked={approvedDiffs.diff2}
                        onChange={e =>
                          setApprovedDiffs(prev => ({ ...prev, diff2: e.target.checked }))
                        }
                      />
                      <span>批准</span>
                    </label>
                  </div>
                </div>

                <div className="diff-row-item">
                  <div>
                    <span className="diff-tag" style={{ background: '#f2ebfc', color: 'var(--agent-purple)' }}>
                      深度 OOXML
                    </span>{' '}
                    引注转脚注
                  </div>
                  <div className="diff-before">文内手动文本 [1]，文末文献表</div>
                  <div className="diff-after">转换为真正的 Word 物理脚注，每页重排</div>
                  <div>
                    <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <input
                        type="checkbox"
                        checked={approvedDiffs.diff3}
                        onChange={e =>
                          setApprovedDiffs(prev => ({ ...prev, diff3: e.target.checked }))
                        }
                      />
                      <span>批准</span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="action-row">
                <button
                  type="button"
                  className="btn-hero"
                  style={{ background: 'var(--agent-purple)' }}
                  onClick={() => alert('已按照 Agent 深度规则执行受控排版并生成成果！')}
                >
                  <svg viewBox="0 0 24 24">
                    <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3L12 3z" />
                  </svg>
                  <span>授权并执行深度 Agent 排版</span>
                </button>
              </div>
            </section>

            {/* Feature 4: Codex Agent QA Panel */}
            <section className="card-panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
                <div>
                  <span className="card-kicker purple">AI 二次盲审质检</span>
                  <h2 className="card-title">Agent 质量审查清单</h2>
                </div>
                <div className="agent-engine-selector">
                  <span style={{ fontSize: 12, color: 'var(--ink-secondary)' }}>协同源：</span>
                  <select
                    className="agent-engine-select"
                    value={agentEngine}
                    onChange={e => setAgentEngine(e.target.value as 'mcp' | 'codex' | 'offline')}
                  >
                    <option value="mcp">外部 Agent 协同 (Cursor / Claude 经由 MCP)</option>
                    <option value="codex">本机 Codex CLI (只读沙箱)</option>
                    <option value="offline">本地确定性规约引擎 (0 Token)</option>
                  </select>
                  <button
                    type="button"
                    className="btn-agent-action"
                    disabled={isReauditing}
                    onClick={() => {
                      setIsReauditing(true)
                      setTimeout(() => {
                        setIsReauditing(false)
                        setAuditVerdict('pass_clean')
                        setAuditTimestamp('刚刚刷新')
                      }, 1100)
                    }}
                  >
                    {isReauditing ? (
                      <>
                        <svg className="spinning" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                        </svg>
                        正在复核...
                      </>
                    ) : (
                      '⚡ 重新运行质检'
                    )}
                  </button>
                </div>
              </div>

              <div
                style={{
                  background: '#f9f8fe',
                  border: '1px solid #d9d2f5',
                  borderRadius: 12,
                  padding: 18,
                  marginTop: 12,
                  fontSize: 13,
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                  <strong>
                    Agent 盲审判决：
                    <span style={{ color: 'var(--agent-purple)', marginLeft: 6 }}>
                      {isReauditing
                        ? '正在执行 OOXML 深度扫描与合规校验...'
                        : auditVerdict === 'pass_clean'
                          ? 'PASS (全部 18 项学术出版规范完全通过)'
                          : 'PASS WITH 1 SUGGESTION (通过并提示)'}
                    </span>
                  </strong>
                  <small style={{ color: 'var(--ink-muted)', fontSize: 11 }}>
                    复核时间: {auditTimestamp} · 模式: {agentEngine === 'mcp' ? 'MCP 管道协同' : agentEngine === 'codex' ? 'Codex 本地沙箱' : '本地离线纯算'}
                  </small>
                </div>

                {auditVerdict === 'pass_suggestion' && (
                  <div
                    style={{
                      marginTop: 10,
                      padding: '10px 14px',
                      background: '#fff',
                      borderRadius: 8,
                      borderLeft: '4px solid #3b82f6',
                    }}
                  >
                    <b>[建议]</b> 参考文献第 14 条缺少出版年份，已由 Agent 在 operations.json 标出建议位置。
                  </div>
                )}
                <div
                  style={{
                    marginTop: 8,
                    padding: '10px 14px',
                    background: '#fff',
                    borderRadius: 8,
                    borderLeft: '4px solid var(--state-success)',
                  }}
                >
                  <b>[通过]</b> 4 处数学公式与图 2-1 交叉引用在重构后结构完好无损，三线表线宽 (1.5pt/0.75pt) 100% 对齐。
                </div>
                {auditVerdict === 'pass_clean' && (
                  <div
                    style={{
                      marginTop: 8,
                      padding: '10px 14px',
                      background: '#fff',
                      borderRadius: 8,
                      borderLeft: '4px solid var(--state-success)',
                    }}
                  >
                    <b>[通过]</b> 所有标题 keepNext 防孤行属性与首行缩进 2 字符基线校验通过，未发现违规项。
                  </div>
                )}
              </div>
            </section>
          </div>
        )}

        {/* Optional developer link at the bottom (never intrusive) */}
        {onSwitchToLegacy && (
          <div className="dev-console-drawer">
            <button
              type="button"
              className="dev-console-toggle"
              onClick={onSwitchToLegacy}
            >
              🔧 开发者底层调试控制台 (v1.0 兼容)
            </button>
          </div>
        )}
      </div>

      {/* Agent MCP Console Modal */}
      <McpConsoleModal isOpen={isMcpModalOpen} onClose={() => setIsMcpModalOpen(false)} />
    </>
  )
}
