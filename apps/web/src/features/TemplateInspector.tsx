import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  api,
  errorMessage,
  type TemplateCombinedPreview,
  type TemplateInspection,
  type TemplateSectionStructureConfig,
  type TemplateSectionUpdate,
} from '../lib/api'

const roleLabels: Record<string, string> = {
  abstract_body: '摘要正文',
  abstract_heading: '摘要标题',
  bibliography_heading: '参考文献标题',
  body: '正文',
  figure_caption: '图题',
  heading_1: '一级标题',
  heading_2: '二级标题',
  heading_3: '三级标题',
  keywords: '关键词',
  paper_title: '论文标题',
  reference_entry: '参考文献条目',
  table_body: '表格正文',
  table_caption: '表题',
}

export function TemplateInspector() {
  const [open, setOpen] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const inspection = useMutation({ mutationFn: () => api.inspectTemplate(file!) })

  return <div className="rule-builder template-inspector">
    <button className="ghost rule-builder-toggle" type="button" onClick={() => setOpen(value => !value)}>
      {open ? '收起学校模板分析' : '分析学校 DOCX 模板'}
    </button>
    {open && <div className="rule-builder-body">
      <div className="rule-builder-intro">
        <div><strong>学校模板预检</strong><p>先只读扫描结构；如需填写字段，审核计划后生成新的 DOCX 副本。</p></div>
      </div>
      <div className="rule-source-actions">
        <label className="file-button">选择模板 DOCX
          <input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => { setFile(event.target.files?.[0] ?? null); inspection.reset() }} />
          <small>{file ? `${file.name} · ${Math.ceil(file.size / 1024)} KiB` : '最大 50 MiB'}</small>
        </label>
        <button className="primary" type="button" disabled={!file || inspection.isPending} onClick={() => inspection.mutate()}>{inspection.isPending ? '正在分析…' : '分析模板结构'}</button>
      </div>
      {inspection.error && <div className="alert" role="alert">{errorMessage(inspection.error)}</div>}
      {inspection.data && file && <TemplateInspectionResult key={inspection.data.source_sha256} inspection={inspection.data} file={file} />}
    </div>}
  </div>
}

function TemplateInspectionResult({ inspection, file }: { inspection: TemplateInspection; file: File }) {
  const summary = inspection.summary
  const planned = inspection.capabilities.filter(item => item.status === 'planned')
  return <div className="template-result">
    <div className="template-result-head"><div><strong>{inspection.source_filename}</strong><small>SHA-256 · {inspection.source_sha256.slice(0, 12)}</small></div><span>{planned.length ? `${planned.length} 类能力待开发` : '当前能力可覆盖'}</span></div>
    <div className="template-metrics">
      <div><strong>{summary.sections}</strong><small>分节</small></div>
      <div><strong>{summary.used_styles}/{summary.styles}</strong><small>已用/全部样式</small></div>
      <div><strong>{summary.placeholders}</strong><small>占位符</small></div>
      <div><strong>{summary.content_controls}</strong><small>内容控件</small></div>
      <div><strong>{summary.fields}</strong><small>字段</small></div>
      <div><strong>{summary.text_boxes}</strong><small>文本框</small></div>
    </div>
    <div className="template-groups">
      <section><h4>能力覆盖</h4><div className="capability-list">{inspection.capabilities.map(item => <article className={item.status} key={item.id}><span>{item.status === 'supported' ? '已支持' : '待开发'}</span><div><strong>{item.label}</strong><p>{item.detail}</p></div><b>{item.evidence_count}</b></article>)}</div></section>
      <section><h4>分节与页码</h4><div className="section-list">{inspection.sections.map(section => <article key={section.section_index}><strong>第 {section.section_index + 1} 节</strong><span>{section.page_number_format ? `${section.page_number_format} · 从 ${section.page_number_start ?? '继承'} 开始` : '继承页码设置'}</span><small>{section.references?.length ?? 0} 个页眉页脚引用{section.different_first_page ? ' · 首页不同' : ''}{section.inherits_headers || section.inherits_footers ? ' · 存在前节继承' : ''}</small></article>)}</div></section>
    </div>
    {(inspection.placeholders.length > 0 || inspection.content_controls.length > 0) && <details className="template-details" open><summary>字段候选（{inspection.placeholders.length + inspection.content_controls.length}）</summary><div>{inspection.placeholders.map(item => <article key={`${item.part_name}-${item.token}`}><code>{item.token}</code><span>{item.story}{item.in_text_box ? ' · 文本框' : ''}</span><b>{item.occurrences} 处</b></article>)}{inspection.content_controls.map((item, index) => <article key={`${item.part_name}-${item.tag}-${index}`}><code>{item.tag ?? item.alias ?? '未命名内容控件'}</code><span>{item.story} · 内容控件</span><b>1 处</b></article>)}</div></details>}
    {inspection.semantic_candidates.length > 0 && <details className="template-details"><summary>语义映射候选（{inspection.semantic_candidates.length}）</summary><div>{inspection.semantic_candidates.slice(0, 30).map(item => <article key={`${item.role}-${item.style_id}-${item.stable_id}`}><strong>{roleLabels[item.role] ?? item.role}</strong><span>{item.style_id ?? '无样式'} · {item.text_preview || '空段落'}</span><b>{Math.round(item.confidence * 100)}% · {item.occurrences}</b></article>)}</div></details>}
    <TemplateCombinedWorkspace inspection={inspection} file={file} />
    {(inspection.warnings ?? []).map(warning => <div className="warning" key={warning}>{warning}</div>)}
  </div>
}

