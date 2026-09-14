import type { components } from '../generated/schema'

export type RulePackSummary = components['schemas']['RulePackSummary']
export type RulePackDraft = components['schemas']['RulePackDraft']
export type CapabilityDefinition = components['schemas']['CapabilityDefinition']
export type RulePackCapabilityReport = components['schemas']['RulePackCapabilityReport']
export type TemplateInspection = components['schemas']['TemplateInspection']
export type TemplateFillPreview = components['schemas']['TemplateFillPreview']
export type TemplateSectionStructureConfig = components['schemas']['TemplateSectionStructureConfig']
export type TemplateSectionUpdate = components['schemas']['TemplateSectionUpdate']
export type TemplateStructurePreview = components['schemas']['TemplateStructurePreview']
export type TemplateCombinedPreview = components['schemas']['TemplateCombinedPreview']
export type ManuscriptCompositionPreview = components['schemas']['ManuscriptCompositionPreview']
export type JobView = components['schemas']['JobView']
export type JobPage = components['schemas']['JobPage']
export type PatchPlan = components['schemas']['PatchPlan']
export type PatchOperation = components['schemas']['PatchOperation']
export type ArtifactView = components['schemas']['ArtifactView']
export type DocumentInspection = components['schemas']['DocumentInspection']
export type ValidationReport = components['schemas']['ValidationReport']

