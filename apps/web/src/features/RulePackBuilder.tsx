import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api, errorMessage, type RulePackDraft, type RulePackSummary } from '../lib/api'

type Props = {
  onImported: (rulePack: RulePackSummary) => void
}

const example = `页面采用 A4 纸，纵向，上下边距 2.5cm，左边距 3cm，右边距 2.5cm。
正文：宋体，小四，Times New Roman，1.5 倍行距，首行缩进 2 字符，两端对齐。
一级标题：黑体，三号，加粗，居中，段前 12 磅，段后 6 磅。
注释一律采用脚注，文末不列参考文献。每页脚注重新编号，编号格式为带圈数字。`

export function RulePackBuilder({ onImported }: Props) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [sourceFile, setSourceFile] = useState<File | null>(null)
  const [name, setName] = useState('')
  const [rulePackId, setRulePackId] = useState('')
  const [draft, setDraft] = useState<RulePackDraft | null>(null)
  const [json, setJson] = useState('')

  const extract = useMutation({
    mutationFn: () => api.extractRulePack(text, sourceFile, name, rulePackId),
    onSuccess: result => {
      setDraft(result)
      setJson(JSON.stringify(result.rule_pack, null, 2))
    },
  })
  const importDraft = useMutation({
    mutationFn: () => api.importRulePackJson(json),
    onSuccess: imported => {
      queryClient.invalidateQueries({ queryKey: ['rule-packs'] })
      onImported(imported)
      setOpen(false)
    },
  })
  const problem = extract.error ?? importDraft.error

  return <div className="rule-builder">
    <button className="ghost rule-builder-toggle" type="button" onClick={() => setOpen(value => !value)}>
      {open ? '收起规则包生成器' : '从规范文本或文件生成规则包'}
    </button>
    {open && <div className="rule-builder-body">
      <div className="rule-builder-intro">
        <div><strong>规则包生成器</strong><p>本地解析 `.txt`、`.md` 和 `.docx`；先审核证据和 JSON，再正式导入。</p></div>
        <button className="ghost" type="button" onClick={() => setText(example)}>填入示例</button>
      </div>
      <div className="rule-builder-fields">
        <label>规则包名称<input value={name} onChange={event => setName(event.target.value)} placeholder="例：某大学硕士论文格式" /></label>
        <label>规则包 ID（可选）<input value={rulePackId} onChange={event => setRulePackId(event.target.value)} placeholder="university-thesis-2026" /></label>
      </div>
      <label className="rule-source-text">粘贴格式规范
        <textarea value={text} onChange={event => setText(event.target.value)} rows={8} placeholder={example} />
      </label>
      <div className="rule-source-actions">
        <label className="file-button">或选择规范文件
          <input type="file" accept=".txt,.md,.docx,text/plain,text/markdown,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onChange={event => setSourceFile(event.target.files?.[0] ?? null)} />
          <small>{sourceFile ? `${sourceFile.name} · ${Math.ceil(sourceFile.size / 1024)} KiB` : '最大 5 MiB'}</small>
        </label>
        <button className="primary" type="button" disabled={extract.isPending || (!text.trim() && !sourceFile)} onClick={() => extract.mutate()}>{extract.isPending ? '正在识别…' : '识别并生成草稿'}</button>
      </div>
      {problem && <div className="alert" role="alert">{errorMessage(problem)}</div>}
      {draft && <DraftReview draft={draft} json={json} setJson={setJson} importing={importDraft.isPending} onImport={() => importDraft.mutate()} />}
    </div>}
  </div>
}

function DraftReview({ draft, json, setJson, importing, onImport }: { draft: RulePackDraft; json: string; setJson: (value: string) => void; importing: boolean; onImport: () => void }) {
  return <div className="draft-review">
    <div className="draft-metrics">
      <div><strong>{draft.recognized_properties}</strong><small>已识别属性</small></div>
      <div><strong>{draft.rule_pack.roles.length}</strong><small>语义角色</small></div>
      <div><strong>{draft.unrecognized_lines}</strong><small>未识别行</small></div>
      <div><strong>{draft.source_format.toUpperCase()}</strong><small>来源类型</small></div>
    </div>
    {draft.warnings.map(warning => <div className="warning" key={warning}>{warning}</div>)}
    <div className={`capability-gate ${draft.capability_report.executable ? 'executable' : 'blocked'}`}>
      <strong>{draft.capability_report.executable ? '能力检查通过' : '规则包暂不可执行'}</strong>
      <p>需要 {draft.capability_report.required.length} 类能力，当前覆盖 {draft.capability_report.supported.length} 类。</p>
      {(draft.capability_report.blockers ?? []).map(blocker => <small key={blocker}>{blocker}</small>)}
    </div>
    <details className="evidence-list" open>
      <summary>查看提取证据（{draft.evidence.length}）</summary>
      <div>{draft.evidence.map((item, index) => <article key={`${item.source_line}-${item.property_path}-${index}`}><span>{item.role}</span><code>{item.property_path}</code><b>{String(item.value)}</b><small>第 {item.source_line} 行 · {Math.round(item.confidence * 100)}%</small><p>{item.quote}</p></article>)}</div>
    </details>
    <label className="rule-json">可编辑规则包 JSON
      <textarea value={json} onChange={event => setJson(event.target.value)} rows={16} spellCheck={false} />
    </label>
    <div className="draft-import"><p>正式导入后会再次执行能力检查，不会立即修改任何论文。</p><button className="primary" type="button" disabled={importing || !json.trim() || !draft.capability_report.executable} onClick={onImport}>{importing ? '正在导入…' : '确认并导入规则包'}</button></div>
  </div>
}