type FillField = { key: string; label: string; mechanisms: string[]; locations: number }

function templateFields(inspection: TemplateInspection): FillField[] {
  const fields = new Map<string, FillField>()
  const add = (key: string, label: string, mechanism: string, locations: number) => {
    const existing = fields.get(key)
    if (existing) {
      existing.locations += locations
      if (!existing.mechanisms.includes(mechanism)) existing.mechanisms.push(mechanism)
    } else {
      fields.set(key, { key, label, mechanisms: [mechanism], locations })
    }
  }
  inspection.placeholders.forEach(item => add(item.key, item.key, '占位符', item.occurrences))
  inspection.content_controls.forEach(item => {
    const key = item.tag ?? item.alias
    if (key) add(key, item.alias ?? item.tag ?? key, '内容控件', 1)
  })
  return [...fields.values()].sort((left, right) => left.key.localeCompare(right.key, 'zh-CN'))
}

function TemplateCombinedWorkspace({ inspection, file }: { inspection: TemplateInspection; file: File }) {
  const fields = useMemo(() => templateFields(inspection), [inspection])
  const [values, setValues] = useState<Record<string, string>>({})
  const [editors, setEditors] = useState(() => initialSectionEditors(inspection))
  const [evenAndOdd, setEvenAndOdd] = useState(inspection.even_and_odd_headers ?? false)
  const configuration = sectionConfiguration(inspection, editors, evenAndOdd)
  const hasFill = Object.keys(submittedValues(values)).length > 0
  const hasStructure = (configuration.sections?.length ?? 0) > 0 || configuration.even_and_odd_headers !== undefined
  const preview = useMutation({
    mutationFn: () => api.previewTemplateCombined(file, submittedValues(values), configuration, inspection.source_sha256),
  })
  const generate = useMutation({
    mutationFn: (plan: TemplateCombinedPreview) => api.combinedTemplate(file, submittedValues(values), configuration, plan),
    onSuccess: result => {
      triggerDownload(result)
    },
  })

  const updateValue = (key: string, value: string) => {
    setValues(current => ({ ...current, [key]: value }))
    preview.reset()
    generate.reset()
  }
  const updateEditor = (index: number, patch: Partial<SectionEditor>) => {
    setEditors(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item))
    preview.reset()
    generate.reset()
  }
  const updateEvenAndOdd = (checked: boolean) => {
    setEvenAndOdd(checked)
    preview.reset()
    generate.reset()
  }

  return <section className="template-fill combined">
    <div className="template-fill-head">
      <div><h4>填写字段 + 分节页码与页眉页脚</h4><p>一次组合执行：先原子填写字段，再设置分节页码和链接关系，最终生成一个 DOCX 副本。留空字段或保持现状的分节不受影响。</p></div>
      <span>{fields.length} 个字段 · {inspection.sections.length} 个分节</span>
    </div>
    {fields.length > 0 && <div className="template-fill-fields">
      {fields.map(field => <label key={field.key}>
        <span><strong>{field.label}</strong><small>{field.key} · {field.mechanisms.join(' / ')} · {field.locations} 处</small></span>
        <input value={values[field.key] ?? ''} maxLength={20000} placeholder={`填写 ${field.label}`} onChange={event => updateValue(field.key, event.target.value)} />
      </label>)}
    </div>}
    {fields.length === 0 && <div className="template-fill empty">当前模板没有可安全填写的显式字段；可仅调整分节页码与页眉页脚，或在 Word 模板中加入占位符。</div>}
    <div className="section-structure">
      <label className="structure-global"><input type="checkbox" checked={evenAndOdd} onChange={event => updateEvenAndOdd(event.target.checked)} /> 启用奇偶页不同的页眉页脚</label>
      <div className="section-editors">
        {inspection.sections.map((section, index) => {
          const editor = editors[index]
          return <article key={section.section_index}>
            <header><strong>第 {index + 1} 节</strong><small>{section.inherits_headers ? '页眉继承' : '页眉独立'} · {section.inherits_footers ? '页脚继承' : '页脚独立'}</small></header>
            <label><span>页码格式</span><select aria-label={`第 ${index + 1} 节页码格式`} value={editor.format} onChange={event => updateEditor(index, { format: event.target.value })}><option value="">继承 / Word 默认</option>{Object.entries(pageNumberLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            <label><span>起始页码</span><input aria-label={`第 ${index + 1} 节起始页码`} type="number" min="0" max="32767" value={editor.start} placeholder="连续编号" onChange={event => updateEditor(index, { start: event.target.value })} /></label>
            <label><span>页眉</span><select aria-label={`第 ${index + 1} 节页眉关系`} value={editor.headerMode} onChange={event => updateEditor(index, { headerMode: event.target.value as SectionEditor['headerMode'] })}><option value="keep">保持现状</option>{index > 0 && <option value="inherit">继承前一节</option>}<option value="independent_copy">复制为独立部件</option></select></label>
            <label><span>页脚</span><select aria-label={`第 ${index + 1} 节页脚关系`} value={editor.footerMode} onChange={event => updateEditor(index, { footerMode: event.target.value as SectionEditor['footerMode'] })}><option value="keep">保持现状</option>{index > 0 && <option value="inherit">继承前一节</option>}<option value="independent_copy">复制为独立部件</option></select></label>
            <label className="structure-check"><input type="checkbox" checked={editor.differentFirstPage} onChange={event => updateEditor(index, { differentFirstPage: event.target.checked })} /> 首页不同</label>
          </article>
        })}
      </div>
    </div>
    <div className="template-fill-actions">
      <button className="primary" type="button" disabled={(!hasFill && !hasStructure) || preview.isPending} onClick={() => preview.mutate()}>{preview.isPending ? '正在生成组合计划…' : '预览组合计划'}</button>
      {preview.data && <span>计划版本 · {preview.data.plan_version.slice(0, 10)}</span>}
    </div>
    {preview.error && <div className="alert" role="alert">{errorMessage(preview.error)}</div>}
    {preview.data && <CombinedPreview plan={preview.data} pending={generate.isPending} onGenerate={() => generate.mutate(preview.data!)} />}
    {generate.error && <div className="alert" role="alert">{errorMessage(generate.error)}</div>}
    {generate.isSuccess && <div className="capability-gate"><strong>已组合执行并下载 DOCX 副本</strong><small>原模板未被覆盖；字段填写与分节结构同在一个副本中，已通过完整性验证。</small></div>}
  </section>
}

function CombinedPreview({ plan, pending, onGenerate }: { plan: TemplateCombinedPreview; pending: boolean; onGenerate: () => void }) {
  const fill = plan.fill
  const structure = plan.structure
  const blockers = [...(plan.blockers ?? [])]
  const totalOperations = fill.operations.length + structure.operations.length
  return <div className={`fill-preview ${plan.can_generate ? '' : 'blocked'}`}>
    <div className="fill-preview-metrics">
      <div><strong>{fill.replacement_count}</strong><small>将替换位置</small></div>
      <div><strong>{structure.operations.length}</strong><small>结构操作</small></div>
      <div><strong>{totalOperations}</strong><small>合计操作</small></div>
      <div><strong>{blockers.length}</strong><small>阻塞项</small></div>
    </div>
    <details className="template-details" open><summary>字段填写（{fill.operations.length}）</summary><div>{fill.operations.map(item => <article className="fill-operation" key={item.operation_id}><code>{item.key}</code><span>{item.mechanism === 'placeholder' ? '占位符' : '内容控件'} · {item.story} · {item.value_preview}</span><b>{item.occurrences} 处</b></article>)}{fill.missing_keys?.map(key => <div className="warning" key={key}>未提供值，保留原样：{key}</div>)}{fill.unused_keys?.map(key => <div className="warning" key={key}>模板中未找到：{key}</div>)}</div></details>
    <details className="template-details"><summary>分节结构（{structure.operations.length}）</summary><div>{structure.operations.map(item => <article className="fill-operation" key={item.operation_id}><code>{item.section_index === null || item.section_index === undefined ? '全文' : `第 ${item.section_index + 1} 节`}</code><span>{item.detail}</span><b>{item.risk === 'medium' ? '结构复制' : '属性修改'}</b></article>)}</div></details>
    {blockers.map(blocker => <div className="warning" key={blocker}>{blocker}</div>)}
    <button className="primary" type="button" disabled={!plan.can_generate || pending} onClick={onGenerate}>{pending ? '正在验证并生成…' : '生成并下载组合 DOCX'}</button>
  </div>
}

type SectionEditor = {
  format: string
  start: string
  differentFirstPage: boolean
  headerMode: 'keep' | 'inherit' | 'independent_copy'
  footerMode: 'keep' | 'inherit' | 'independent_copy'
}

const pageNumberLabels: Record<string, string> = {
  decimal: '阿拉伯数字（1, 2, 3）',
  lowerRoman: '小写罗马数字（i, ii, iii）',
  upperRoman: '大写罗马数字（I, II, III）',
  lowerLetter: '小写字母（a, b, c）',
  upperLetter: '大写字母（A, B, C）',
}

function initialSectionEditors(inspection: TemplateInspection): SectionEditor[] {
  return inspection.sections.map(section => ({
    format: section.page_number_format ?? '',
    start: section.page_number_start === null || section.page_number_start === undefined ? '' : String(section.page_number_start),
    differentFirstPage: section.different_first_page ?? false,
    headerMode: 'keep',
    footerMode: 'keep',
  }))
}

function sectionConfiguration(
  inspection: TemplateInspection,
  editors: SectionEditor[],
  evenAndOdd: boolean,
): TemplateSectionStructureConfig {
  const sections: TemplateSectionUpdate[] = []
  inspection.sections.forEach((current, index) => {
    const editor = editors[index]
    const update: TemplateSectionUpdate = {
      section_index: index,
      clear_page_numbering: false,
      clear_page_number_start: false,
      header_mode: 'keep',
      footer_mode: 'keep',
    }
    let changed = false
    const currentFormat = current.page_number_format ?? ''
    if (editor.format !== currentFormat) {
      if (!editor.format) update.clear_page_numbering = true
      else update.page_number_format = editor.format as TemplateSectionUpdate['page_number_format']
      changed = true
    }
    if (!update.clear_page_numbering) {
      const currentStart = current.page_number_start === null || current.page_number_start === undefined ? '' : String(current.page_number_start)
      if (editor.start !== currentStart) {
        if (editor.start === '') update.clear_page_number_start = true
        else update.page_number_start = Number(editor.start)
        changed = true
      }
    }
    if (editor.differentFirstPage !== (current.different_first_page ?? false)) {
      update.different_first_page = editor.differentFirstPage
      changed = true
    }
    if (editor.headerMode !== 'keep') {
      update.header_mode = editor.headerMode
      changed = true
    }
    if (editor.footerMode !== 'keep') {
      update.footer_mode = editor.footerMode
      changed = true
    }
    if (changed) sections.push(update)
  })
  return {
    sections,
    ...(evenAndOdd !== (inspection.even_and_odd_headers ?? false) ? { even_and_odd_headers: evenAndOdd } : {}),
  }
}

function triggerDownload(result: { blob: Blob; filename: string }) {
  const url = URL.createObjectURL(result.blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = result.filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function submittedValues(values: Record<string, string>) {
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ''))
}
