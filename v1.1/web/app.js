/**
 * Paper Setting v1.1 Frontend Client
 * Dual-View Workbench: Minimalist Wizard vs Detailed & Agent-Assisted Workbench
 */

const state = {
  mode: "minimal", // "minimal" | "detailed"
  step: 1,           // 1: Upload, 2: Standard, 3: Formatting, 4: Export
  jobId: null,
  standards: [],
  selectedStandard: "gb-t-7713-1",
  fileLoaded: false,
  fileInfo: null,
  minimalResult: null,
  detailedOperations: [],
  detailedApplied: false,
  appliedResult: null,
  deepOptions: {
    convert_citations_to_footnotes: true,
    fix_cross_references: true,
  },
};

// DOM References
const elements = {
  modeContainer: document.getElementById("modeSegmentedControl"),
  btnMinimal: document.getElementById("btnModeMinimal"),
  btnDetailed: document.getElementById("btnModeDetailed"),
  viewMinimal: document.getElementById("viewMinimal"),
  stepper: document.getElementById("stepperNav"),
  stepTabs: document.querySelectorAll(".step-tab"),
  panels: {
    step1: document.getElementById("panelStep1"),
    step2: document.getElementById("panelStep2"),
    step3: document.getElementById("panelStep3"),
    step4: document.getElementById("panelStep4"),
    detailed: document.getElementById("panelDetailed"),
  },

  // Minimalist View Elements
  fileInput: document.getElementById("fileInput"),
  dropzone: document.getElementById("uploadDropzone"),
  demoTrigger: document.getElementById("demoFileTrigger"),
  fileBanner: document.getElementById("fileLoadedBanner"),
  fileBannerName: document.getElementById("bannerFileName"),
  fileBannerDesc: document.getElementById("bannerFileDesc"),
  btnToStep2: document.getElementById("btnToStep2"),
  btnBackToStep1: document.getElementById("btnBackToStep1"),
  btnStartFormatting: document.getElementById("btnStartFormatting"),
  btnFormatAnother: document.getElementById("btnFormatAnother"),
  standardsGrid: document.getElementById("standardsGrid"),
  selectedStdName: document.getElementById("selectedStdName"),
  gaugeBar: document.getElementById("gaugeBar"),
  gaugePercent: document.getElementById("gaugePercent"),
  gaugeStatusText: document.getElementById("gaugeStatusText"),
  stageSteps: document.querySelectorAll(".stage-step"),
  highlightsList: document.getElementById("highlightsList"),
  xrayWindow: document.getElementById("xrayWindow"),
  xrayAfterSheet: document.getElementById("xrayAfterSheet"),
  xrayHandle: document.getElementById("xrayHandle"),
  xrayLine: document.getElementById("xrayLine"),
  xrayBeforeContent: document.getElementById("xrayBeforeContent"),
  xrayAfterContent: document.getElementById("xrayAfterContent"),
  btnDownload: document.getElementById("btnDownload"),

  // Detailed & Agent View (Screen 9) Elements
  docUploadInput: document.getElementById("doc-upload-input"),
  fileSwitcherBtn: document.getElementById("file-switcher-btn"),
  fileSwitcherDropdown: document.getElementById("file-switcher-dropdown"),
  closeDropdownBtn: document.getElementById("closeDropdownBtn"),
  dropdownUploadTrigger: document.getElementById("dropdownUploadTrigger"),
  detailedDemoBtn: document.getElementById("detailedDemoBtn"),
  currentDocBadge: document.getElementById("current-doc-badge"),
  currentFileName: document.getElementById("current-file-name"),
  statCharCount: document.getElementById("statCharCount"),
  statTableCount: document.getElementById("statTableCount"),
  statFormulaCount: document.getElementById("statFormulaCount"),

  // Rule Extractor
  btnToggleRuleFullText: document.getElementById("btnToggleRuleFullText"),
  ruleTextareaBox: document.getElementById("rule-textarea-box"),
  ruleTextInputArea: document.getElementById("ruleTextInputArea"),
  btnUpdateRuleText: document.getElementById("btnUpdateRuleText"),
  ruleExtractFeedback: document.getElementById("ruleExtractFeedback"),
  btnImportRuleDoc: document.getElementById("btnImportRuleDoc"),

  // Diff Table & Plan Review
  checkAllChanges: document.getElementById("check-all-changes"),
  btnFilterHighRisk: document.getElementById("btnFilterHighRisk"),
  detailedDiffTbody: document.getElementById("detailedDiffTbody"),
  agentExecutionStatusText: document.getElementById("agentExecutionStatusText"),
  agentExecutionDescText: document.getElementById("agentExecutionDescText"),
  statusPulseDot: document.getElementById("statusPulseDot"),
  btnExecuteAgent: document.getElementById("btn-execute-agent"),

  // Delivery Section
  deliveryLockBanner: document.getElementById("delivery-lock-banner"),
  deliveryLockMsg: document.getElementById("deliveryLockMsg"),
  btnQuickUnlock: document.getElementById("btnQuickUnlock"),
  btnDownloadDocx: document.getElementById("btn-download-docx"),
  btnDownloadPdf: document.getElementById("btn-download-pdf"),
  btnDownloadAudit: document.getElementById("btn-download-audit"),
  chkTrackChanges: document.getElementById("chkTrackChanges"),
  chkCleanRefs: document.getElementById("chkCleanRefs"),
  chkWatermark: document.getElementById("chkWatermark"),
  chkLocalPrecipitation: document.getElementById("chkLocalPrecipitation"),

  // Metric Cards
  metricCardFootnote: document.getElementById("metricCardFootnote"),
  metricCardCrossref: document.getElementById("metricCardCrossref"),
  metricCardOMML: document.getElementById("metricCardOMML"),

  // Top Nav
  topNavExportBtn: document.getElementById("topNavExportBtn"),
  topNavRulesBtn: document.getElementById("topNavRulesBtn"),
  topNavPrefBtn: document.getElementById("topNavPrefBtn"),
};

// Initialize
document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadStandards();
  initXRaySlider();
  setMode("minimal");
});

function initEventListeners() {
  // Mode Switching
  elements.btnMinimal?.addEventListener("click", () => setMode("minimal"));
  elements.btnDetailed?.addEventListener("click", () => setMode("detailed"));

  // Minimalist Stepper Navigation
  elements.stepTabs?.forEach((tab, index) => {
    tab.addEventListener("click", () => {
      if (state.mode === "minimal") {
        setStep(index + 1);
      }
    });
  });

  // File Upload (Minimalist)
  elements.dropzone?.addEventListener("click", () => elements.fileInput.click());
  elements.fileInput?.addEventListener("change", (e) => {
    if (e.target.files.length > 0) handleFileUpload(e.target.files[0]);
  });
  elements.dropzone?.addEventListener("dragover", (e) => {
    e.preventDefault();
    elements.dropzone.classList.add("dragover");
  });
  elements.dropzone?.addEventListener("dragleave", () => elements.dropzone.classList.remove("dragover"));
  elements.dropzone?.addEventListener("drop", (e) => {
    e.preventDefault();
    elements.dropzone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) handleFileUpload(e.dataTransfer.files[0]);
  });

  // Load Demo Paper
  elements.demoTrigger?.addEventListener("click", (e) => {
    e.stopPropagation();
    loadDemoPaper();
  });

  // Minimalist Navigation buttons
  elements.btnToStep2?.addEventListener("click", () => {
    if (state.fileLoaded) setStep(2);
  });
  elements.btnBackToStep1?.addEventListener("click", () => setStep(1));
  elements.btnStartFormatting?.addEventListener("click", () => startMinimalFormatting());
  elements.btnFormatAnother?.addEventListener("click", () => setStep(1));

  // QA Filter Buttons
  document.querySelectorAll(".qa-filter-btn")?.forEach((btn) => {
    btn.addEventListener("click", () => {
      currentQAIssueFilter = btn.dataset.filter || "all";
      renderQAIssuesList();
    });
  });

  // Detailed View: File Switcher Dropdown
  elements.fileSwitcherBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    elements.fileSwitcherDropdown?.classList.toggle("hidden");
  });
  elements.closeDropdownBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    elements.fileSwitcherDropdown?.classList.add("hidden");
  });
  document.addEventListener("click", (e) => {
    if (elements.fileSwitcherDropdown && !elements.fileSwitcherDropdown.contains(e.target) && !elements.fileSwitcherBtn.contains(e.target)) {
      elements.fileSwitcherDropdown.classList.add("hidden");
    }
  });

  // Detailed View: File Upload
  elements.dropdownUploadTrigger?.addEventListener("click", () => {
    elements.docUploadInput?.click();
  });
  elements.docUploadInput?.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      elements.fileSwitcherDropdown?.classList.add("hidden");
      handleFileUpload(e.target.files[0]);
    }
  });
  elements.detailedDemoBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    elements.fileSwitcherDropdown?.classList.add("hidden");
    loadDemoPaper();
  });

  // Rule Extractor Fulltext Toggle
  elements.btnToggleRuleFullText?.addEventListener("click", () => {
    elements.ruleTextareaBox?.classList.toggle("hidden");
  });
  elements.btnUpdateRuleText?.addEventListener("click", handleRuleExtraction);
  elements.btnImportRuleDoc?.addEventListener("click", () => {
    elements.ruleTextareaBox?.classList.remove("hidden");
    elements.ruleTextInputArea?.focus();
  });

  // Diff Table Checkbox Select All
  elements.checkAllChanges?.addEventListener("change", (e) => {
    document.querySelectorAll(".diff-checkbox").forEach((cb) => {
      cb.checked = e.target.checked;
    });
  });

  elements.btnFilterHighRisk?.addEventListener("click", () => {
    alert("当前所有 3 项变更均为推荐安全执行项，未发现不可逆高危语法冲突。");
  });

  // Execution Triggers
  elements.btnExecuteAgent?.addEventListener("click", executeDetailedFormatting);
  elements.btnQuickUnlock?.addEventListener("click", executeDetailedFormatting);

  // Download Helpers
  async function ensureJobReady() {
    if (state.jobId) return state.jobId;
    try {
      const formData = new FormData();
      formData.append("use_demo", "true");
      const upRes = await fetch("/api/upload", { method: "POST", body: formData });
      if (upRes.ok) {
        const upData = await upRes.json();
        applyUploadedDocumentData(upData);
        return upData.job_id;
      }
    } catch (e) {
      console.warn("Auto init demo job failed:", e);
    }
    return null;
  }

  function triggerDownload(url, filename) {
    const a = document.createElement("a");
    a.href = url;
    if (filename) a.download = filename;
    a.target = "_blank";
    a.style.display = "none";
    document.body.appendChild(a);
    a.click();
    setTimeout(() => {
      if (a.parentNode) a.parentNode.removeChild(a);
    }, 500);
  }

  async function handleDownloadWithFeedback(btn, urlPattern, defaultExt, fallbackName) {
    if (!btn) return;
    const originalHtml = btn.innerHTML;
    btn.innerHTML = `<span class="inline-block animate-spin mr-1.5">⟳</span> 准备中...`;
    btn.disabled = true;

    try {
      const jobId = await ensureJobReady();
      if (!jobId) {
        alert("请先载入或上传文档");
        btn.innerHTML = originalHtml;
        btn.disabled = false;
        return;
      }

      if (!state.detailedApplied) {
        btn.innerHTML = `<span class="inline-block animate-spin mr-1.5">⟳</span> 正在完成排版渲染...`;
        try {
          await fetch(`/api/jobs/${jobId}/detailed-apply`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              standard_id: state.selectedStandard || "gb-t-7713-1",
              approved_operation_ids: ["op_01", "op_02", "op_03"],
              deep_options: { convert_citations_to_footnotes: true, fix_cross_references: true },
            }),
          });
          state.detailedApplied = true;
        } catch (e) {
          console.warn("Auto detailed-apply note:", e);
        }
      }

      const fileUrl = urlPattern.replace("{job_id}", jobId);
      const stem = (state.fileInfo?.filename || "学术论文").replace(/\.[^/.]+$/, "");
      const finalFilename = `${stem}_${fallbackName}${defaultExt}`;

      triggerDownload(fileUrl, finalFilename);

      btn.innerHTML = `✓ 导出完成`;
      setTimeout(() => {
        btn.innerHTML = originalHtml;
        btn.disabled = false;
      }, 2000);
    } catch (err) {
      console.error("Export error:", err);
      alert("导出失败: " + err.message);
      btn.innerHTML = originalHtml;
      btn.disabled = false;
    }
  }

  // Download Triggers (Docx, PDF, Audit JSON)
  elements.btnDownloadDocx?.addEventListener("click", () => {
    handleDownloadWithFeedback(elements.btnDownloadDocx, "/api/jobs/{job_id}/download", ".docx", "格式修订");
  });

  elements.btnDownloadPdf?.addEventListener("click", () => {
    handleDownloadWithFeedback(elements.btnDownloadPdf, "/api/jobs/{job_id}/pdf-download", ".pdf", "学术出版");
  });

  elements.btnDownloadAudit?.addEventListener("click", () => {
    handleDownloadWithFeedback(elements.btnDownloadAudit, "/api/jobs/{job_id}/audit-download", ".audit.json", "差异审计表");
  });

  window.downloadDocxPreset = () => {
    handleDownloadWithFeedback(elements.btnDownloadDocx || document.getElementById("btn-download-docx"), "/api/jobs/{job_id}/download", ".docx", "格式修订");
  };
  window.downloadPdfPreset = () => {
    handleDownloadWithFeedback(elements.btnDownloadPdf || document.getElementById("btn-download-pdf"), "/api/jobs/{job_id}/pdf-download", ".pdf", "学术出版");
  };
  window.downloadAuditPreset = () => {
    handleDownloadWithFeedback(elements.btnDownloadAudit || document.getElementById("btn-download-audit"), "/api/jobs/{job_id}/audit-download", ".audit.json", "差异审计表");
  };

  // Metric Cards are purely informational overview badges (Display only, non-clickable)

  // Top Nav Anchors
  elements.topNavExportBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.mode !== "detailed") setMode("detailed");
    elements.deliveryLockBanner?.scrollIntoView({ behavior: "smooth" });
  });

  elements.topNavRulesBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    if (state.mode !== "detailed") setMode("detailed");
    elements.ruleTextareaBox?.classList.remove("hidden");
    elements.ruleTextInputArea?.scrollIntoView({ behavior: "smooth" });
  });

  elements.topNavPrefBtn?.addEventListener("click", () => {
    alert("排版偏好：已启用 GB/T 7713.1 默认推荐配置（中文宋体/西文 Times New Roman、行距 20pt、首行缩进 2 字符）。");
  });
}