const baseUrl = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly body: Record<string, unknown> | null) {
    super(typeof body?.detail === 'string' ? body.detail : `API 请求失败 (${status})`)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, init)
  if (!response.ok) {
    const body = await response.json().catch(() => null) as Record<string, unknown> | null
    throw new ApiError(response.status, body)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

async function download(path: string, body: FormData): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${baseUrl}${path}`, { method: 'POST', body })
  if (!response.ok) {
    const problem = await response.json().catch(() => null) as Record<string, unknown> | null
    throw new ApiError(response.status, problem)
  }
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1]
  return {
    blob: await response.blob(),
    filename: encoded ? decodeURIComponent(encoded) : 'template-filled.docx',
  }
}

function templateFillBody(file: File, values: Record<string, string>) {
  const body = new FormData()
  body.append('document', file)
  body.append('values', JSON.stringify(values))
  return body
}

function templateStructureBody(file: File, configuration: TemplateSectionStructureConfig) {
  const body = new FormData()
  body.append('document', file)
  body.append('configuration', JSON.stringify(configuration))
  return body
}

function templateCombinedBody(
  file: File,
  values: Record<string, string>,
  configuration: TemplateSectionStructureConfig,
) {
  const body = templateStructureBody(file, configuration)
  body.append('values', JSON.stringify(values))
  return body
}

export const api = {
  listRulePacks: () => request<RulePackSummary[]>('/api/v1/rule-packs'),
  listCapabilities: () => request<CapabilityDefinition[]>('/api/v1/rule-packs/capabilities'),
  inspectTemplate: (file: File) => {
    const body = new FormData()
    body.append('document', file)
    return request<TemplateInspection>('/api/v1/templates/inspect', { method: 'POST', body })
  },
  previewTemplateFill: (file: File, values: Record<string, string>, sourceSha256: string) => {
    const body = templateFillBody(file, values)
    body.append('source_sha256', sourceSha256)
    return request<TemplateFillPreview>('/api/v1/templates/fill/preview', { method: 'POST', body })
  },
  fillTemplate: (file: File, values: Record<string, string>, preview: TemplateFillPreview) => {
    const body = templateFillBody(file, values)
    body.append('source_sha256', preview.source_sha256)
    body.append('plan_version', preview.plan_version)
    return download('/api/v1/templates/fill', body)
  },
  previewTemplateStructure: (file: File, configuration: TemplateSectionStructureConfig, sourceSha256: string) => {
    const body = templateStructureBody(file, configuration)
    body.append('source_sha256', sourceSha256)
    return request<TemplateStructurePreview>('/api/v1/templates/structure/preview', { method: 'POST', body })
  },
  structureTemplate: (file: File, configuration: TemplateSectionStructureConfig, preview: TemplateStructurePreview) => {
    const body = templateStructureBody(file, configuration)
    body.append('source_sha256', preview.source_sha256)
    body.append('plan_version', preview.plan_version)
    return download('/api/v1/templates/structure', body)
  },
  previewTemplateCombined: (file: File, values: Record<string, string>, configuration: TemplateSectionStructureConfig, sourceSha256: string) => {
    const body = templateCombinedBody(file, values, configuration)
    body.append('source_sha256', sourceSha256)
    return request<TemplateCombinedPreview>('/api/v1/templates/combined/preview', { method: 'POST', body })
  },
  combinedTemplate: (file: File, values: Record<string, string>, configuration: TemplateSectionStructureConfig, preview: TemplateCombinedPreview) => {
    const body = templateCombinedBody(file, values, configuration)
    body.append('source_sha256', preview.source_sha256)
    body.append('plan_version', preview.plan_version)
    return download('/api/v1/templates/combined', body)
  },
  importRulePack: (file: File) => {
    const body = new FormData()
    body.append('document', file)
    return request<RulePackSummary>('/api/v1/rule-packs/import', { method: 'POST', body })
  },
  extractRulePack: (text: string, file: File | null, name: string, rulePackId: string) => {
    const body = new FormData()
    if (text.trim()) body.append('text', text)
    if (file) body.append('document', file)
    if (name.trim()) body.append('name', name)
    if (rulePackId.trim()) body.append('rule_pack_id', rulePackId)
    return request<RulePackDraft>('/api/v1/rule-packs/drafts', { method: 'POST', body })
  },
  importRulePackJson: (json: string) => {
    const body = new FormData()
    body.append('document', new File([json], 'generated-rule-pack.json', { type: 'application/json' }))
    return request<RulePackSummary>('/api/v1/rule-packs/import', { method: 'POST', body })
  },
  createJob: (file: File, rulePackId: string, renderPreview: boolean, templateFile?: File | null, formattingMode: 'standardize' | 'preserve' = 'standardize') => {
    const body = new FormData()
    body.append('document', file)
    body.append('rule_pack_id', rulePackId)
    body.append('render_preview', String(renderPreview))
    body.append('formatting_mode', formattingMode)
    if (templateFile) body.append('template_document', templateFile)
    return request<JobView>('/api/v1/jobs', { method: 'POST', body })
  },
  listJobs: (limit = 20, cursor?: string) => {
    const query = new URLSearchParams({ limit: String(limit) })
    if (cursor) query.set('cursor', cursor)
    return request<JobPage>(`/api/v1/jobs?${query}`)
  },
  getJob: (jobId: string) => request<JobView>(`/api/v1/jobs/${jobId}`),
  deleteJob: (jobId: string) => request<void>(`/api/v1/jobs/${jobId}`, { method: 'DELETE' }),
  getInspection: (jobId: string) => request<DocumentInspection>(`/api/v1/jobs/${jobId}/inspection`),
  getPlan: (jobId: string) => request<PatchPlan>(`/api/v1/jobs/${jobId}/plan`),
  getTemplatePlan: (jobId: string) => request<TemplateCombinedPreview | ManuscriptCompositionPreview>(`/api/v1/jobs/${jobId}/template-plan`),
  approve: (jobId: string, planVersion: string, approved: string[], rejected: string[], confirmedManual: string[]) =>
    request<JobView>(`/api/v1/jobs/${jobId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan_version: planVersion,
        approved_operation_ids: approved,
        rejected_operation_ids: rejected,
        confirmed_manual_operation_ids: confirmedManual,
      }),
    }),
  cancel: (jobId: string) => request<JobView>(`/api/v1/jobs/${jobId}/cancel`, { method: 'POST' }),
  getReport: (jobId: string) => request<ValidationReport>(`/api/v1/jobs/${jobId}/report`),
  listArtifacts: (jobId: string) => request<ArtifactView[]>(`/api/v1/jobs/${jobId}/artifacts`),
  artifactUrl: (jobId: string, kind: string) => `${baseUrl}/api/v1/jobs/${jobId}/artifacts/${kind}`,
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const code = typeof error.body?.code === 'string' ? error.body.code : ''
    const messages: Record<string, string> = {
      INVALID_DOCX: 'DOCX 文件结构无效，请重新选择文档。',
      UNSUPPORTED_DOCUMENT_FORMAT: '主论文仅支持 .doc 或 .docx 文件。',
      INVALID_DOC: '该文件不是有效的旧版 Word DOC 文档。',
      DOC_CONVERSION_UNAVAILABLE: '本机未找到 DOC 转换组件，请安装 LibreOffice 后重试。',
      DOC_CONVERSION_BUSY: '已有 DOC 正在转换，请稍后重试。',
      DOC_CONVERSION_TIMEOUT: 'DOC 转换超时，请检查文档后重试。',
      DOC_CONVERSION_FAILED: 'DOC 转换失败，文档可能已损坏或包含不受支持的内容。',
      FILE_TOO_LARGE: '文件超过 50 MiB 限制。',
      UNSAFE_ZIP_PACKAGE: '文档内部结构未通过安全检查。',
      RULE_SOURCE_INVALID: '未能从该文本或文件中生成规则包，请检查格式描述。',
      RULE_PACK_INVALID: '生成的规则包 JSON 无效，请检查编辑内容。',
      RULE_PACK_NOT_EXECUTABLE: '规则包包含未决、冲突或工作台尚未支持的要求。',
      TEMPLATE_FILL_INVALID: '模板填写值无效，请根据字段提示修改。',
      TEMPLATE_FILL_BLOCKED: '填写目标包含字段、公式、修订或数据绑定，已停止生成以保护模板。',
      STALE_TEMPLATE_FILL_PLAN: '模板或填写值已变化，请重新生成填写预览。',
      TEMPLATE_STRUCTURE_INVALID: '分节结构设置无效，请检查页码与页眉页脚选项。',
      TEMPLATE_STRUCTURE_BLOCKED: '分节结构包含无法安全执行的关系，已停止生成。',
      STALE_TEMPLATE_STRUCTURE_PLAN: '模板或分节设置已变化，请重新生成结构预览。',
      TEMPLATE_COMBINED_INVALID: '模板组合设置无效，请检查字段与分节选项。',
      TEMPLATE_COMBINED_BLOCKED: '模板组合计划包含不可执行项，已停止生成。',
      STALE_TEMPLATE_COMBINED_PLAN: '模板、填写值或分节设置已变化，请重新生成组合预览。',
      STALE_PLAN: '计划已变化，请重新载入后审核。',
      JOB_MODE_MISMATCH: '任务模式与规则包配置不一致，请让系统自动选择。',
      JOB_DELETE_CONFLICT: '运行中的任务不能删除，请先取消或等待完成。',
      INVALID_CURSOR: '任务历史游标已失效，请刷新页面。',
      CROSS_REFERENCE_INVALID: '交叉引用标记重复、未解析或位于受保护结构中，请修正后重试。',
      APPROVAL_REQUIRED: '高风险或低置信度操作需要先完成明确确认。',
      INTEGRITY_CHECK_FAILED: '排版结果未通过内容完整性检查。',
    }
    return messages[code] ?? error.message
  }
  if (error instanceof TypeError) return '无法连接本地服务，请确认 API 和 Worker 已启动。'
  return '发生未预期错误。'
}
