import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  api,
  ApiError,
  errorMessage,
  type DocumentInspection,
  type JobPage,
  type JobView,
  type ManuscriptCompositionPreview,
  type PatchOperation,
  type TemplateCombinedPreview,
  type ValidationReport,
} from '../lib/api'
import { RulePackBuilder } from './RulePackBuilder'
import { TemplateInspector } from './TemplateInspector'
import { PrototypeAtelier } from './PrototypeAtelier'
import { SimpleWorkflow } from './SimpleWorkflow'
import { McpConsoleModal } from './McpConsoleModal'

const terminalStates = new Set(['completed', 'failed', 'cancelled'])
const maxDocumentBytes = 50 * 1024 * 1024

function formatBytes(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KiB` : `${(bytes / 1024 / 1024).toFixed(1)} MiB`
}

const roleLabels: Record<string, string> = {
  abstract_body: '摘要正文',
  abstract_heading: '摘要标题',
  bibliography_heading: '参考文献标题',
  body: '正文',
  citations: '数字引用',
  cross_references: '题注与交叉引用',
  figure_caption: '图题',
  footer: '页脚',
  header: '页眉',
  heading_1: '一级标题',
  heading_2: '二级标题',
  heading_3: '三级标题',
  heading_4: '四级标题',
  degree_label: '封面学位标识',
  cover_frontmatter: '封面与声明（保留）',
  figure_caption_en: '英文图题',
  table_caption: '中文表题',
  table_caption_en: '英文表题',
  caption_note: '图表附注',
  toc_heading: '目录标题',
  toc_entry_1: '一级目录项',
  toc_entry_2: '二级目录项',
  toc_entry_3: '三级目录项',
  figure_table_list_entry: '图表目录项',
  figure_list_heading: '图目录标题',
  table_list_heading: '表目录标题',
  symbols_heading: '符号说明标题',
  bibliography_group_heading: '书目分类标题',
  appendix_heading: '附录标题',
  appendix_body: '附录正文',
  acknowledgments_heading: '致谢标题',
  acknowledgments_body: '致谢正文',
  cv_heading: '作者简历标题',
  cv_body: '作者简历正文',
  template_instruction: '模板说明（保留）',
  template_placeholder: '模板占位（保留）',
  date_line: '落款日期（保留）',
  formula_paragraph: '含公式段落（保留）',
  keywords: '关键词',
  formula: '公式样式',
  numbering: '自动编号',
  notes: '注释与脚注',
  paper_title: '论文标题',
  reference_entry: '参考文献条目',
  table_body: '表格正文',
  toc: '目录',
}

const riskLabels: Record<string, string> = {
  drawing: '图形',
  embedded_object: '嵌入对象',
  external_link: '外部链接',
  field: '字段',
  formula: '公式',
  nested_table: '复杂表格',
  revision: '修订',
  text_box: '文本框',
}

const formatLabels: Record<string, string> = {
  alignment: '对齐',
  bold: '粗体',
  color: '颜色',
  east_asia_font: '中文字体',
  first_line_indent_pt: '首行缩进',
  bibliography: '参考文献编号',
  captions: '图表题编号',
  collapse_ranges: '连续序号合并',
  enabled: '启用',
  footer_distance_mm: '页脚距离',
  figure_label: '图题标签',
  header_distance_mm: '页眉距离',
  height_mm: '纸张高度',
  keep_together: '段中不分页',
  keep_with_next: '与下段同页',
  latin_font: '英文字体',
  hyperlinks: '目录超链接',
  left_indent_pt: '左缩进',
  line_spacing: '行距',
  line_spacing_mode: '行距类型',
  margin_bottom_mm: '下边距',
  margin_left_mm: '左边距',
  margin_right_mm: '右边距',
  margin_top_mm: '上边距',
  convert_endnotes: '尾注转脚注',
  convert_inline_citations: '正文引注转脚注',
  delete_bibliography: '删除文末参考文献',
  numbering_restart: '脚注编号重启',
  number_format: '脚注编号格式',
  math_font: '数学字体',
  max_level: '最深目录级别',
  min_level: '最浅目录级别',
  orientation: '方向',
  page_break_before: '段前分页',
  right_indent_pt: '右缩进',
  size_pt: '字号',
  sort_numbers: '引用序号排序',
  space_after_pt: '段后',
  space_before_pt: '段前',
  space_after_lines: '段后（行）',
  space_before_lines: '段前（行）',
  style_id: '当前样式 ID',
  style_name: '样式',
  strip_existing_prefix: '移除已有文本编号',
  table_label: '表题标签',
  update_on_open: '打开时更新',
  width_mm: '纸张宽度',
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === '') return '未设置'
  if (typeof value === 'boolean') return value ? '是' : '否'
  if (value === 'multiple') return '倍数行距'
  if (value === 'exact') return '固定值'
  if (value === 'at_least') return '最小值'
  return String(value)
}

type FormatValue = { path: string; label: string; value: string }

function flattenFormat(value: Record<string, unknown>, prefix = ''): FormatValue[] {
  return Object.entries(value).flatMap(([key, item]): FormatValue[] => {
    const path = prefix ? `${prefix}.${key}` : key
    if (Array.isArray(item)) {
      return item.flatMap((child, index) => (
        child && typeof child === 'object'
          ? flattenFormat(child as Record<string, unknown>, `${path}[${index}]`)
          : [{ path: `${path}[${index}]`, label: `${formatLabels[key] ?? key} ${index + 1}`, value: displayValue(child) }]
      ))
    }
    if (item && typeof item === 'object') {
      return flattenFormat(item as Record<string, unknown>, path)
    }
    return [{ path, label: formatLabels[key] ?? key, value: displayValue(item) }]
  })
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

export function Workflow() {
  const [formattingMode, setFormattingMode] = useState<'standardize' | 'preserve'>('standardize')
  const queryClient = useQueryClient()
  const [file, setFile] = useState<File | null>(null)
  const [templateFile, setTemplateFile] = useState<File | null>(null)
  const [templateProblem, setTemplateProblem] = useState<string | null>(null)
  const [fileProblem, setFileProblem] = useState<string | null>(null)
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const [rulePackId, setRulePackId] = useState('zh-thesis-default')
  const [jobId, setJobId] = useState<string | null>(() => localStorage.getItem('paper-setting.active-job'))
  const [selectedOverride, setSelectedOverride] = useState<Set<string> | null>(null)
  const [manualReviewConfirmed, setManualReviewConfirmed] = useState(false)
  const [filter, setFilter] = useState('all')
  const [eventsConnected, setEventsConnected] = useState(false)
  const [deleteConfirmationOpen, setDeleteConfirmationOpen] = useState(false)
  const [taskNotice, setTaskNotice] = useState<string | null>(null)
  const [viewMode, setViewMode] = useState<'simple' | 'workflow' | 'atelier'>('simple')
  const [isMcpModalOpen, setIsMcpModalOpen] = useState(false)

  const rulePacks = useQuery({ queryKey: ['rule-packs'], queryFn: api.listRulePacks })
  const history = useQuery({
    queryKey: ['jobs'],
    queryFn: () => api.listJobs(5),
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
      return eventsConnected ? 15000 : 2000
    },
  })
  const currentJob = job.data ?? null
  useJobEvents(jobId, currentJob?.status, setEventsConnected)
  useEffect(() => {
    if (jobId) localStorage.setItem('paper-setting.active-job', jobId)
    else localStorage.removeItem('paper-setting.active-job')
  }, [jobId])
  useEffect(() => {
    if (!currentJob) return
    queryClient.setQueryData<JobPage>(['jobs'], current => {
      if (!current) return current
      return {
        ...current,
        items: current.items.map(item => item.id === currentJob.id ? currentJob : item),
      }
    })
  }, [currentJob, queryClient])
  const restoredJobMissing = job.error instanceof ApiError && job.error.status === 404

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
  const inspection = useQuery({
    queryKey: ['inspection', jobId, currentJob?.plan_version],
    queryFn: () => api.getInspection(jobId!),
    enabled: Boolean(jobId && currentJob?.plan_version && (currentJob?.mode !== 'template' || currentJob?.template_filename)),
  })
  const artifacts = useQuery({
    queryKey: ['artifacts', jobId],
    queryFn: () => api.listArtifacts(jobId!),
    enabled: currentJob?.status === 'completed',
  })
  const report = useQuery({
    queryKey: ['report', jobId],
    queryFn: () => api.getReport(jobId!),
    enabled: currentJob?.status === 'completed',
  })

  const defaultSelected = useMemo(
    () => new Set(
      (plan.data?.operations ?? [])
        .filter(operation => operation.status === 'proposed' && operation.risk === 'low')
        .map(operation => operation.operation_id),
    ),
    [plan.data],
  )
  const selected = selectedOverride ?? defaultSelected
  const selectedManualOperations = useMemo(
    () => (plan.data?.operations ?? []).filter(
      operation => operation.status === 'manual_review' && selected.has(operation.operation_id),
    ),
    [plan.data, selected],
  )
  const selectedDeepOperations = useMemo(
    () => selectedManualOperations.filter(
      operation => operation.execution_scope === 'controlled_ooxml_rewrite',
    ),
    [selectedManualOperations],
  )

  const createJob = useMutation({
    mutationFn: () => api.createJob(file!, rulePackId, false, templateFile, formattingMode),
    onSuccess: created => {
      setJobId(created.id)
      queryClient.setQueryData<JobPage>(['jobs'], current => ({
        items: [created, ...(current?.items ?? []).filter(item => item.id !== created.id)].slice(0, 5),
        next_cursor: current?.next_cursor ?? null,
      }))
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
  const importRulePack = useMutation({
    mutationFn: (ruleFile: File) => api.importRulePack(ruleFile),
    onSuccess: imported => {
      setRulePackId(imported.id)
      queryClient.invalidateQueries({ queryKey: ['rule-packs'] })
    },
  })
  const approve = useMutation({
    mutationFn: () => {
      if (currentJob?.mode === 'template') {
        const tp = templatePlan.data
        const approved = [
          ...(tp?.fill.operations ?? []).map(item => item.operation_id),
          ...(tp?.plan_kind === 'manuscript_composition' ? [tp.body_injection.operation_id] : []),
          ...(tp?.structure.operations ?? []).map(item => item.operation_id),
        ]
        return api.approve(jobId!, tp!.plan_version, approved, [], [])
      }
      const operations = plan.data?.operations ?? []
      const approved = [...selected]
      const rejected = operations.filter(item => !selected.has(item.operation_id)).map(item => item.operation_id)
      const confirmedManual = manualReviewConfirmed
        ? selectedManualOperations.map(item => item.operation_id)
        : []
      return api.approve(jobId!, plan.data!.plan_version, approved, rejected, confirmedManual)
    },
    onSuccess: approved => {
      queryClient.setQueryData(['job', approved.id], approved)
      queryClient.invalidateQueries({ queryKey: ['job', approved.id] })
    },
  })
  const cancel = useMutation({
    mutationFn: () => api.cancel(jobId!),
    onSuccess: cancelled => {
      queryClient.setQueryData(['job', cancelled.id], cancelled)
      queryClient.setQueryData<JobPage>(['jobs'], current => current ? {
        ...current,
        items: current.items.map(item => item.id === cancelled.id ? cancelled : item),
      } : current)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })
  const deleteJob = useMutation({
    mutationFn: () => api.deleteJob(jobId!),
    onSuccess: () => {
      const deletedJobId = jobId
      const deletedFilename = currentJob?.source_filename ?? '该任务'
      queryClient.removeQueries({ queryKey: ['job', jobId] })
      queryClient.setQueryData<JobPage>(['jobs'], current => current ? {
        ...current,
        items: current.items.filter(item => item.id !== deletedJobId),
      } : current)
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setJobId(null)
      setFile(null)
      setTemplateFile(null)
      setTemplateProblem(null)
      setFileProblem(null)
      setSelectedOverride(null)
      setManualReviewConfirmed(false)
      setFilter('all')
      setDeleteConfirmationOpen(false)
      setTaskNotice(`已删除“${deletedFilename}”及其所有相关文件。`)
    },
  })
  const filteredOperations = useMemo(() => {
    const operations = plan.data?.operations ?? []
    return filter === 'all' ? operations : operations.filter(item => item.risk === filter || item.semantic_role === filter)
  }, [filter, plan.data])
  const problem = importRulePack.error ?? createJob.error ?? job.error ?? inspection.error ?? plan.error ?? templatePlan.error ?? approve.error ?? cancel.error ?? deleteJob.error ?? history.error ?? report.error ?? artifacts.error
  const currentStep = currentJob?.status === 'completed'
    ? 3
    : currentJob?.plan_version
      ? 2
      : jobId
        ? 1
        : 0

  const navigateToStep = (index: number) => {
    if (index > currentStep) return
    if (index === 0 && jobId) {
      reset()
      window.requestAnimationFrame(() => document.getElementById('upload-stage')?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
      return
    }
    const targetCandidates = [
      ['upload-stage'],
      ['inspection-stage', 'job-status-stage'],
      ['plan-stage', 'result-stage', 'job-status-stage'],
      ['result-stage'],
    ]
    const target = targetCandidates[index]
      .map(id => document.getElementById(id))
      .find((element): element is HTMLElement => Boolean(element))
    target?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const reset = () => {
    queryClient.invalidateQueries({ queryKey: ['jobs'] })
    setJobId(null)
    setFile(null)
    setTemplateFile(null)
    setTemplateProblem(null)
    setFileProblem(null)
    setIsDraggingFile(false)
    setSelectedOverride(null)
    setManualReviewConfirmed(false)
    setFilter('all')
    setDeleteConfirmationOpen(false)
  }

  const selectDocument = (candidate: File | null) => {
    if (!candidate) return
    if (!/\.docx?$/i.test(candidate.name)) {
      setFile(null)
      setFileProblem('请选择 .doc 或 .docx 格式的 Word 文档。')
      return
    }
    if (candidate.size > maxDocumentBytes) {
      setFile(null)
      setFileProblem('文档超过 50 MiB，请压缩图片或移除不必要的附件后重试。')
      return
    }
    setFile(candidate)
    setFileProblem(null)
  }

  const selectTemplate = (candidate: File | null) => {
    if (!candidate) return
    if (!candidate.name.toLowerCase().endsWith('.docx')) {
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
    setTemplateProblem(null)
  }

  if (viewMode === 'simple') {
    return <SimpleWorkflow onSwitchToLegacy={() => setViewMode('workflow')} />
  }

  if (viewMode === 'atelier') {
    return <PrototypeAtelier onBackToWorkflow={() => setViewMode('simple')} />
  }

  return <main className="workspace">
    <header className="hero">
      <div className="hero-copy">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
          <button
            type="button"
            className="btn-pill"
            style={{ background: 'var(--green)', color: '#fff', border: 'none', padding: '6px 14px', borderRadius: 16 }}
            onClick={() => setViewMode('simple')}
          >
            ← 返回现代工作台 (v1.1)
          </button>
          <span style={{ fontSize: 13, color: '#68736b' }}>专家与底层调试控制台</span>
        </div>
        <h1>论文排版台 <em>让格式归位，让内容保持原样。</em></h1>
        <div className="proof-note" aria-label="校样原则">
          <span>校样原则</span><strong>原稿只读</strong><strong>另存副本</strong><strong>完整复核</strong>
          <button
            type="button"
            className="launch-atelier-btn"
            onClick={() => setViewMode('atelier')}
          >
            ✨ 交互原型透视实验室 (X-Ray / A4 舞台)
          </button>
        </div>
      </div>
    </header>

    <div className="app-shell">
      <aside className="left-rail">
        <nav className="steps" aria-label="处理步骤">
          {[
            ['上传文稿', '选择 DOC / DOCX 与规则'],
            ['文档检查', '识别结构与风险'],
            ['审核计划', '确认每一项修改'],
            ['验证下载', '获取成品与报告'],
          ].map(([label, detail], index) => <button
            key={label}
            type="button"
            className={`${currentStep >= index ? 'active' : ''} ${currentStep === index ? 'current' : ''}`}
            disabled={index > currentStep}
            aria-current={currentStep === index ? 'step' : undefined}
            onClick={() => navigateToStep(index)}
          ><i>{String(index + 1).padStart(2, '0')}</i><span><b>{label}</b><small>{detail}</small><span className="step-action" aria-hidden="true">{currentStep === index ? '当前' : '前往'} →</span></span></button>)}
          <div className="step-foot"><span>DOC / DOCX</span><small>最大 50 MiB</small></div>
        </nav>
        <JobHistory jobs={historyJobs} activeJobId={jobId} onOpen={setJobId} onOpenMcp={() => setIsMcpModalOpen(true)} />
      </aside>

      <section className="workflow-stage">
        {taskNotice && <div className="task-notice" role="status"><span>{taskNotice}</span><button type="button" aria-label="关闭提示" onClick={() => setTaskNotice(null)}>×</button></div>}
        {problem && <div className="alert" role="alert">{errorMessage(problem)}</div>}
        {restoredJobMissing && <button className="ghost" type="button" onClick={reset}>清除已失效的任务记录</button>}

    {!jobId && <section className="panel upload-panel" id="upload-stage">
      <div className="section-title"><span>01</span><div><h2>新建排版任务</h2><p>原文件只读复制，永不覆盖。</p></div></div>
      <label
        className={`dropzone ${file ? 'has-file' : ''} ${isDraggingFile ? 'is-dragging' : ''}`}
        onDragEnter={event => { event.preventDefault(); setIsDraggingFile(true) }}
        onDragOver={event => { event.preventDefault(); setIsDraggingFile(true) }}
        onDragLeave={() => setIsDraggingFile(false)}
        onDrop={event => { event.preventDefault(); setIsDraggingFile(false); selectDocument(event.dataTransfer.files?.[0] ?? null) }}
      >
        <input
          type="file"
          aria-label="选择论文 DOC 或 DOCX 文件"
          accept=".doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={event => { selectDocument(event.target.files?.[0] ?? null); event.currentTarget.value = '' }}
        />
        <span className="dropzone-kicker">{file ? '文稿已就绪' : '拖放或点击选择'}</span>
        <strong>{file ? file.name : '选择一个 DOC 或 DOCX 文件'}</strong>
        <small>{file ? formatBytes(file.size) : '最大 50 MiB · 支持 .doc / .docx'}</small>
        <span className="dropzone-action">{file ? '点击更换文稿' : '浏览本机文件'}</span>
      </label>
      {fileProblem && <div className="file-problem" role="alert">{fileProblem}</div>}
      {file?.name.toLowerCase().endsWith('.doc') && <div className="capability-gate" role="status"><strong>旧版 DOC 将先在本机转换为 DOCX</strong><small>最终下载仍为 DOCX；复杂域、宏、批注或精细分页可能变化。自动验证仅覆盖转换后的排版阶段，下载后请用 Word 与原 DOC 人工比对。</small></div>}
      <div className="form-grid">
        <label>排版模式<select value={formattingMode} disabled={Boolean(templateFile)} onChange={event => setFormattingMode(event.target.value as 'standardize' | 'preserve')}><option value="standardize">标准化排版（默认基线补全）</option><option value="preserve">保守排版（未规定项保留原文）</option></select><small>{templateFile ? '学校模板注入使用独立流程，不应用默认基线。' : formattingMode === 'standardize' ? '规则包优先；未规定项由过渡基线补全。正式默认模板待配置。' : '仅修改规则包明确规定的属性，其余格式保持原样。'}</small></label>
        <label>规则包<select value={rulePackId} onChange={event => setRulePackId(event.target.value)} disabled={rulePacks.isLoading}>{rulePacks.data?.map(item => <option disabled={!item.capability_report.executable} key={item.id} value={item.id}>{item.name} · v{item.version}{item.capability_report.executable ? '' : ' · 不可执行'}</option>)}</select><span className="import-control">或导入 JSON<input type="file" accept="application/json,.json" onChange={event => { const ruleFile = event.target.files?.[0]; if (ruleFile) importRulePack.mutate(ruleFile) }} /></span></label>
      </div>
      <div className="template-upload">
        <div><strong>使用学校模板（可选）</strong><small>模板中放置 <code>{'{{document.body}}'}</code>，工作台会自动映射标题、摘要、关键词并注入整篇正文。</small></div>
        <label className="template-file-button">
          <input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => { selectTemplate(event.target.files?.[0] ?? null); event.currentTarget.value = '' }} />
          {templateFile ? '更换模板' : '选择模板'}
        </label>
        {templateFile && <span className="template-file-name"><b>{templateFile.name}</b><button type="button" onClick={() => { setTemplateFile(null); setTemplateProblem(null) }}>移除</button></span>}
      </div>
      {templateProblem && <div className="file-problem" role="alert">{templateProblem}</div>}
      {rulePackId === 'zh-thesis-deep' && <div className="xref-guide"><strong>需要生成图表交叉引用？</strong><span>在题注开头写 <code>[[xref-target:fig-system]]</code>，正文写 <code>[[xref:fig-system]]</code>，页码写 <code>[[xref-page:fig-system]]</code>。表目标使用 <code>tab-</code> 前缀。</span></div>}
      <RulePackBuilder onImported={imported => setRulePackId(imported.id)} />
      <TemplateInspector />
      <button className="primary" disabled={!file || createJob.isPending} onClick={() => createJob.mutate()}>{createJob.isPending ? '正在上传…' : '检查论文并生成计划'}</button>
    </section>}

    {jobId && currentJob && <section className="panel status-panel" id="job-status-stage">
      <div className="status-head"><div><span className={`status ${currentJob.status}`}>{currentJob.status}</span><h2>{currentJob.source_filename}</h2></div><div className="status-actions">{['uploaded', 'plan_ready'].includes(currentJob.status) && <button className="ghost danger" disabled={cancel.isPending} onClick={() => cancel.mutate()}>{cancel.isPending ? '取消中…' : '取消任务'}</button>}<button className="ghost" onClick={reset}>新建任务</button></div></div>
      <div className="progress"><i style={{ width: `${currentJob.progress}%` }} /></div>
      <div className="metrics"><div><small>当前阶段</small><strong>{currentJob.current_stage}</strong></div><div><small>进度</small><strong>{currentJob.progress}%</strong></div><div><small>规则包</small><strong>{currentJob.rule_pack_id}</strong></div></div>
      {currentJob.status === 'failed' && <div className="alert">{currentJob.error_code}: {currentJob.error_detail}</div>}
    </section>}

    {inspection.data && <InspectionPanel inspection={inspection.data} />}

    {plan.data && currentJob?.status === 'plan_ready' && <section className="panel plan-panel" id="plan-stage">
      <p>{plan.data.formatting_policy?.mode === 'standardize' ? '标准化排版：规则包 > 默认基线 > 原格式' : '保守排版：仅应用明确规则'}。未指定的加粗、斜体、上下标和受保护对象内部格式保留。</p>
      {plan.data.formatting_policy?.baseline && <p>默认基线：{plan.data.formatting_policy.baseline.name} · v{plan.data.formatting_policy.baseline.version}</p>}
      {plan.data.notices?.map(notice => <p key={notice} role="status">{notice}</p>)}
      <div className="section-title"><span>03</span><div><h2>审核修改计划</h2><p>{plan.data.summary.proposed ?? 0} 项低风险操作，{plan.data.summary.manual_review ?? 0} 项需明确确认，{plan.data.summary.compliant ?? 0} 项已经合规。</p></div></div>
      <div className="toolbar">
        <select value={filter} onChange={event => setFilter(event.target.value)}><option value="all">全部操作</option><option value="low">低风险</option><option value="medium">中风险</option><option value="high">高风险</option>{[...new Set(plan.data.operations.map(item => item.semantic_role))].sort().map(role => <option key={role} value={role}>{roleLabels[role] ?? role}</option>)}</select>
        <div className="selection-actions"><button className="ghost" onClick={() => { setSelectedOverride(new Set(plan.data.operations.map(item => item.operation_id))); setManualReviewConfirmed(false) }}>选择全部可排版项</button><button className="ghost" onClick={() => { setSelectedOverride(new Set()); setManualReviewConfirmed(false) }}>清空</button><span>已选择 {selected.size} 项</span></div>
      </div>
      <div className="operations">{filteredOperations.map(operation => <OperationRow key={operation.operation_id} operation={operation} checked={selected.has(operation.operation_id)} onChange={checked => setSelectedOverride(current => { const next = new Set(current ?? defaultSelected); if (checked) next.add(operation.operation_id); else next.delete(operation.operation_id); return next })} />)}</div>
      <div className="approval">
        <div><p>{selectedManualOperations.length ? `已选 ${selectedManualOperations.length} 项需复核操作${selectedDeepOperations.length ? `，其中 ${selectedDeepOperations.length} 项会执行受控 OOXML 重构` : ''}。所有变化都会进入完整性白名单和审计报告。` : '当前只选中了低风险操作。'}</p>{selectedManualOperations.length > 0 && <label className="manual-confirm"><input type="checkbox" checked={manualReviewConfirmed} onChange={event => setManualReviewConfirmed(event.target.checked)} />我已复核语义角色和深层操作，确认执行计划内的文本与 OOXML 变化</label>}</div>
        <button className="primary" disabled={approve.isPending || (selected.size === 0 && plan.data.operations.length > 0) || (selectedManualOperations.length > 0 && !manualReviewConfirmed)} onClick={() => approve.mutate()}>{approve.isPending ? '正在提交…' : plan.data.operations.length === 0 ? '确认无需修改并导出' : `批准并执行 ${selected.size} 项`}</button>
      </div>
    </section>}

    {templatePlan.data && currentJob?.status === 'plan_ready' && <TemplatePlanPanel
      plan={templatePlan.data}
      pending={approve.isPending}
      onApprove={() => approve.mutate()}
    />}

    {currentJob?.status === 'completed' && <section className="panel result-panel" id="result-stage">
      {report.data && <p>本次实际修改：规则包 {report.data.format_source_counts?.rule_pack ?? 0} 项属性，默认基线补全 {report.data.format_source_counts?.default_template ?? 0} 项属性。</p>}
      {report.data?.formatting_notices?.map(notice => <p key={notice}>{notice}</p>)}
      <div className="section-title"><span>04</span><div><h2>排版与完整性验证完成</h2><p>下载排版完成的 Word 文档。</p></div></div>
      {report.data && <OperationIssues report={report.data} />}
      {report.data && <AgentAuditSummary report={report.data} />}
      <div className="artifacts">{artifacts.data?.map(item => <a key={item.kind} href={api.artifactUrl(jobId!, item.kind)}><strong>{item.kind === 'agent_audit' ? 'Agent 审核报告' : completedFilename(currentJob.source_filename)}</strong><small>{formatBytes(item.size_bytes)}</small><span>{item.kind === 'agent_audit' ? '下载 JSON ↗' : '下载 Word ↗'}</span></a>)}</div>
    </section>}

    {currentJob && terminalStates.has(currentJob.status) && <section className="task-delete-zone" aria-label="删除任务">
      <div><strong>删除此任务</strong><p>同时删除该任务的历史记录、上传文件、内部报告和排版成品。</p></div>
      {deleteConfirmationOpen ? <div className="task-delete-confirm" role="alert">
        <span>此操作无法撤销，确定继续？</span>
        <button className="ghost" type="button" disabled={deleteJob.isPending} onClick={() => setDeleteConfirmationOpen(false)}>取消</button>
        <button className="danger-confirm" type="button" disabled={deleteJob.isPending} onClick={() => deleteJob.mutate()}>{deleteJob.isPending ? '正在删除…' : '确认永久删除'}</button>
      </div> : <button className="ghost danger" type="button" onClick={() => setDeleteConfirmationOpen(true)}>删除此任务</button>}
    </section>}
      </section>
    </div>
    <McpConsoleModal isOpen={isMcpModalOpen} onClose={() => setIsMcpModalOpen(false)} />
  </main>
}

function OperationRow({ operation, checked, onChange }: { operation: PatchOperation; checked: boolean; onChange: (checked: boolean) => void }) {
  const requiresConfirmation = operation.status === 'manual_review'
  const changed = new Set(operation.changed_fields ?? [])
  const isPage = operation.operation_type === 'apply_page_format'
  const before = flattenFormat(operation.before).filter(item => changed.has(item.path))
  const after = flattenFormat(operation.after).filter(item => (
    isPage
      ? [...changed].some(path => path.endsWith(`.${item.path}`))
      : changed.has(item.path)
  ))
  for (const item of after) {
    const source = operation.field_sources?.[item.path]
    if (source) item.value = `${item.value}（${source === 'rule_pack' ? '规则包' : '默认基线'}）`
  }
  return <label className={`operation ${requiresConfirmation ? 'requires-confirmation' : ''}`}>
    <input type="checkbox" checked={checked} onChange={event => onChange(event.target.checked)} />
    <div><div className="operation-meta"><span className={`risk ${operation.risk}`}>{operation.risk}</span><b>{roleLabels[operation.semantic_role] ?? operation.semantic_role}</b><small>{Math.round(operation.confidence * 100)}%</small>{requiresConfirmation && <span className="review-badge">需确认</span>}{operation.execution_scope === 'preserve_protected_content' && <span className="safe-scope-badge">保留对象</span>}{operation.execution_scope === 'controlled_ooxml_rewrite' && <span className="deep-scope-badge">受控重构</span>}</div><p>{operation.text_preview || '页面与分节设置'}</p><small>{(operation.reasons ?? []).join(' · ')}</small><details className="format-details" onClick={event => event.stopPropagation()}><summary>查看修改前后</summary><div className="format-diff"><FormatColumn title="修改前" values={before} empty="继承原文档设置" /><FormatColumn title="修改后" values={after} empty="无目标设置" /></div></details></div>
  </label>
}

function FormatColumn({ title, values, empty }: { title: string; values: FormatValue[]; empty: string }) {
  return <div><strong>{title}</strong>{values.length ? <dl>{values.map(({ path, label, value }) => <div key={path}><dt>{label}</dt><dd>{value}</dd></div>)}</dl> : <small>{empty}</small>}</div>
}

function InspectionPanel({ inspection }: { inspection: DocumentInspection }) {
  const summary = inspection.summary
  const advanced = inspection.advanced
  const roleCounts = summary.role_counts ?? {}
  const riskCounts = summary.risk_counts ?? {}
  return <section className="panel inspection-panel" id="inspection-stage">
    <div className="section-title"><span>02</span><div><h2>文档检查结果</h2><p>已建立稳定索引；受保护对象保留内部结构，可在复核后排版外层段落与普通文字。</p></div></div>
    <div className="summary-grid">
      <div><strong>{summary.paragraphs}</strong><small>正文段落</small></div>
      <div><strong>{summary.table_paragraphs}</strong><small>表格段落</small></div>
      <div><strong>{summary.headers + summary.footers}</strong><small>页眉页脚</small></div>
      <div><strong>{summary.protected_items}</strong><small>受保护对象</small></div>
    </div>
    <div className="inspection-groups">
      <div><h3>识别角色</h3><div className="chips">{Object.entries(roleCounts).sort((a, b) => b[1] - a[1]).map(([role, count]) => <span key={role}>{roleLabels[role] ?? role}<b>{count}</b></span>)}</div></div>
      <div><h3>复杂对象</h3>{Object.keys(riskCounts).length ? <div className="chips risks">{Object.entries(riskCounts).map(([risk, count]) => <span key={risk}>{riskLabels[risk] ?? risk}<b>{count}</b></span>)}</div> : <p className="muted">未检测到公式、字段、文本框或复杂表格。</p>}</div>
    </div>
    <div className="advanced-inspection"><h3>深层 Word 对象</h3><div className="chips">
      <span>公式<b>{advanced?.formula_count ?? 0}</b></span>
      <span>待规范数字引用<b>{advanced?.citation_candidate_count ?? 0}</b></span>
      <span>交叉引用目标<b>{advanced?.cross_reference_target_count ?? 0}</b></span>
      <span>REF 标记<b>{advanced?.cross_reference_marker_count ?? 0}</b></span>
      <span>PAGEREF 标记<b>{advanced?.cross_reference_page_marker_count ?? 0}</b></span>
      <span>已有交叉引用域<b>{advanced?.cross_reference_existing_field_count ?? 0}</b></span>
      <span>SEQ 图表编号<b>{Object.values(advanced?.sequence_numbered_role_counts ?? {}).reduce((sum, count) => sum + count, 0)}</b></span>
      <span>脚注<b>{advanced?.footnote_count ?? 0}</b></span>
      <span>尾注<b>{advanced?.endnote_count ?? 0}</b></span>
      <span>可转换正文引注<b>{advanced?.inline_note_candidate_count ?? 0}</b></span>
      <span>文末参考文献<b>{advanced?.bibliography_entry_count ?? 0}</b></span>
      <span>目录域<b>{advanced?.toc_instructions?.length ?? 0}</b></span>
      <span>已绑定自动编号<b>{Object.values(advanced?.numbered_role_counts ?? {}).reduce((sum, count) => sum + count, 0)}</b></span>
    </div></div>
    {(inspection.warnings ?? []).map(warning => <div className="warning" key={warning}>{warning}</div>)}
  </section>
}

function completedFilename(sourceFilename: string) {
  const dot = sourceFilename.lastIndexOf('.')
  const stem = dot > 0 ? sourceFilename.slice(0, dot) : sourceFilename
  return `${stem}排版完成.docx`
}

function OperationIssues({ report }: { report: ValidationReport }) {
  const operationCounts = report.operation_counts ?? {}
  const issueCount = (operationCounts.skipped ?? 0) + (operationCounts.failed ?? 0)
  if (!issueCount) return null
  return <div className="operation-issue-notice" role="alert" aria-live="assertive">
    <strong>有 {issueCount} 项操作未完成</strong>
    {(report.operation_issues ?? []).map((message, index) => <p key={`${index}-${message}`}>{message}</p>)}
  </div>
}

type AgentAuditIssue = { severity?: string; category?: string; location?: string; description?: string; recommendation?: string }

function AgentAuditSummary({ report }: { report: ValidationReport }) {
  const audit = report.agent_audit
  if (!audit || audit.status === 'disabled') return null
  if (audit.status !== 'completed') return <div className="operation-issue-notice"><strong>Agent 审核未完成</strong><p>{String(audit.detail ?? '请人工复核排版结果。')}</p></div>
  const issues = Array.isArray(audit.issues) ? audit.issues as AgentAuditIssue[] : []
  return <div className="operation-issue-notice" role="status">
    <strong>Agent 二次审核：{audit.verdict === 'pass' ? '通过' : audit.verdict === 'fail' ? '发现严重问题' : '建议复核'}</strong>
    <p>{String(audit.summary ?? '')}</p>
    {issues.map((issue, index) => <p key={`${index}-${issue.description}`}><b>[{issue.severity ?? 'medium'}] {issue.category ?? '排版'}</b>{issue.location ? ` · ${issue.location}` : ''}：{issue.description}{issue.recommendation ? `；建议：${issue.recommendation}` : ''}</p>)}
  </div>
}

function JobHistory({ jobs, activeJobId, onOpen, onOpenMcp }: { jobs: JobView[]; activeJobId: string | null; onOpen: (id: string) => void; onOpenMcp: () => void }) {
  const recentJobs = jobs.slice(0, 5)
  return <section className="job-history" aria-labelledby="recent-jobs-title">
    <div className="job-history-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
      <strong id="recent-jobs-title">最近任务</strong>
      <button
        type="button"
        className="mcp-entry-btn purple-accent"
        onClick={onOpenMcp}
        style={{ fontSize: 11, padding: '2px 8px', borderRadius: 8 }}
        title="打开 Agent MCP 协同控制中心"
      >
        <span className="pulse-dot green" />
        MCP
      </button>
    </div>
    {recentJobs.length > 0 ? (
      <div className="job-history-list">{recentJobs.map(item => <button
        className={item.id === activeJobId ? 'is-active' : ''}
        type="button"
        key={item.id}
        title={item.source_filename}
        aria-label={`打开任务：${item.source_filename}`}
        onClick={() => onOpen(item.id)}
      ><span className={`job-status-dot ${item.status}`} aria-hidden="true" /><span className="job-history-copy"><b>{item.source_filename}</b><small>{formatRecentTaskTime(item.created_at)}</small></span></button>)}</div>
    ) : (
      <div style={{ padding: '8px 4px', fontSize: 11.5, color: '#7a857e' }}>
        暂无任务，可直接拖放文稿或通过 MCP 提交。
      </div>
    )}
  </section>
}

function formatRecentTaskTime(value: string) {
  const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/.test(value)
  const date = new Date(hasTimezone ? value : `${value}Z`)
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Shanghai',
  }).format(date)
}

function TemplatePlanPanel({ plan, pending, onApprove }: { plan: TemplateCombinedPreview | ManuscriptCompositionPreview; pending: boolean; onApprove: () => void }) {
  const fill = plan.fill
  const structure = plan.structure
  const blockers = plan.blockers ?? []
  const composition = plan.plan_kind === 'manuscript_composition' ? plan : null
  const operationCount = fill.operations.length + structure.operations.length + (composition ? 1 : 0)
  return <section className="panel plan-panel" id="plan-stage">
    <div className="section-title"><span>03</span><div><h2>{composition ? '审核整篇正文注入计划' : '审核模板驱动计划'}</h2><p>{composition ? '原稿将被注入学校模板，标题、摘要和关键词按语义自动映射，原文档与模板均保持不变。' : '规则包将自动填写字段并设置分节页码与页眉页脚，组合成一个 DOCX 副本。'}</p></div></div>
    <div className="summary-grid">
      <div><strong>{fill.replacement_count}</strong><small>将替换字段位置</small></div>
      <div><strong>{composition?.body_injection.source_blocks ?? structure.operations.length}</strong><small>{composition ? '注入正文块' : '分节结构操作'}</small></div>
      <div><strong>{operationCount}</strong><small>合计操作</small></div>
      <div><strong>{blockers.length}</strong><small>阻塞项</small></div>
    </div>
    <div className="operations">
      {composition && <div className="mapping-summary">
        <h3>智能字段映射</h3>
        <div>{composition.mappings.map(item => <span className={item.source === 'unmapped' ? 'unmapped' : ''} key={item.key}><b>{item.key}</b><small>{item.source === 'unmapped' ? '未自动填写' : `${Math.round(item.confidence * 100)}% · ${item.value_preview}`}</small></span>)}</div>
      </div>}
      {composition && <div className="operation">
        <input type="checkbox" checked readOnly />
        <div><div className="operation-meta"><span className="risk medium">medium</span><b>整篇正文注入</b><small>{composition.body_injection.paragraph_blocks} 段 · {composition.body_injection.table_blocks} 表 · {composition.body_injection.image_relationships} 图</small></div><p>在 {`{{${composition.body_injection.anchor_key}}}`} 位置注入，并移除原稿分节属性，使页眉页脚继续由模板控制。</p></div>
      </div>}
      {fill.operations.map(item => <div className="operation" key={item.operation_id}>
        <input type="checkbox" checked readOnly />
        <div><div className="operation-meta"><span className="risk low">low</span><b>{item.key}</b><small>{item.mechanism === 'placeholder' ? '占位符' : '内容控件'} · {item.story}</small></div><p>{item.value_preview || item.key}</p><small>{item.occurrences} 处</small></div>
      </div>)}
      {structure.operations.map(item => <div className="operation" key={item.operation_id}>
        <input type="checkbox" checked readOnly />
        <div><div className="operation-meta"><span className={`risk ${item.risk}`}>{item.risk}</span><b>{item.section_index === null || item.section_index === undefined ? '全文' : `第 ${item.section_index + 1} 节`}</b><small>{item.operation_type}</small></div><p>{item.detail}</p></div>
      </div>)}
    </div>
    {blockers.map(blocker => <div className="warning" key={blocker}>{blocker}</div>)}
    <div className="approval">
      <div><p>{composition ? '正文注入、智能字段填写和分节结构将在同一个 DOCX 副本中原子执行。' : '整个模板组合将作为一次原子执行处理。'}所有变化进入完整性白名单和审计报告。</p></div>
      <button className="primary" disabled={pending || !plan.can_generate || blockers.length > 0} onClick={onApprove}>{pending ? '正在提交…' : composition ? '批准并生成模板成品' : '批准并执行模板组合'}</button>
    </div>
  </section>
}