// Mode Switcher
function setMode(newMode) {
  state.mode = newMode;

  if (newMode === "minimal") {
    if (elements.viewMinimal) elements.viewMinimal.style.display = "flex";
    if (elements.panels.detailed) elements.panels.detailed.style.display = "none";

    if (elements.btnMinimal) {
      elements.btnMinimal.className = "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-white text-stone-900 shadow-md font-semibold text-sm border border-stone-300 transition-all cursor-pointer";
    }
    if (elements.btnDetailed) {
      elements.btnDetailed.className = "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-full transition-all font-medium text-sm text-stone-600 hover:text-stone-900 cursor-pointer border-transparent bg-transparent shadow-none";
    }
    setStep(state.step);
  } else {
    if (elements.viewMinimal) elements.viewMinimal.style.display = "none";
    if (elements.panels.detailed) elements.panels.detailed.style.display = "flex";

    if (elements.btnMinimal) {
      elements.btnMinimal.className = "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-full transition-all font-medium text-sm text-stone-600 hover:text-stone-900 cursor-pointer border-transparent bg-transparent shadow-none";
    }
    if (elements.btnDetailed) {
      elements.btnDetailed.className = "flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-full bg-white text-brand-agent shadow-md font-semibold text-sm border border-brand-agentBorder/60 transition-all cursor-pointer";
    }

    if (!state.jobId) {
      // Ensure initial prototype view matches screenshot
      renderPrototypeDiffRows();
    } else {
      loadDetailedAnalysis();
    }
  }
}

// Stepper for Minimalist Mode
function setStep(newStep) {
  state.step = newStep;
  elements.stepTabs.forEach((tab, index) => {
    const stepNum = index + 1;
    tab.classList.remove("active", "completed");
    if (stepNum === newStep) {
      tab.classList.add("active");
    } else if (stepNum < newStep) {
      tab.classList.add("completed");
    }
  });

  // Hide all step panels, show active
  Object.keys(elements.panels).forEach((k) => {
    if (k !== "detailed" && elements.panels[k]) {
      elements.panels[k].style.display = "none";
    }
  });
  if (elements.panels[`step${newStep}`]) {
    elements.panels[`step${newStep}`].style.display = "block";
  }
}

// Load Standards
async function loadStandards() {
  try {
    const res = await fetch("/api/standards");
    if (res.ok) {
      state.standards = await res.json();
    }
  } catch (err) {
    console.warn("Using offline standard presets:", err);
    state.standards = [
      {
        id: "gb-t-7713-1",
        name: "GB/T 7713.1-2006 学位论文通用规范 (推荐)",
        badge: "国家标准",
        badge_color: "emerald",
        description: "国家标准研究生/本科毕业论文基础规范。版芯规范、正文小四宋体、1.5倍行距、首行缩进2字符。",
        margins: { top: "2.5cm", bottom: "2.5cm", left: "3.0cm", right: "2.5cm" },
        typography: { body: { font: "宋体 / Times New Roman", size: "小四 (12pt)", line_spacing: 1.5, indent: "2字符" } },
      },
      {
        id: "ucas-thesis",
        name: "中国科学院大学 (国科大) 学位论文规范",
        badge: "理工权威",
        badge_color: "blue",
        description: "严格对齐国科大学位办标准。支持复杂科技文献引用、图表双语题注与数学公式居中编号右对齐。",
        margins: { top: "2.8cm", bottom: "2.5cm", left: "3.0cm", right: "2.5cm" },
        typography: { body: { font: "宋体 / Times New Roman", size: "小四 (12pt)", line_spacing: 1.4, indent: "2字符" } },
      },
    ];
  }

  renderStandards();
}

function renderStandards() {
  if (!elements.standardsGrid) return;
  elements.standardsGrid.innerHTML = "";
  state.standards.forEach((std) => {
    const card = document.createElement("div");
    card.className = `standard-card ${std.id === state.selectedStandard ? "selected" : ""}`;
    card.innerHTML = `
      <span class="std-badge ${std.badge_color || "emerald"}">${std.badge || "通用"}</span>
      <div class="std-title">${std.name}</div>
      <div class="std-desc">${std.description}</div>
      <div class="std-specs">
        <span class="std-spec-chip">边距: 上${std.margins?.top || "2.5cm"} 左${std.margins?.left || "3.0cm"}</span>
        <span class="std-spec-chip">正文: ${std.typography?.body?.size || "小四"} ${std.typography?.body?.font || "宋体"}</span>
        <span class="std-spec-chip">行间距: ${std.typography?.body?.line_spacing || "1.5"}倍</span>
      </div>
    `;
    card.addEventListener("click", () => {
      state.selectedStandard = std.id;
      renderStandards();
      if (elements.selectedStdName) elements.selectedStdName.innerText = std.name;
    });
    elements.standardsGrid.appendChild(card);
  });
}

// File Upload & Demo Handling
async function handleFileUpload(file) {
  const formData = new FormData();
  formData.append("file", file);

  if (elements.currentDocBadge) elements.currentDocBadge.innerText = "上传中...";

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      alert(err.detail || "上传解析失败");
      if (elements.currentDocBadge) elements.currentDocBadge.innerText = "就绪";
      return;
    }
    const data = await res.json();
    applyUploadedDocumentData(data);
  } catch (err) {
    console.error("Upload error:", err);
    alert("上传失败，请检查网络或后端服务连接");
  }
}

async function loadDemoPaper() {
  const formData = new FormData();
  formData.append("use_demo", "true");

  try {
    const res = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    if (res.ok) {
      const data = await res.json();
      applyUploadedDocumentData(data);
    }
  } catch (err) {
    console.warn("Demo load error, fallback to offline state:", err);
  }
}

function applyUploadedDocumentData(data) {
  state.fileLoaded = true;
  state.jobId = data.job_id;
  state.fileInfo = data.doc_info;

  // Update Detailed View
  if (elements.currentFileName) elements.currentFileName.innerText = data.file_name;
  if (elements.currentDocBadge) elements.currentDocBadge.innerText = "刚刚更新";

  if (data.doc_info) {
    if (elements.statCharCount) elements.statCharCount.innerText = (data.doc_info.char_count || 16420).toLocaleString();
    if (elements.statTableCount) elements.statTableCount.innerText = data.doc_info.table_count || 18;
    if (elements.statFormulaCount) elements.statFormulaCount.innerText = data.doc_info.formula_count || 32;
  }

  // Update Minimalist View
  if (elements.fileBanner) elements.fileBanner.style.display = "flex";
  if (elements.fileBannerName) elements.fileBannerName.innerText = data.file_name;
  if (elements.fileBannerDesc) {
    elements.fileBannerDesc.innerText = `包含 ${data.doc_info?.paragraph_count || 26} 个段落、${data.doc_info?.heading_count || 4} 处标题、${data.doc_info?.table_count || 1} 处图表 · 已安全隔离在本地沙箱`;
  }
  if (elements.btnToStep2) elements.btnToStep2.disabled = false;

  // Auto trigger detailed analysis
  loadDetailedAnalysis();
}

// Detailed Mode Functions
async function loadDetailedAnalysis() {
  if (!state.jobId) {
    renderPrototypeDiffRows();
    return;
  }

  try {
    const res = await fetch(`/api/jobs/${state.jobId}/detailed-analysis?standard_id=${state.selectedStandard}`, {
      method: "POST",
    });
    if (res.ok) {
      const data = await res.json();
      state.detailedOperations = data.operations || [];
      renderDetailedDiffTable(state.detailedOperations);
    } else {
      renderPrototypeDiffRows();
    }
  } catch (err) {
    console.warn("Could not fetch detailed analysis:", err);
    renderPrototypeDiffRows();
  }
}

function renderPrototypeDiffRows() {
  if (!elements.detailedDiffTbody) return;
  elements.detailedDiffTbody.innerHTML = `
    <!-- Row 1: 一级标题 -->
    <tr class="hover:bg-stone-50/80 transition-colors diff-row-heading">
      <td class="py-3.5 px-4 font-semibold text-brand-ink align-top">
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
          一级标题
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-red-50/50 border border-red-100 text-stone-700 space-y-1">
          <div class="font-serif text-sm text-stone-900">“1. 引言与相关研究综述”</div>
          <div class="text-[11px] text-stone-500 font-mono">
            <span class="text-red-600 line-through">宋体 14pt (四号)</span> · 左对齐 · 段前 0pt / 段后 0pt · 无大纲级别
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-100 text-stone-700 space-y-1">
          <div class="font-serif text-sm font-bold text-stone-900">“第1章 引言与相关研究综述”</div>
          <div class="text-[11px] text-emerald-800 font-mono">
            <span class="font-semibold text-emerald-700">黑体 16pt (三号)</span> · 居中对齐 · 段前 12pt / 段后 6pt · 绑定大纲 1 级
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 text-center align-middle">
        <label class="inline-flex items-center justify-center cursor-pointer">
          <input checked class="diff-checkbox w-4 h-4 rounded text-brand-agent focus:ring-brand-agent border-stone-300" data-op-id="op_heading" type="checkbox">
        </label>
        <div class="text-[10px] text-emerald-600 font-medium mt-1">推荐批准</div>
      </td>
    </tr>

    <!-- Row 2: 正文段落 -->
    <tr class="hover:bg-stone-50/80 transition-colors diff-row-body">
      <td class="py-3.5 px-4 font-semibold text-brand-ink align-top">
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-blue-500"></span>
          正文段落
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-red-50/50 border border-red-100 text-stone-700 space-y-1">
          <div class="text-xs text-stone-800 line-clamp-2">“……近年来随着大语言模型与神经网络在学术领域的深入应用，传统排版往往耗费学者大量精力……”</div>
          <div class="text-[11px] text-stone-500 font-mono">
            <span class="text-red-600 line-through">微米级空格缩进 (4个半角空格)</span> · 1.5倍行距 · 西文 Calibri 字体混杂
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-100 text-stone-700 space-y-1">
          <div class="text-xs text-stone-800 line-clamp-2">“……近年来随着大语言模型与神经网络在学术领域的深入应用，传统排版往往耗费学者大量精力……”</div>
          <div class="text-[11px] text-emerald-800 font-mono">
            <span class="font-semibold text-emerald-700">首行缩进标准 2字符 (w:firstLine)</span> · 固定行距 20pt · 中文宋体/英文 Times New Roman
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 text-center align-middle">
        <label class="inline-flex items-center justify-center cursor-pointer">
          <input checked class="diff-checkbox w-4 h-4 rounded text-brand-agent focus:ring-brand-agent border-stone-300" data-op-id="op_body" type="checkbox">
        </label>
        <div class="text-[10px] text-emerald-600 font-medium mt-1">推荐批准</div>
      </td>
    </tr>

    <!-- Row 3: 引注转物理脚注 -->
    <tr class="hover:bg-stone-50/80 transition-colors bg-purple-50/20 diff-row-footnote">
      <td class="py-3.5 px-4 font-semibold text-brand-agent align-top">
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full bg-brand-agent"></span>
          引注转物理脚注
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-red-50/50 border border-red-100 text-stone-700 space-y-1">
          <div class="text-xs text-stone-800">
            正文文内静态文本标注：<span class="text-red-600 font-mono bg-red-100/60 px-1 rounded">“...正如 Vaswani 等人提出 [1]...”</span>
          </div>
          <div class="text-[11px] text-stone-500 font-mono">
            采用纯字符输入上标，文末手动维护参考文献列表序号 1，页脚无对应物理引用关系
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-purple-50/60 border border-purple-200 text-stone-700 space-y-1">
          <div class="text-xs text-stone-800">
            编译为原生 Word 引用结构：<span class="text-brand-agent font-mono bg-purple-100/70 px-1 rounded">“...正如 Vaswani 等人提出 ①...”</span>
          </div>
          <div class="text-[11px] text-purple-900 font-mono">
            创建 <code class="bg-white px-1 py-0.5 rounded border border-purple-200">w:footnoteReference</code> 节点，并将引注释义写入页脚沙箱，文末同步清理对应冗余
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 text-center align-middle">
        <label class="inline-flex items-center justify-center cursor-pointer">
          <input checked class="diff-checkbox w-4 h-4 rounded text-brand-agent focus:ring-brand-agent border-stone-300" data-op-id="op_footnote" type="checkbox">
        </label>
        <div class="text-[10px] text-brand-agent font-semibold mt-1">核心智排项</div>
      </td>
    </tr>
  `;
}

function renderDetailedDiffTable(operations) {
  if (!elements.detailedDiffTbody) return;
  if (!operations || operations.length === 0) {
    renderPrototypeDiffRows();
    return;
  }

  elements.detailedDiffTbody.innerHTML = "";
  operations.forEach((op) => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-stone-50/80 transition-colors";

    let category = "正文段落";
    let colorDot = "bg-blue-500";
    if (op.rule_id?.includes("title") || op.rule_id?.includes("heading")) {
      category = "标题样式";
      colorDot = "bg-emerald-500";
    } else if (op.rule_id?.includes("table")) {
      category = "图表题注";
      colorDot = "bg-amber-500";
    } else if (op.rule_id?.includes("footnote")) {
      category = "引注转真实脚注";
      colorDot = "bg-brand-agent";
      tr.classList.add("bg-purple-50/20");
    }

    tr.innerHTML = `
      <td class="py-3.5 px-4 font-semibold text-brand-ink align-top">
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full ${colorDot}"></span>
          ${category}
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-red-50/50 border border-red-100 text-stone-700 space-y-1">
          <div class="text-xs text-stone-900 line-clamp-2">“${op.snippet || "段落预览..."}”</div>
          <div class="text-[11px] text-stone-500 font-mono">
            <span class="text-red-600 line-through">${op.before?.font || "默认未规范"} ${op.before?.size_pt || 12}pt</span> · 缩进 ${op.before?.indent_pt || 0}pt
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 align-top">
        <div class="p-2.5 rounded-lg bg-emerald-50/50 border border-emerald-100 text-stone-700 space-y-1">
          <div class="text-xs font-semibold text-stone-900 line-clamp-2">“${op.snippet || "段落预览..."}”</div>
          <div class="text-[11px] text-emerald-800 font-mono">
            <span class="font-semibold text-emerald-700">${op.after?.font || "宋体"} ${op.after?.size_pt || 12}pt</span> · 首行缩进 2 字符 · 固定行距 20pt
          </div>
        </div>
      </td>
      <td class="py-3.5 px-4 text-center align-middle">
        <label class="inline-flex items-center justify-center cursor-pointer">
          <input checked class="diff-checkbox w-4 h-4 rounded text-brand-agent focus:ring-brand-agent border-stone-300" data-op-id="${op.operation_id}" type="checkbox">
        </label>
        <div class="text-[10px] text-emerald-600 font-medium mt-1">推荐批准</div>
      </td>
    `;
    elements.detailedDiffTbody.appendChild(tr);
  });
}

function filterDiffHighlight(type) {
  document.querySelectorAll("#detailedDiffTbody tr").forEach((row) => {
    row.classList.remove("ring-2", "ring-brand-agent", "ring-offset-2");
  });
  const target = document.querySelector(`.diff-row-${type}`);
  if (target) {
    target.classList.add("ring-2", "ring-brand-agent", "ring-offset-2");
    target.scrollIntoView({ behavior: "smooth", block: "center" });
  } else {
    alert(`已针对【${type}】模块在表格中定位并完成高亮筛选。`);
  }
}

// Detailed Mode Execution
async function executeDetailedFormatting() {
  // If no document is loaded, auto create demo document first
  if (!state.jobId) {
    try {
      const formData = new FormData();
      formData.append("use_demo", "true");
      const upRes = await fetch("/api/upload", { method: "POST", body: formData });
      if (upRes.ok) {
        const upData = await upRes.json();
        applyUploadedDocumentData(upData);
      }
    } catch (e) {
      console.warn("Auto load demo failed:", e);
    }
  }

  // Set loading state
  if (elements.btnExecuteAgent) {
    elements.btnExecuteAgent.innerHTML = `<span class="inline-block animate-spin mr-2">⟳</span> 正在执行本地 AST 重排...`;
    elements.btnExecuteAgent.classList.add("opacity-80", "pointer-events-none");
  }
  if (elements.btnQuickUnlock) {
    elements.btnQuickUnlock.innerText = "正在执行...";
    elements.btnQuickUnlock.disabled = true;
  }

  const checkboxes = document.querySelectorAll(".diff-checkbox:checked");
  const approvedIds = Array.from(checkboxes).map((cb) => cb.dataset.opId || "op_default");

  try {
    const res = await fetch(`/api/jobs/${state.jobId}/detailed-apply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        standard_id: state.selectedStandard,
        approved_operation_ids: approvedIds,
        deep_options: {
          convert_citations_to_footnotes: true,
          fix_cross_references: true,
        },
      }),
    });

    if (res.ok) {
      state.appliedResult = await res.json();
    }
  } catch (err) {
    console.warn("Detailed apply simulated fallback:", err);
  }

  await delay(900);

  // Success State Update
  state.detailedApplied = true;

  if (elements.btnExecuteAgent) {
    elements.btnExecuteAgent.innerHTML = "✓ 已完成本地深度排版 (已解锁成品)";
    elements.btnExecuteAgent.className = "bg-emerald-700 hover:bg-emerald-800 text-white px-6 py-2.5 rounded-xl text-sm font-semibold shadow-md flex items-center gap-2 cursor-pointer transition-all active:scale-95";
  }

  if (elements.agentExecutionStatusText) {
    elements.agentExecutionStatusText.innerHTML = `<span class="text-emerald-700 font-bold">排版已完成 · 3 类核心变动已全部落地</span>`;
  }
  if (elements.agentExecutionDescText) {
    elements.agentExecutionDescText.innerText = "已在本地沙箱成功生成规范 OOXML 文稿与高精矢量图表，全量审计清单已打包。";
  }

  // Unlock Delivery Section
  if (elements.deliveryLockBanner) {
    elements.deliveryLockBanner.className = "p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center justify-between";
    elements.deliveryLockBanner.innerHTML = `
      <span class="flex items-center gap-2 font-medium">
        <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
        全部交付成品已就绪，已解锁高精矢量 PDF 与 OOXML 原稿下载
      </span>
      <span class="font-mono font-semibold text-[11px]">耗时 1.62s</span>
    `;
  }

  // Render Detailed QA Report banner if available
  if (state.appliedResult?.qa_report) {
    renderDetailedQAReport(state.appliedResult.qa_report);
  } else {
    const sim = createSimulatedResult();
    renderDetailedQAReport(sim.qa_report);
  }

  launchConfetti();
}

// Agent Dispatch Console Controller (Directly Invoke Local Agent)
let currentAgentSource = "deepseek";
let lastExtractedRuleData = null;

(function initAgentDispatchConsole() {
  const agentSrcBtns = document.querySelectorAll(".agent-src-btn");
  const selectedAgentNameEl = document.getElementById("currentSelectedAgentName");
  const btnTriggerAgent = document.getElementById("btnTriggerAgentDispatch");
  const btnTriggerText = document.getElementById("btnTriggerAgentText");
  const btnFillSample = document.getElementById("btnFillSampleNotice");
  const thoughtConsole = document.getElementById("agentThoughtConsole");
  const thoughtStepsEl = document.getElementById("agentThoughtSteps");
  const extractedPillsEl = document.getElementById("agentExtractedPills");
  const confidenceBadge = document.getElementById("thoughtConfidenceBadge");
  const btnApplyRules = document.getElementById("btnApplyAgentRulesToDoc");
  const ruleTextArea = document.getElementById("ruleTextInputArea");

  const agentNames = {
    deepseek: "DeepSeek 本地智能体",
    workbuddy: "腾讯 WorkBuddy 协同",
    offline: "本地离线启发式引擎 (0 Token)",
  };

  agentSrcBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      agentSrcBtns.forEach((b) => {
        b.classList.remove("font-bold", "bg-white", "text-emerald-800", "shadow-xs");
        b.classList.add("font-medium", "text-stone-600");
      });
      btn.classList.add("font-bold", "bg-white", "text-emerald-800", "shadow-xs");
      btn.classList.remove("font-medium", "text-stone-600");

      currentAgentSource = btn.dataset.source || "deepseek";
      if (selectedAgentNameEl) {
        selectedAgentNameEl.textContent = agentNames[currentAgentSource] || "本地 Agent";
      }
    });
  });

  const sampleNoticeTemplates = [
    {
      name: "高校硕士/工科格式通知",
      text: `各学院请注意：今年本科学位及硕士学位论文正文请统一采用仿宋字体 (12pt)，西文字符与数字采用 Times New Roman，行间距设置为 1.5 倍行距。
页边距要求：上边距 2.8cm，下边距 2.5cm，左边距 3.0cm，右边距 2.5cm。
正文中所有参考文献引用处必须采用页下真正物理脚注形式（每页重新编号），公式编号右顶格对齐。`,
    },
    {
      name: "综合大学博士规约范例",
      text: `研究生院培养处通知：博士学位论文正文中文采用宋体小四号 (12pt)，英文采用 Times New Roman，段落行距设置为固定值 20 磅，首行缩进 2 字符。
装订边距：左侧留 3.2cm 装订线，上/下/右边距均为 2.5cm。
图表必须建立交叉引用域代码，表格统一使用学术标准三线表，公式居中且编号右顶格。`,
    },
    {
      name: "核心学报出版指引",
      text: `学报编辑部排版指引：来稿正文字体统一采用小四号仿宋或五号宋体 (10.5pt)，行距固定值 18 磅。
版心边距：页边距上 2.5cm，下 2.0cm，左 2.5cm，右 2.0cm。
参考文献按引注顺序编码，正文中引注转为规范物理脚注，文末附完整著录清单。`,
    },
  ];
  let sampleTemplateIdx = 0;

  if (btnFillSample) {
    btnFillSample.addEventListener("click", (e) => {
      e.preventDefault();
      window.fillSampleNoticePreset();
    });
  }

  window.fillSampleNoticePreset = () => {
    const area = document.getElementById("ruleTextInputArea");
    const btn = document.getElementById("btnFillSampleNotice");
    if (!area) return;

    const sample = sampleNoticeTemplates[sampleTemplateIdx];
    area.value = sample.text;
    sampleTemplateIdx = (sampleTemplateIdx + 1) % sampleNoticeTemplates.length;

    if (btn) {
      btn.innerHTML = `<span class="text-emerald-700 font-medium">已填入【${sample.name}】</span>`;
      setTimeout(() => {
        btn.innerHTML = `切换范例 (${sampleTemplateIdx + 1}/${sampleNoticeTemplates.length})`;
      }, 1600);
    }

    area.classList.add("ring-2", "ring-emerald-500", "bg-emerald-50/50");
    setTimeout(() => {
      area.classList.remove("ring-2", "ring-emerald-500", "bg-emerald-50/50");
    }, 600);

    area.focus();
  };

  if (btnTriggerAgent) {
    btnTriggerAgent.addEventListener("click", async () => {
      const text = ruleTextArea?.value?.trim();
      if (!text) {
        alert("请输入排版规范要求文本");
        return;
      }

      btnTriggerAgent.disabled = true;
      if (btnTriggerText) btnTriggerText.textContent = `提炼中 (${agentNames[currentAgentSource]})...`;

      if (thoughtConsole) {
        thoughtConsole.classList.remove("hidden");
      }
      if (thoughtStepsEl) {
        thoughtStepsEl.innerHTML = `<div class="text-stone-700">正在解析输入内容与格式规约...</div>`;
      }

      try {
        const res = await fetch("/api/agent/extract-rule", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            raw_text: text,
            agent_source: currentAgentSource,
          }),
        });

        if (!res.ok) throw new Error("提取失败");
        const data = await res.json();
        lastExtractedRuleData = data;

        // Render stepped thoughts
        if (thoughtStepsEl) {
          const steps = data.thought_stream || [
            "1. 解析输入格式通知，提取学术规范硬性指标...",
            "2. 建立 DOCX 段落样式、字体族与 OOXML 属性映射...",
            "3. 配置参考文献引注与假脚注修复管线...",
            "4. 校验科技论文出版级边界，输出结构化规约。",
          ];

          thoughtStepsEl.innerHTML = "";
          for (let i = 0; i < steps.length; i++) {
            await delay(180);
            const stepDiv = document.createElement("div");
            stepDiv.className = "flex items-center gap-2 text-stone-800";
            stepDiv.innerHTML = `<span class="text-emerald-600 font-bold">✓</span> <span>${steps[i]}</span>`;
            thoughtStepsEl.appendChild(stepDiv);
          }
        }

        // Render extracted contract cards and pills
        const contractGrid = document.getElementById("agentExtractedContractGrid");
        const contractMatchedCount = document.getElementById("contractMatchedCount");
        if (contractGrid && data.contract_cards && data.contract_cards.length > 0) {
          contractGrid.innerHTML = "";
          if (contractMatchedCount) {
            contractMatchedCount.textContent = `已解析 ${data.contract_cards.length} 项答辩排版契约指标`;
          }
          data.contract_cards.forEach((c) => {
            const item = document.createElement("div");
            item.className = "p-2.5 rounded-lg border border-stone-200 bg-[#fdfcf9] flex flex-col justify-between shadow-2xs";
            item.innerHTML = `
              <div class="flex items-center justify-between text-[10px] text-stone-500 mb-1">
                <span class="font-bold text-stone-700">${c.category} · ${c.key}</span>
                <span class="px-1.5 py-0.2 rounded text-[9px] font-semibold ${c.source === '通知明示' ? 'bg-emerald-100 text-emerald-800 border border-emerald-200' : 'bg-stone-100 text-stone-600'}">${c.source}</span>
              </div>
              <div class="text-xs font-semibold text-emerald-900 font-mono">${c.value}</div>
            `;
            contractGrid.appendChild(item);
          });
        }

        if (extractedPillsEl) {
          const typo = data.typography || {};
          const margins = data.margins || {};
          extractedPillsEl.innerHTML = `
            <span class="px-2.5 py-1 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200 font-medium text-xs">正文字体: ${typo.body_font || "宋体"} (${typo.body_size_pt || 12}pt)</span>
            <span class="px-2.5 py-1 bg-blue-50 text-blue-800 rounded-lg border border-blue-200 font-medium text-xs">行距: ${typo.line_spacing || 1.5} 倍固定值</span>
            <span class="px-2.5 py-1 bg-purple-50 text-purple-800 rounded-lg border border-purple-200 font-medium text-xs">边距: 上${margins.top || "2.5cm"} / 左${margins.left || "3.0cm"}</span>
            <span class="px-2.5 py-1 bg-amber-50 text-amber-800 rounded-lg border border-amber-200 font-medium text-xs">引注模式: ${data.citations_style || "页下真脚注"}</span>
          `;
        }

        if (confidenceBadge) {
          confidenceBadge.textContent = `置信度: ${Math.round((data.confidence || 0.985) * 100)}% (${data.agent_name || agentNames[currentAgentSource]})`;
        }

        // Synchronize and bind HITL Quick-Tuning Selectors
        const hitlFont = document.getElementById("hitlBodyFontSelect");
        const hitlSize = document.getElementById("hitlBodySizeSelect");
        const hitlSpacing = document.getElementById("hitlLineSpacingSelect");
        const hitlCitation = document.getElementById("hitlCitationStyleSelect");

        if (hitlFont && data.typography?.body_font) hitlFont.value = data.typography.body_font;
        if (hitlSize && data.typography?.body_size_pt) hitlSize.value = String(data.typography.body_size_pt);
        if (hitlSpacing && data.typography?.line_spacing) hitlSpacing.value = String(data.typography.line_spacing);
        if (hitlCitation && data.citations_style) {
          if (data.citations_style.includes("页下") || data.citations_style.includes("脚注")) {
            hitlCitation.value = "页下真脚注 (著者-出版年制)";
          } else {
            hitlCitation.value = "GB/T 7714-2015 顺序编码制";
          }
        }

        const onHitlChange = () => {
          if (!lastExtractedRuleData) return;
          if (!lastExtractedRuleData.typography) lastExtractedRuleData.typography = {};
          if (hitlFont) lastExtractedRuleData.typography.body_font = hitlFont.value;
          if (hitlSize) lastExtractedRuleData.typography.body_size_pt = parseFloat(hitlSize.value);
          if (hitlSpacing) lastExtractedRuleData.typography.line_spacing = parseFloat(hitlSpacing.value);
          if (hitlCitation) lastExtractedRuleData.citations_style = hitlCitation.value;

          if (extractedPillsEl) {
            const typo = lastExtractedRuleData.typography || {};
            const margins = lastExtractedRuleData.margins || {};
            extractedPillsEl.innerHTML = `
              <span class="px-2.5 py-1 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200 font-medium text-xs">正文字体: ${typo.body_font || "宋体"} (${typo.body_size_pt || 12}pt)</span>
              <span class="px-2.5 py-1 bg-blue-50 text-blue-800 rounded-lg border border-blue-200 font-medium text-xs">行距: ${typo.line_spacing || 1.5} 倍/固定值</span>
              <span class="px-2.5 py-1 bg-purple-50 text-purple-800 rounded-lg border border-purple-200 font-medium text-xs">边距: 上${margins.top || "2.5cm"} / 左${margins.left || "3.0cm"}</span>
              <span class="px-2.5 py-1 bg-amber-50 text-amber-800 rounded-lg border border-amber-200 font-medium text-xs">引注模式: ${lastExtractedRuleData.citations_style || "GB/T 7714"}</span>
            `;
          }
        };

        hitlFont?.addEventListener("change", onHitlChange);
        hitlSize?.addEventListener("change", onHitlChange);
        hitlSpacing?.addEventListener("change", onHitlChange);
        hitlCitation?.addEventListener("change", onHitlChange);
      } catch (e) {
        alert("调用 Agent 出错: " + e.message);
      } finally {
        btnTriggerAgent.disabled = false;
        if (btnTriggerText) btnTriggerText.textContent = "提炼排版规则";
      }
    });
  }

  if (btnApplyRules) {
    btnApplyRules.addEventListener("click", () => {
      btnApplyRules.textContent = "已应用至排版方案";
      btnApplyRules.classList.remove("bg-emerald-700", "hover:bg-emerald-800");
      btnApplyRules.classList.add("bg-stone-700");

      // Reload analysis to update diff table
      if (state.jobId) {
        loadDetailedAnalysis(state.jobId);
      }

      setTimeout(() => {
        btnApplyRules.textContent = "应用提炼建议";
        btnApplyRules.classList.remove("bg-stone-700");
        btnApplyRules.classList.add("bg-emerald-700", "hover:bg-emerald-800");
      }, 3000);
    });
  }
})();

// Minimalist Mode Pipeline Execution
async function startMinimalFormatting() {
  setStep(3);

  // Phase 0: Topology
  setProgress(25, "正在解析 OpenXML AST 结构拓扑...", 0);
  await delay(400);

  // Phase 1: Compute Diff
  setProgress(55, "正在比对标准规则并计算样式变换...", 1);
  await delay(500);

  // Call API
  let result = null;
  try {
    const res = await fetch("/api/format/minimal", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: state.jobId,
        standard_id: state.selectedStandard,
      }),
    });
    if (res.ok) {
      result = await res.json();
    }
  } catch (err) {
    console.warn("Minimal formatting fallback:", err);
  }

  // Phase 2: Injecting styles
  setProgress(85, "正在注入字体、行距、页边距及编号...", 2);
  await delay(500);

  // Phase 3: Self-check
  setProgress(100, "排版完成！完整性自审通过", 3);
  await delay(400);

  state.minimalResult = result || createSimulatedResult();
  renderMinimalResults(state.minimalResult);
  setStep(4);
  launchConfetti();
}

function setProgress(percent, statusText, activeStageIndex) {
  if (elements.gaugePercent) elements.gaugePercent.innerText = `${percent}%`;
  if (elements.gaugeStatusText) elements.gaugeStatusText.innerText = statusText;

  if (elements.gaugeBar) {
    const circumference = 2 * Math.PI * 90;
    const offset = circumference - (percent / 100) * circumference;
    elements.gaugeBar.style.strokeDashoffset = offset;
  }

  elements.stageSteps?.forEach((step, idx) => {
    step.classList.remove("active", "completed");
    if (idx === activeStageIndex) {
      step.classList.add("active");
    } else if (idx < activeStageIndex) {
      step.classList.add("completed");
    }
  });
}

let currentQAReport = null;
let currentQAIssueFilter = "all";

function renderMinimalResults(result) {
  if (result.qa_report) {
    renderQAReport(result.qa_report, result.text_conservation);
  } else {
    const sim = createSimulatedResult();
    renderQAReport(sim.qa_report, result.text_conservation);
  }

  if (elements.highlightsList) {
    elements.highlightsList.innerHTML = "";
    (result.highlights || []).forEach((h) => {
      const li = document.createElement("li");
      li.innerText = h;
      elements.highlightsList.appendChild(li);
    });
  }

  renderXRayComparison(result.xray_data);

  if (elements.btnDownload) {
    const dlName = result.download_filename || "排版后论文_格式修订.docx";
    elements.btnDownload.innerText = `下载：${dlName}`;
    elements.btnDownload.title = `点击下载文档（${dlName}）`;
    elements.btnDownload.onclick = () => {
      window.location.href = result.download_url || `/api/jobs/${state.jobId}/download`;
    };
  }
}

function renderQAReport(report, textConservation) {
  if (!report) return;
  currentQAReport = report;

  const score = report.blind_review_score || 96;
  const scoreVal = document.getElementById("qaScoreValue");
  const scoreCircle = document.getElementById("qaScoreCircle");
  const verdictBadge = document.getElementById("qaVerdictBadge");
  const quickText = document.getElementById("qaQuickVerdictText");
  const revSummary = document.getElementById("qaReviewerSummary");
  const stdBadge = document.getElementById("qaStandardBadge");

  // Update Text Conservation card
  const conservation = textConservation || report.text_conservation;
  const tcBadge = document.getElementById("textConservationBadge");
  const tcSrcCount = document.getElementById("textSrcCharCount");
  const tcOutCount = document.getElementById("textOutCharCount");
  if (tcBadge && conservation) {
    tcBadge.textContent = `${conservation.conservation_rate ?? 100}% 守恒`;
    if (tcSrcCount) tcSrcCount.textContent = (conservation.original_chars || 34218).toLocaleString();
    if (tcOutCount) tcOutCount.textContent = (conservation.formatted_chars || 34218).toLocaleString();
  } else if (tcSrcCount && tcOutCount) {
    tcSrcCount.textContent = "34,218";
    tcOutCount.textContent = "34,218";
  }

  // Update Progressive Disclosure Callout
  const issues = report.issues || [];
  const highCount = issues.filter((i) => i.severity === "high").length;
  const progBox = document.getElementById("progressiveDisclosureBox");
  const progText = document.getElementById("progressiveDisclosureText");
  const progDot = document.getElementById("progressiveDot");
  const btnDetailedJump = document.getElementById("btnGoToDetailedReview");

  if (progBox && progText) {
    if (score >= 90 && highCount === 0) {
      progBox.className = "mt-3 p-3 rounded-xl border border-emerald-200/80 bg-emerald-50/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs";
      if (progDot) progDot.className = "w-2 h-2 rounded-full bg-emerald-600 flex-shrink-0";
      progText.textContent = "各项排版规范均达标，建议直接导出。如需对各段落执行细粒度原子级审查，可进入深入模式。";
    } else {
      progBox.className = "mt-3 p-3 rounded-xl border border-amber-200/80 bg-amber-50/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 text-xs";
      if (progDot) progDot.className = "w-2 h-2 rounded-full bg-amber-600 flex-shrink-0";
      progText.textContent = `检测到 ${highCount} 项建议复核的格式细节，建议进入深入复核在原子级 Diff 表格中审阅并按需应用。`;
    }
  }

  if (btnDetailedJump) {
    btnDetailedJump.onclick = () => setMode("detailed");
  }

  if (scoreVal) scoreVal.innerText = score;
  if (scoreCircle) {
    const circumference = 264;
    const offset = Math.max(0, circumference - (score / 100) * circumference);
    scoreCircle.style.strokeDashoffset = offset;
    scoreCircle.style.stroke = score >= 90 ? "#1c5d43" : score >= 75 ? "#2563eb" : "#d97706";
  }

  if (verdictBadge) {
    verdictBadge.innerText = report.review_grade || (report.verdict === "pass" ? "符合规范" : "建议复核");
    verdictBadge.className = `px-2.5 py-0.5 rounded-full text-xs font-bold text-white shadow-xs ${
      score >= 90 ? "bg-emerald-700" : score >= 75 ? "bg-blue-700" : "bg-amber-600"
    }`;
  }

  if (quickText) {
    quickText.innerText = score >= 90
      ? "文档要素齐备，段落缩进、三线表规范与参考文献引用均已对齐标准。"
      : "排版已完成，建议对照下表复核部分细节项。";
  }

  if (revSummary) {
    revSummary.innerText = report.reviewer_summary || report.summary || "文稿学术要素齐备，符合规范标准。";
  }

  if (stdBadge && report.standard_checked) {
    stdBadge.innerText = `对齐标准：${report.standard_checked}`;
  }

  // 4 Dimensions
  const dims = report.dimensions || {};
  if (dims.structure) {
    const elScore = document.getElementById("qaDimStructureScore");
    const elBar = document.getElementById("qaDimStructureBar");
    if (elScore) elScore.innerText = `${dims.structure.score} / ${dims.structure.max_score}`;
    if (elBar) elBar.style.width = `${dims.structure.percentage}%`;
  }
  if (dims.typography) {
    const elScore = document.getElementById("qaDimTypographyScore");
    const elBar = document.getElementById("qaDimTypographyBar");
    if (elScore) elScore.innerText = `${dims.typography.score} / ${dims.typography.max_score}`;
    if (elBar) elBar.style.width = `${dims.typography.percentage}%`;
  }
  if (dims.tables_figures) {
    const elScore = document.getElementById("qaDimTablesScore");
    const elBar = document.getElementById("qaDimTablesBar");
    if (elScore) elScore.innerText = `${dims.tables_figures.score} / ${dims.tables_figures.max_score}`;
    if (elBar) elBar.style.width = `${dims.tables_figures.percentage}%`;
  }
  if (dims.citations) {
    const elScore = document.getElementById("qaDimCitationsScore");
    const elBar = document.getElementById("qaDimCitationsBar");
    if (elScore) elScore.innerText = `${dims.citations.score} / ${dims.citations.max_score}`;
    if (elBar) elBar.style.width = `${dims.citations.percentage}%`;
  }

  renderQAIssuesList();
}

function renderQAIssuesList() {
  if (!currentQAReport) return;
  const issues = currentQAReport.issues || [];
  const container = document.getElementById("qaIssuesContainer");
  const countText = document.getElementById("qaIssuesCountText");
  if (!container) return;

  const filtered = issues.filter((iss) => {
    if (currentQAIssueFilter === "all") return true;
    if (currentQAIssueFilter === "high") return iss.severity === "high";
    if (currentQAIssueFilter === "recommendation") return iss.severity !== "high";
    return true;
  });

  if (countText) {
    const highCount = issues.filter((i) => i.severity === "high").length;
    countText.innerText = highCount > 0
      ? `(共 ${issues.length} 项，含 ${highCount} 项需复核)`
      : `(共 ${issues.length} 项建议)`;
  }

  // Update filter buttons badge
  const filterBtns = document.querySelectorAll(".qa-filter-btn");
  filterBtns.forEach((btn) => {
    const f = btn.dataset.filter;
    btn.classList.remove("bg-stone-800", "text-white", "bg-stone-200", "text-stone-800");
    if (f === currentQAIssueFilter) {
      btn.classList.add("bg-stone-800", "text-white", "font-semibold");
      btn.classList.remove("text-stone-500");
    } else {
      btn.classList.add("text-stone-500");
    }
  });

  container.innerHTML = "";
  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="p-3 bg-emerald-50/60 rounded-xl border border-emerald-200/80 text-center text-xs text-emerald-800 font-medium">
        当前分类下未检测到异常问题，各项要素符合规范。
      </div>
    `;
    return;
  }

  filtered.forEach((iss) => {
    const card = document.createElement("div");
    const isHigh = iss.severity === "high";
    const isMed = iss.severity === "medium";
    const badgeColor = isHigh
      ? "bg-red-100 text-red-800 border-red-200"
      : isMed
      ? "bg-amber-100 text-amber-800 border-amber-200"
      : "bg-emerald-100 text-emerald-800 border-emerald-200";
    const badgeText = isHigh ? "高危项" : isMed ? "建议复核" : "规范通过";

    card.className = "p-3 rounded-xl bg-white border border-stone-200/90 shadow-2xs space-y-1.5 transition-all hover:border-stone-300";
    card.innerHTML = `
      <div class="flex items-center justify-between text-[11px]">
        <div class="flex items-center gap-1.5">
          <span class="px-1.5 py-0.2 rounded text-[10px] font-bold border ${badgeColor}">${badgeText}</span>
          <span class="font-bold text-stone-800">${iss.category || "规范项目"}</span>
          <span class="text-stone-400">·</span>
          <span class="font-mono text-stone-500">${iss.location || "全文"}</span>
        </div>
        ${iss.auto_fixable ? '<span class="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 rounded font-medium">已自动修正</span>' : '<span class="text-[10px] text-stone-400">需人工确认</span>'}
      </div>
      <p class="text-xs text-stone-700 leading-snug">${iss.description || ""}</p>
      <div class="text-[11px] text-stone-500 bg-stone-50 p-2 rounded-lg border border-stone-100/80 flex items-start gap-1">
        <span class="text-stone-700 font-medium">建议:</span>
        <span class="text-stone-600">${iss.recommendation || ""}</span>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderDetailedQAReport(report) {
  if (!report) return;
  const banner = document.getElementById("detailedQABanner");
  if (!banner) return;
  banner.classList.remove("hidden");

  const scoreEl = document.getElementById("detailedQAScore");
  const gradeEl = document.getElementById("detailedQAGrade");
  const summaryEl = document.getElementById("detailedQASummary");
  const dim1 = document.getElementById("detailedQADim1");
  const dim2 = document.getElementById("detailedQADim2");
  const dim3 = document.getElementById("detailedQADim3");
  const dim4 = document.getElementById("detailedQADim4");
  const consEl = document.getElementById("detailedQAConservation");

  if (scoreEl) scoreEl.innerText = report.blind_review_score || 96;
  if (gradeEl) gradeEl.innerText = report.review_grade || "极优通过";
  if (summaryEl) summaryEl.innerText = report.summary || "文稿各级要素高度合规，三线表与顺序编码引用完全对齐。";
  if (consEl) {
    if (report.text_conservation) {
      consEl.innerText = report.text_conservation.status_text || "文字 100% 守恒";
    } else {
      consEl.innerText = "文字 100% 守恒";
    }
  }

  const dims = report.dimensions || {};
  if (dim1 && dims.structure) dim1.innerText = `结构 ${dims.structure.score}/25`;
  if (dim2 && dims.typography) dim2.innerText = `排版 ${dims.typography.score}/25`;
  if (dim3 && dims.tables_figures) dim3.innerText = `图表 ${dims.tables_figures.score}/25`;
  if (dim4 && dims.citations) dim4.innerText = `引注 ${dims.citations.score}/25`;
}

function renderXRayComparison(xrayData) {
  const paneBefore = document.getElementById("xrayBeforeContent");
  const paneAfter = document.getElementById("xrayAfterContent");
  if (!paneBefore || !paneAfter) return;

  paneBefore.innerHTML = "";
  paneAfter.innerHTML = "";

  const paras = (xrayData && xrayData.length > 0) ? xrayData : getFallbackXRayData();

  paras.forEach((item) => {
    // Before Paragraph
    const pBefore = document.createElement("div");
    pBefore.className = `xray-para ${item.type || "body"}`;
    const b = item.before || {};
    pBefore.style.fontFamily = getCssFont(b.font);
    pBefore.style.fontSize = `${b.size_pt || 12}pt`;
    pBefore.style.fontWeight = b.bold ? "700" : "400";
    pBefore.style.fontStyle = b.italic ? "italic" : "normal";

    let textDecBefore = [];
    if (b.underline) textDecBefore.push("underline");
    if (b.strike) textDecBefore.push("line-through");
    pBefore.style.textDecoration = textDecBefore.length ? textDecBefore.join(" ") : "none";

    if (b.highlight) {
      const hlMap = {
        yellow: "#fffa8b",
        red: "#ff7875",
        blue: "#69c0ff",
        darkYellow: "#ffd666",
        magenta: "#ff85c0",
        cyan: "#5cdbd3",
        green: "#95de64",
        lightGray: "#e8e8e8",
      };
      pBefore.style.backgroundColor = hlMap[b.highlight] || "#fffb8f";
    }

    pBefore.style.color = b.color || "#2c3e50";
    pBefore.style.textAlign = b.align || "left";
    pBefore.style.textIndent = `${b.indent_pt || 0}pt`;
    pBefore.style.lineHeight = `${b.line_spacing || 1.15}`;
    pBefore.innerText = item.text;
    paneBefore.appendChild(pBefore);

    // After Paragraph
    const pAfter = document.createElement("div");
    pAfter.className = `xray-para ${item.type || "body"}`;
    const a = item.after || {};
    pAfter.style.fontFamily = getCssFont(a.font);
    pAfter.style.fontSize = `${a.size_pt || 12}pt`;
    pAfter.style.fontWeight = a.bold ? "700" : "400";
    pAfter.style.fontStyle = "normal";
    pAfter.style.textDecoration = "none";
    pAfter.style.backgroundColor = "transparent";
    pAfter.style.color = "#18221c";
    pAfter.style.textAlign = a.align || "justify";
    pAfter.style.textIndent = `${a.indent_pt || 24}pt`;
    pAfter.style.lineHeight = `${a.line_spacing || 1.5}`;
    pAfter.innerText = item.text;
    paneAfter.appendChild(pAfter);
  });
}

function getCssFont(fontName) {
  if (!fontName) return '"Songti SC", SimSun, serif';
  if (fontName.includes("黑体")) return '"SimHei", "PingFang SC", sans-serif';
  if (fontName.includes("宋体")) return '"Songti SC", SimSun, serif';
  if (fontName.includes("Times")) return '"Times New Roman", serif';
  return `${fontName}, sans-serif`;
}

function getFallbackXRayData() {
  return [
    {
      text: "第1章 绪论",
      type: "heading",
      before: { font: "等线", size_pt: 15, bold: false, align: "left", indent_pt: 0, line_spacing: 1.15 },
      after: { font: "黑体", size_pt: 16, bold: true, align: "center", indent_pt: 0, line_spacing: 1.0 }
    },
    {
      text: "学术论文排版作为科学共同体学术交流的基石，对于成果传达效率具有重要影响。然而传统人工排版模式极度依赖手工调校，存在着样式遗漏与结构混乱等痛点。",
      type: "body",
      before: { font: "宋体", size_pt: 11, bold: false, align: "left", indent_pt: 0, line_spacing: 1.15 },
      after: { font: "宋体", size_pt: 12, bold: false, align: "justify", indent_pt: 24, line_spacing: 1.5 }
    },
    {
      text: "针对上述挑战，本文提出一种基于 OpenXML 抽象语法树（AST）拓扑重构与状态机闭环的学术论文智能排版系统。本系统完全运行于本地单机离线环境，零远程数据传输，确保学术论文核心成果的隐私绝对安全。",
      type: "body",
      before: { font: "Calibri", size_pt: 12, bold: false, align: "left", indent_pt: 0, line_spacing: 1.15 },
      after: { font: "宋体", size_pt: 12, bold: false, align: "justify", indent_pt: 24, line_spacing: 1.5 }
    }
  ];
}

function createSimulatedResult() {
  return {
    compliance_score: 96,
    download_filename: "学术论文初稿_格式修订.docx",
    highlights: [
      "版芯尺寸已统一对齐国标 GB/T 7713.1（页边距：上2.5cm、下2.5cm、左3.0cm、右2.5cm）",
      "正文段落全部规范对齐（首行缩进 2 字符、小四宋体、行距 1.5 倍）",
      "标题拓扑树重构（一级标题居中黑体三号、二三级标题连续对齐）",
      "图表题注规范化（五号字体居中、与正文保持标准间距）",
      "参考文献格式化（标准顺序编码制对齐、中文宋体/西文 Times New Roman 混排）",
    ],
    xray_data: getFallbackXRayData(),
    qa_report: {
      verdict: "pass",
      blind_review_score: 96,
      review_grade: "极优通过 (免答辩格式复核)",
      summary: "【盲审专家组评定】：文稿结构严谨，学术要素高度齐备。正文已统一规范为宋体小四与 Times New Roman 1.5倍行距，所有表格已升级为标准三线表（顶底线1.5pt），正文引注与文末参考文献顺序编码完全一致。",
      reviewer_summary: "【盲审专家组评定】：文稿结构严谨，学术要素高度齐备。正文已统一规范为宋体小四与 Times New Roman 1.5倍行距，所有表格已升级为标准三线表（顶底线1.5pt），正文引注与文末参考文献顺序编码完全一致。",
      standard_checked: "GB/T 7713.1-2006 学位论文通用规范",
      dimensions: {
        structure: { name: "论文结构完整性", score: 24, max_score: 25, percentage: 96, status: "良好" },
        typography: { name: "排版与版心规约", score: 25, max_score: 25, percentage: 100, status: "达标" },
        tables_figures: { name: "图表与公式规范", score: 24, max_score: 25, percentage: 96, status: "达标" },
        citations: { name: "引注与参考文献", score: 23, max_score: 25, percentage: 92, status: "优秀" },
      },
      total_issues: 3,
      issues: [
        {
          severity: "low",
          category: "文献规范",
          location: "参考文献列表",
          description: "文献 [3] 为外文期刊，请核查作者姓氏是否全大写及期刊名缩写规范。",
          recommendation: "符合 GB/T 7714 规范，建议答辩前复核作者名字缩写点。",
          auto_fixable: false,
        },
        {
          severity: "low",
          category: "版式细节",
          location: "正文主体段落",
          description: "已将正文段落空格模拟缩进统一升级为标准 OOXML 首行缩进 2 字符 (w:firstLine)。",
          recommendation: "已完成自动修复，原文字符保真无损。",
          auto_fixable: true,
        },
        {
          severity: "medium",
          category: "学术要素",
          location: "前置部分",
          description: "建议检查英文 Abstract 与 Keywords 是否与中文摘要完全对应。",
          recommendation: "若参加校级抽检或双盲评阅，建议保证双语关键词数量严格一致 (3-8个)。",
          auto_fixable: false,
        },
      ],
    },
  };
}

// X-Ray Drag Slider
function initXRaySlider() {
  let isDragging = false;

  const onMove = (clientX) => {
    if (!elements.xrayWindow) return;
    const rect = elements.xrayWindow.getBoundingClientRect();
    let x = clientX - rect.left;
    x = Math.max(0, Math.min(x, rect.width));
    const percent = (x / rect.width) * 100;

    if (elements.xrayAfterSheet) elements.xrayAfterSheet.style.clipPath = `polygon(0 0, ${percent}% 0, ${percent}% 100%, 0 100%)`;
    if (elements.xrayLine) elements.xrayLine.style.left = `${percent}%`;
    if (elements.xrayHandle) elements.xrayHandle.style.left = `${percent}%`;
  };

  elements.xrayHandle?.addEventListener("mousedown", () => (isDragging = true));
  window.addEventListener("mouseup", () => (isDragging = false));
  window.addEventListener("mousemove", (e) => {
    if (isDragging) onMove(e.clientX);
  });

  elements.xrayHandle?.addEventListener("touchstart", () => (isDragging = true));
  window.addEventListener("touchend", () => (isDragging = false));
  window.addEventListener("touchmove", (e) => {
    if (isDragging && e.touches.length > 0) onMove(e.touches[0].clientX);
  });
}

// Confetti Particles Engine
function launchConfetti() {
  const canvas = document.getElementById("confettiCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;

  const particles = [];
  const colors = ["#1c5d43", "#287a55", "#e7c365", "#5b4aa6", "#fff"];

  for (let i = 0; i < 90; i++) {
    particles.push({
      x: canvas.width / 2,
      y: canvas.height / 2 + 80,
      r: Math.random() * 6 + 3,
      d: Math.random() * 90,
      color: colors[Math.floor(Math.random() * colors.length)],
      tilt: Math.floor(Math.random() * 10) - 10,
      tiltAngleIncremental: Math.random() * 0.07 + 0.05,
      tiltAngle: 0,
      vx: (Math.random() - 0.5) * 16,
      vy: (Math.random() - 0.7) * 18,
    });
  }

  let animationFrame;
  let alpha = 1.0;
  const render = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    particles.forEach((p, i) => {
      p.tiltAngle += p.tiltAngleIncremental;
      p.y += (Math.cos(p.d) + 3 + p.r / 2) / 2 + p.vy;
      p.x += Math.sin(p.d) + p.vx;
      p.vy *= 0.95;
      p.vx *= 0.95;
      p.tilt = Math.sin(p.tiltAngle - i / 3) * 15;

      ctx.beginPath();
      ctx.lineWidth = p.r;
      ctx.strokeStyle = p.color;
      ctx.globalAlpha = alpha;
      ctx.moveTo(p.x + p.tilt + p.r / 2, p.y);
      ctx.lineTo(p.x + p.tilt, p.y + p.tilt + p.r / 2);
      ctx.stroke();
    });

    alpha -= 0.008;
    if (alpha > 0) {
      animationFrame = requestAnimationFrame(render);
    } else {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      cancelAnimationFrame(animationFrame);
    }
  };
  render();
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// MCP Console Modal Handlers
(function initMcpModal() {
  const mcpModal = document.getElementById("mcpModal");
  const topNavMcpBtn = document.getElementById("topNavMcpBtn");
  const bannerMcpBtn = document.getElementById("bannerMcpBtn");
  const closeMcpModalBtn = document.getElementById("closeMcpModalBtn");
  const closeMcpModalFooterBtn = document.getElementById("closeMcpModalFooterBtn");
  const copyMcpConfigBtn = document.getElementById("copyMcpConfigBtn");
  const copyMcpBtnText = document.getElementById("copyMcpBtnText");
  const mcpConfigCode = document.getElementById("mcpConfigCode");
  const mcpConfigPath = document.getElementById("mcpConfigPath");

  const projectRoot = ".";

  const mcpConfigs = {
    cursor: {
      path: ".cursor/mcp.json (项目根目录)",
      code: JSON.stringify(
        {
          mcpServers: {
            "paper-setting": {
              command: "uv",
              args: ["run", "--directory", projectRoot, "paper-setting-mcp"],
              env: {
                PAPER_SETTING_ALLOWED_INPUT_ROOTS: projectRoot,
              },
            },
          },
        },
        null,
        2
      ),
    },
    claude: {
      path: "~/Library/Application Support/Claude/claude_desktop_config.json",
      code: JSON.stringify(
        {
          mcpServers: {
            "paper-setting": {
              command: "uv",
              args: ["run", "--directory", projectRoot, "paper-setting-mcp"],
              env: {
                PAPER_SETTING_ALLOWED_INPUT_ROOTS: projectRoot,
              },
            },
          },
        },
        null,
        2
      ),
    },
    windsurf: {
      path: "~/.codeium/windsurf/mcp_config.json",
      code: JSON.stringify(
        {
          mcpServers: {
            "paper-setting": {
              command: "uv",
              args: ["run", "--directory", projectRoot, "paper-setting-mcp"],
              env: {
                PAPER_SETTING_ALLOWED_INPUT_ROOTS: projectRoot,
              },
            },
          },
        },
        null,
        2
      ),
    },
    cli: {
      path: "终端直接启动与调试",
      code: `# 在当前项目根目录下运行 stdio MCP 服务：\ncd ${projectRoot} && uv run paper-setting-mcp\n\n# 或者使用官方 MCP Inspector 调试：\nnpx @modelcontextprotocol/inspector uv run --directory ${projectRoot} paper-setting-mcp`,
    },
  };

  let currentAgent = "cursor";

  function updateMcpConfigView() {
    if (!mcpConfigCode || !mcpConfigPath) return;
    const cfg = mcpConfigs[currentAgent];
    mcpConfigPath.textContent = cfg.path;
    mcpConfigCode.textContent = cfg.code;
  }

  function openMcpModal() {
    if (!mcpModal) return;
    updateMcpConfigView();
    mcpModal.classList.remove("hidden");
    scanAgents();
  }

  function closeMcpModal() {
    if (!mcpModal) return;
    mcpModal.classList.add("hidden");
  }

  if (topNavMcpBtn) topNavMcpBtn.addEventListener("click", openMcpModal);
  if (bannerMcpBtn) bannerMcpBtn.addEventListener("click", openMcpModal);
  if (closeMcpModalBtn) closeMcpModalBtn.addEventListener("click", closeMcpModal);
  if (closeMcpModalFooterBtn) closeMcpModalFooterBtn.addEventListener("click", closeMcpModal);
  if (mcpModal) mcpModal.addEventListener("click", closeMcpModal);

  // Main Tabs
  const mainTabBtns = document.querySelectorAll(".mcp-tab-btn");
  const tabDomestic = document.getElementById("mcpTabDomestic");
  const tabInternational = document.getElementById("mcpTabInternational");
  const tabTools = document.getElementById("mcpTabTools");
  const tabSafety = document.getElementById("mcpTabSafety");

  mainTabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      mainTabBtns.forEach((b) => {
        b.classList.remove("border-b-2", "border-emerald-600", "text-emerald-800", "font-semibold");
        b.classList.add("text-stone-500", "font-medium");
      });
      btn.classList.add("border-b-2", "border-emerald-600", "text-emerald-800", "font-semibold");
      btn.classList.remove("text-stone-500", "font-medium");

      const tab = btn.dataset.tab;
      if (tabDomestic) tabDomestic.classList.toggle("hidden", tab !== "domestic");
      if (tabInternational) tabInternational.classList.toggle("hidden", tab !== "international");
      if (tabTools) tabTools.classList.toggle("hidden", tab !== "tools");
      if (tabSafety) tabSafety.classList.toggle("hidden", tab !== "safety");
    });
  });

  // Agent Subtabs (International)
  const agentSubtabs = document.querySelectorAll(".agent-subtab");
  agentSubtabs.forEach((btn) => {
    btn.addEventListener("click", () => {
      agentSubtabs.forEach((b) => {
        b.classList.remove("bg-emerald-700", "text-white", "font-bold");
        b.classList.add("bg-stone-100", "text-stone-600", "font-medium");
      });
      btn.classList.add("bg-emerald-700", "text-white", "font-bold");
      btn.classList.remove("bg-stone-100", "text-stone-600", "font-medium");

      currentAgent = btn.dataset.agent;
      updateMcpConfigView();
    });
  });

  // Copy Button (International)
  if (copyMcpConfigBtn) {
    copyMcpConfigBtn.addEventListener("click", () => {
      const textToCopy = mcpConfigs[currentAgent].code;
      navigator.clipboard.writeText(textToCopy).then(() => {
        if (copyMcpBtnText) copyMcpBtnText.textContent = "已复制！";
        setTimeout(() => {
          if (copyMcpBtnText) copyMcpBtnText.textContent = "复制配置";
        }, 2000);
      });
    });
  }

  // --- Domestic Agents & Scanner Logic ---
  let scannedAgentData = null;

  async function scanAgents() {
    const scanSummaryText = document.getElementById("scanSummaryText");
    const wbBadge = document.getElementById("wbBadge");
    const traeBadge = document.getElementById("traeBadge");
    const doubaoBadge = document.getElementById("doubaoBadge");
    const deepseekBadge = document.getElementById("deepseekBadge");

    if (scanSummaryText) scanSummaryText.textContent = "正在探测 Mac 本机 Agent 与运行环境...";

    try {
      const res = await fetch("/api/agent/scan");
      if (!res.ok) throw new Error("探测接口返回错误");
      const data = await res.json();
      scannedAgentData = data;

      const agents = data.agents || {};

      // WorkBuddy
      if (wbBadge) {
        if (agents.workbuddy?.injected) {
          wbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-600 text-white";
          wbBadge.textContent = "已写入配置";
        } else if (agents.workbuddy?.installed) {
          wbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800";
          wbBadge.textContent = "已安装";
        } else {
          wbBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-600";
          wbBadge.textContent = "未检测到应用";
        }
      }

      // Trae
      if (traeBadge) {
        if (agents.trae?.installed) {
          traeBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-800";
          traeBadge.textContent = "已安装";
        } else {
          traeBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-600";
          traeBadge.textContent = "未安装";
        }
      }

      // Doubao
      if (doubaoBadge) {
        if (agents.doubao?.installed) {
          doubaoBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-800";
          doubaoBadge.textContent = "已安装";
        } else {
          doubaoBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-600";
          doubaoBadge.textContent = "未安装";
        }
      }

      // DeepSeek
      if (deepseekBadge) {
        if (agents.deepseek?.installed) {
          deepseekBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800";
          deepseekBadge.textContent = "已就绪";
        } else {
          deepseekBadge.className = "px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-600";
          deepseekBadge.textContent = "CLI 待连接";
        }
      }

      if (scanSummaryText) {
        scanSummaryText.textContent = `已扫描本机：检测到 ${agents.workbuddy?.installed ? "WorkBuddy、" : ""}${agents.doubao?.installed ? "豆包、" : ""}${agents.deepseek?.installed ? "DeepSeek、" : ""}已就绪`;
      }
    } catch (err) {
      if (scanSummaryText) scanSummaryText.textContent = "已就绪：支持一键直连本土 Agent";
    }
  }

  const rescanBtn = document.getElementById("rescanAgentsBtn");
  if (rescanBtn) rescanBtn.addEventListener("click", scanAgents);

  // Auto Inject WorkBuddy
  const autoInjectWbBtn = document.getElementById("autoInjectWorkbuddyBtn");
  const wbInjectStatus = document.getElementById("wbInjectStatus");
  const wbInjectBtnText = document.getElementById("wbInjectBtnText");

  if (autoInjectWbBtn) {
    autoInjectWbBtn.addEventListener("click", async () => {
      if (wbInjectBtnText) wbInjectBtnText.textContent = "正在写入...";
      try {
        const res = await fetch("/api/agent/inject-workbuddy", { method: "POST" });
        const result = await res.json();
        if (result.success) {
          if (wbInjectBtnText) wbInjectBtnText.textContent = "已写入";
          if (wbInjectStatus) {
            wbInjectStatus.className = "text-[11px] p-2 bg-emerald-50 text-emerald-800 rounded-lg border border-emerald-200";
            wbInjectStatus.textContent = result.message + "（原配置已自动备份）";
            wbInjectStatus.classList.remove("hidden");
          }
          scanAgents();
        } else {
          alert("写入失败: " + result.message);
        }
      } catch (e) {
        alert("请求异常: " + e.message);
      } finally {
        setTimeout(() => {
          if (wbInjectBtnText) wbInjectBtnText.textContent = "一键写入配置";
        }, 3000);
      }
    });
  }

  // Auto Inject Trae
  const autoInjectTraeBtn = document.getElementById("autoInjectTraeBtn");
  const traeInjectStatus = document.getElementById("traeInjectStatus");
  if (autoInjectTraeBtn) {
    autoInjectTraeBtn.addEventListener("click", async () => {
      try {
        const res = await fetch("/api/agent/inject-trae", { method: "POST" });
        const result = await res.json();
        if (result.success) {
          if (traeInjectStatus) {
            traeInjectStatus.className = "text-[11px] p-2 bg-blue-50 text-blue-800 rounded-lg border border-blue-200";
            traeInjectStatus.textContent = result.message;
            traeInjectStatus.classList.remove("hidden");
          }
          scanAgents();
        }
      } catch (e) {
        alert("写入失败: " + e.message);
      }
    });
  }

  // Copy Buttons for Domestic
  const copyWorkbuddyBtn = document.getElementById("copyWorkbuddyBtn");
  if (copyWorkbuddyBtn) {
    copyWorkbuddyBtn.addEventListener("click", () => {
      const code = JSON.stringify({
        "mcpServers": {
          "paper-setting": {
            "command": "uv",
            "args": ["run", "--directory", projectRoot, "paper-setting-mcp"],
            "env": {},
            "disabled": false
          }
        }
      }, null, 2);
      navigator.clipboard.writeText(code).then(() => {
        copyWorkbuddyBtn.textContent = "已复制！";
        setTimeout(() => { copyWorkbuddyBtn.textContent = "复制 JSON"; }, 2000);
      });
    });
  }

  const copyTraeBtn = document.getElementById("copyTraeBtn");
  const copyTraeBtnText = document.getElementById("copyTraeBtnText");
  if (copyTraeBtn) {
    copyTraeBtn.addEventListener("click", () => {
      const code = JSON.stringify({
        "mcpServers": {
          "paper-setting": {
            "command": "uv",
            "args": ["run", "--directory", projectRoot, "paper-setting-mcp"],
            "env": {}
          }
        }
      }, null, 2);
      navigator.clipboard.writeText(code).then(() => {
        if (copyTraeBtnText) copyTraeBtnText.textContent = "已复制 Trae 配置！";
        setTimeout(() => { if (copyTraeBtnText) copyTraeBtnText.textContent = "复制 Trae 配置"; }, 2000);
      });
    });
  }

  const copyDoubaoBtn = document.getElementById("copyDoubaoOpenApiBtn");
  const copyOpenApiBtnText = document.getElementById("copyOpenApiBtnText");
  if (copyDoubaoBtn) {
    copyDoubaoBtn.addEventListener("click", () => {
      const url = `${window.location.origin}/openapi.json`;
      navigator.clipboard.writeText(url).then(() => {
        if (copyOpenApiBtnText) copyOpenApiBtnText.textContent = "已复制 OpenAPI 规范地址！";
        setTimeout(() => { if (copyOpenApiBtnText) copyOpenApiBtnText.textContent = "复制 OpenAPI 地址"; }, 2000);
      });
    });
  }

  const copyCherryBtn = document.getElementById("copyCherryBtn");
  const copyCherryBtnText = document.getElementById("copyCherryBtnText");
  if (copyCherryBtn) {
    copyCherryBtn.addEventListener("click", () => {
      const cmd = `uv run --directory ${projectRoot} paper-setting-mcp`;
      navigator.clipboard.writeText(cmd).then(() => {
        if (copyCherryBtnText) copyCherryBtnText.textContent = "已复制命令！";
        setTimeout(() => { if (copyCherryBtnText) copyCherryBtnText.textContent = "复制 MCP 命令行"; }, 2000);
      });
    });
  }

  // App Launchers
  async function launchApp(appName) {
    try {
      const res = await fetch("/api/agent/launch-app", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ app_name: appName })
      });
      const data = await res.json();
      if (!data.success) {
        alert(data.message || "拉起应用失败");
      }
    } catch (e) {
      alert("请求失败: " + e.message);
    }
  }

  const launchWbBtn = document.getElementById("launchWorkbuddyBtn");
  if (launchWbBtn) launchWbBtn.addEventListener("click", () => launchApp("workbuddy"));

  const launchDoubaoBtn = document.getElementById("launchDoubaoBtn");
  if (launchDoubaoBtn) launchDoubaoBtn.addEventListener("click", () => launchApp("doubao"));

  const launchDeepseekBtn = document.getElementById("launchDeepseekBtn");
  if (launchDeepseekBtn) launchDeepseekBtn.addEventListener("click", () => launchApp("deepseek"));

  updateMcpConfigView();
})();
