const sampleNovel = `第一章 雾港来信
清晨，雾港的码头被潮气盖住，林澈站在废弃售票亭前，手里捏着一封没有署名的信。信纸被海风吹得发皱，上面只有一句话：午夜以前，不要相信沈雾。
周栩从街角跑来，压低声音说：“你真的要去旧灯塔？那里昨晚又有人失踪。”
林澈望向远处若隐若现的灯塔，沉默片刻说：“我必须知道父亲当年留下了什么。”
两人刚要离开，售票亭的门突然自己打开，里面传来老式电话的铃声。林澈接起电话，只听见一个沙哑的声音提醒：“信不是给你的。”

第二章 旧灯塔
夜晚，雨水敲在灯塔的铁门上。沈雾撑着黑伞站在门外，像是早就知道林澈会来。
沈雾冷静地说：“你拿到那封信，就已经进局了。”
林澈愤怒地问：“我父亲的失踪和你有关吗？”
沈雾没有回答，只把一枚生锈的钥匙放进林澈掌心。灯塔深处传来脚步声，周栩突然发现墙上刻着林澈父亲的名字。
三人沿着旋梯向上，灯光突然熄灭。黑暗里，有人低声说：“别让他看到档案。”

第三章 档案室
黎明前，灯塔地下的档案室终于被打开。满墙照片记录着雾港十年来所有失踪者，林澈发现每张照片背后都有同一个符号。
周栩紧张地喊：“有人在靠近！”
沈雾迅速关上门，解释说：“你父亲不是失踪，他是在保护最后一份名单。”
林澈翻开档案，终于看见父亲留下的录音笔。录音里传出熟悉的声音：“林澈，如果你听到这里，说明雾港已经没有退路。”
门外的撞击声越来越近，林澈决定带着名单离开。`;

const titleInput = document.querySelector("#titleInput");
const modeInput = document.querySelector("#modeInput");
const densityInput = document.querySelector("#densityInput");
const engineInput = document.querySelector("#engineInput");
const charactersInput = document.querySelector("#charactersInput");
const themesInput = document.querySelector("#themesInput");
const novelInput = document.querySelector("#novelInput");
const yamlOutput = document.querySelector("#yamlOutput");
const outlineOutput = document.querySelector("#outlineOutput");
const yamlFrame = document.querySelector(".yaml-frame");
const yamlViewBtn = document.querySelector("#yamlViewBtn");
const outlineViewBtn = document.querySelector("#outlineViewBtn");
const warningBox = document.querySelector("#warningBox");
const engineBox = document.querySelector("#engineBox");
const convertBtn = document.querySelector("#convertBtn");
const loadSampleBtn = document.querySelector("#loadSampleBtn");
const fileInput = document.querySelector("#fileInput");
const cleanupBtn = document.querySelector("#cleanupBtn");
const analyzeBtn = document.querySelector("#analyzeBtn");
const copyBtn = document.querySelector("#copyBtn");
const downloadBtn = document.querySelector("#downloadBtn");
const exportFormatInput = document.querySelector("#exportFormatInput");
const clearBtn = document.querySelector("#clearBtn");
const qualityBox = document.querySelector("#qualityBox");
const qualityScore = document.querySelector("#qualityScore");
const qualityStatus = document.querySelector("#qualityStatus");
const qualityMetrics = document.querySelector("#qualityMetrics");
const qualityChecks = document.querySelector("#qualityChecks");
const analysisBox = document.querySelector("#analysisBox");
const analysisStatus = document.querySelector("#analysisStatus");
const analysisSummary = document.querySelector("#analysisSummary");
const analysisWarnings = document.querySelector("#analysisWarnings");
const chapterList = document.querySelector("#chapterList");

let latestYaml = "";
let latestScript = null;
let appConfig = {
  ai: {
    enabled: false,
    model: "",
    provider: ""
  }
};

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

titleInput.value = "";
charactersInput.value = "";
themesInput.value = "";

function setStats(stats = {}) {
  document.querySelector("#chapterStat").textContent = stats.chapters ?? 0;
  document.querySelector("#characterStat").textContent = stats.characters ?? 0;
  document.querySelector("#sceneStat").textContent = stats.scenes ?? 0;
  document.querySelector("#beatStat").textContent = stats.beats ?? 0;
}

function setWarnings(warnings = []) {
  if (!warnings.length) {
    warningBox.hidden = true;
    warningBox.textContent = "";
    return;
  }

  warningBox.hidden = false;
  warningBox.textContent = warnings.join(" ");
}

function setEngineMessage(message = "") {
  if (!message) {
    engineBox.hidden = true;
    engineBox.textContent = "";
    return;
  }

  engineBox.hidden = false;
  engineBox.textContent = message;
}

function statusLabel(status) {
  if (status === "ready") return "输入可转换";
  if (status === "needs_fix") return "需要修正";
  return "建议复核";
}

function setAnalysis(analysis) {
  if (!analysis) {
    analysisBox.hidden = false;
    analysisStatus.textContent = "等待分析";
    analysisSummary.textContent = "";
    analysisWarnings.textContent = "";
    analysisWarnings.classList.remove("show");
    chapterList.textContent = "";
    return;
  }

  analysisBox.hidden = false;
  analysisStatus.textContent = statusLabel(analysis.status);
  analysisSummary.innerHTML = [
    ["章节", analysis.summary.chapter_count],
    ["字数", analysis.summary.chars],
    ["段落", analysis.summary.paragraphs],
    ["对白", analysis.summary.dialogues]
  ]
    .map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`)
    .join("");

  if (analysis.warnings?.length) {
    analysisWarnings.textContent = analysis.warnings.join(" ");
    analysisWarnings.classList.add("show");
  } else {
    analysisWarnings.textContent = "";
    analysisWarnings.classList.remove("show");
  }

  chapterList.innerHTML = analysis.chapters
    .map((chapter) => `
      <div class="chapter-row">
        <div><span>章节</span><strong>${chapter.title}</strong></div>
        <div><span>字数</span><strong>${chapter.chars}</strong></div>
        <div><span>段落</span><strong>${chapter.paragraphs}</strong></div>
        <div><span>对白</span><strong>${chapter.dialogues}</strong></div>
      </div>`)
    .join("");
}

async function analyzeInput() {
  if (!novelInput.value.trim()) {
    setAnalysis();
    return;
  }

  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      text: novelInput.value,
      characters: charactersInput.value
    })
  });
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "分析失败");
  setAnalysis(data);
}

async function cleanupInput() {
  if (!novelInput.value.trim()) {
    setAnalysis();
    return;
  }

  cleanupBtn.disabled = true;
  try {
    const response = await fetch("/api/cleanup", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        text: novelInput.value
      })
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "清洗失败");
    novelInput.value = data.text;
    await analyzeInput();
    const removed = data.stats?.removed_lines ?? 0;
    const originalChars = data.stats?.original_chars ?? 0;
    const cleanedChars = data.stats?.cleaned_chars ?? 0;
    analysisWarnings.textContent = `已清洗文本：移除 ${removed} 行噪声，字数 ${originalChars} → ${cleanedChars}。`;
    analysisWarnings.classList.add("show");
  } catch (error) {
    analysisWarnings.textContent = error instanceof Error ? error.message : "清洗失败";
    analysisWarnings.classList.add("show");
  } finally {
    cleanupBtn.disabled = false;
  }
}

function statusText(status) {
  if (status === "ready") return "结构完整";
  if (status === "review") return "建议复核";
  if (status === "needs_fix") return "需要修正";
  return "等待输入";
}

function setQuality(quality) {
  if (!quality) {
    qualityBox.hidden = true;
    qualityScore.textContent = "0";
    qualityStatus.textContent = "等待输入";
    qualityMetrics.textContent = "";
    qualityChecks.textContent = "";
    return;
  }

  qualityBox.hidden = false;
  qualityScore.textContent = quality.score;
  qualityStatus.textContent = statusText(quality.status);
  qualityMetrics.innerHTML = [
    ["输入字数", quality.metrics.input_chars],
    ["平均章长", quality.metrics.average_chapter_chars],
    ["对白节拍", quality.metrics.dialogue_beat_count],
    ["预计时长", `${quality.metrics.estimated_runtime_minutes || 0} 分钟`],
    ["场均时长", `${quality.metrics.average_scene_minutes || 0} 分钟`],
    ["章节覆盖", `${quality.metrics.source_coverage_rate || 0}%`],
    ["修订任务", quality.metrics.revision_task_count || 0]
  ]
    .map(([label, value]) => `<div><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
  qualityChecks.innerHTML = quality.checks
    .map((check) => `<span class="quality-pill ${check.passed ? "pass" : "fail"}" title="${check.message}">${check.passed ? "✓" : "!"} ${check.label}</span>`)
    .join("");
}

function beatTypeLabel(type) {
  if (type === "dialogue") return "对白";
  if (type === "narration") return "旁白";
  if (type === "transition") return "转场";
  return "动作";
}

function renderOutline(script) {
  if (!script) {
    outlineOutput.innerHTML = '<div class="outline-empty">等待转换...</div>';
    return;
  }

  const characters = script.characters?.length
    ? `<section class="outline-section">
        <h3 class="outline-title">角色</h3>
        <div class="character-list">
          ${script.characters.map((character) => `
            <div class="character-card">
              <div class="character-head">
                <strong>${escapeHtml(character.name)}</strong>
                <span>${escapeHtml(character.role || "角色")}</span>
              </div>
              <div class="outline-grid">
                <div class="outline-field"><span>目标</span><strong>${escapeHtml(character.goal || "待确认")}</strong></div>
                <div class="outline-field"><span>弧光</span><strong>${escapeHtml(character.arc || "待补充")}</strong></div>
              </div>
              <div class="outline-meta">
                <span class="outline-chip">首次：${escapeHtml(character.first_appearance || "待确认")}</span>
                <span class="outline-chip">出场：${escapeHtml((character.appearances || []).length)} 场</span>
              </div>
            </div>`).join("")}
        </div>
      </section>`
    : "";

  const acts = (script.acts || [])
    .map((act) => `
      <section class="outline-section">
        <h3 class="outline-title">${escapeHtml(act.title)}</h3>
        <div class="outline-meta">
          <span class="outline-chip">${escapeHtml(act.id)}</span>
          <span class="outline-chip">${escapeHtml(act.purpose || "待确认")}</span>
          ${act.estimated_runtime_minutes ? `<span class="outline-chip">${escapeHtml(act.estimated_runtime_minutes)} 分钟</span>` : ""}
        </div>
        ${(act.scenes || []).map((scene) => `
          <div class="outline-section">
            <h4 class="outline-title">${escapeHtml(scene.title)}</h4>
            <div class="outline-meta">
              <span class="outline-chip">${escapeHtml(scene.location)}</span>
              <span class="outline-chip">${escapeHtml(scene.time)}</span>
              <span class="outline-chip">${escapeHtml(scene.mood)}</span>
              <span class="outline-chip">${escapeHtml(scene.source_chapter)}</span>
              ${scene.estimated_runtime_minutes ? `<span class="outline-chip">${escapeHtml(scene.estimated_runtime_minutes)} 分钟</span>` : ""}
            </div>
            <p class="outline-text">${escapeHtml(scene.summary)}</p>
            <div class="outline-grid">
              <div class="outline-field"><span>目标</span><strong>${escapeHtml(scene.objective || "待确认")}</strong></div>
              <div class="outline-field"><span>阻碍</span><strong>${escapeHtml(scene.obstacle || scene.conflict)}</strong></div>
              <div class="outline-field"><span>结果</span><strong>${escapeHtml(scene.outcome || "待确认")}</strong></div>
              <div class="outline-field"><span>转折</span><strong>${escapeHtml(scene.turning_point)}</strong></div>
            </div>
            ${(scene.props || []).length ? `
              <div class="outline-props">
                <span>道具/线索</span>
                <div class="outline-meta">
                  ${scene.props.map((prop) => `<span class="outline-chip">${escapeHtml(prop)}</span>`).join("")}
                </div>
              </div>` : ""}
            <div class="beat-list">
              ${(scene.beats || []).slice(0, 8).map((beat) => `
                <div class="beat-item">
                  <div class="beat-type">${beatTypeLabel(beat.type)}${beat.speaker ? ` · ${escapeHtml(beat.speaker)}` : ""}</div>
                  <div>${escapeHtml(beat.text)}</div>
                </div>`).join("")}
            </div>
          </div>`).join("")}
      </section>`)
    .join("");

  const productionNotes = script.production_notes || {};
  const sourceCoverage = productionNotes.source_coverage || [];
  const coverageSection = sourceCoverage.length
    ? `<section class="outline-section">
        <h3 class="outline-title">来源覆盖</h3>
        <div class="character-list">
          ${sourceCoverage.map((item) => `
            <div class="character-card">
              <div class="character-head">
                <strong>${escapeHtml(item.chapter || "未命名章节")}</strong>
                <span>${item.covered ? "已覆盖" : "需检查"}</span>
              </div>
              <div class="outline-grid">
                <div class="outline-field"><span>场景</span><strong>${escapeHtml(item.scene_count || 0)} 场</strong></div>
                <div class="outline-field"><span>节拍</span><strong>${escapeHtml(item.beat_count || 0)} 个</strong></div>
              </div>
              <div class="outline-meta">
                ${(item.scene_ids || []).map((sceneId) => `<span class="outline-chip">${escapeHtml(sceneId)}</span>`).join("")}
              </div>
              ${item.coverage_note ? `<p class="outline-text">${escapeHtml(item.coverage_note)}</p>` : ""}
            </div>`).join("")}
        </div>
      </section>`
    : "";
  const runtimePlan = productionNotes.runtime_plan || {};
  const runtimeSection = productionNotes.estimated_runtime_minutes || runtimePlan.pacing
    ? `<section class="outline-section">
        <h3 class="outline-title">篇幅规划</h3>
        <div class="outline-grid">
          <div class="outline-field"><span>总时长</span><strong>${escapeHtml(productionNotes.estimated_runtime_minutes || 0)} 分钟</strong></div>
          <div class="outline-field"><span>场均</span><strong>${escapeHtml(runtimePlan.average_scene_minutes || 0)} 分钟</strong></div>
          <div class="outline-field"><span>最短场</span><strong>${escapeHtml(runtimePlan.shortest_scene_minutes || 0)} 分钟</strong></div>
          <div class="outline-field"><span>最长场</span><strong>${escapeHtml(runtimePlan.longest_scene_minutes || 0)} 分钟</strong></div>
        </div>
        ${runtimePlan.pacing ? `<p class="outline-text">${escapeHtml(runtimePlan.pacing)}</p>` : ""}
      </section>`
    : "";
  const revisionTasks = productionNotes.revision_tasks || [];
  const taskSection = revisionTasks.length
    ? `<section class="outline-section">
        <h3 class="outline-title">修订任务</h3>
        <div class="character-list">
          ${revisionTasks.map((task) => `
            <div class="character-card">
              <div class="character-head">
                <strong>${escapeHtml(task.title || task.id || "未命名任务")}</strong>
                <span>${escapeHtml(task.priority || "medium")}</span>
              </div>
              <div class="outline-meta">
                <span class="outline-chip">${escapeHtml(task.category || "general")}</span>
                ${task.status ? `<span class="outline-chip">${escapeHtml(task.status)}</span>` : ""}
                ${(task.target_scene_ids || []).map((sceneId) => `<span class="outline-chip">${escapeHtml(sceneId)}</span>`).join("")}
              </div>
              ${task.reason ? `<p class="outline-text">${escapeHtml(task.reason)}</p>` : ""}
              ${task.action ? `<p class="outline-text">${escapeHtml(task.action)}</p>` : ""}
            </div>`).join("")}
        </div>
      </section>`
    : "";

  outlineOutput.innerHTML = `
    <section class="outline-section">
      <h3 class="outline-title">${escapeHtml(script.title)}</h3>
      <p class="outline-text">${escapeHtml(script.logline)}</p>
      <div class="outline-meta">
        ${(script.themes || []).map((theme) => `<span class="outline-chip">${escapeHtml(theme)}</span>`).join("")}
      </div>
    </section>
    ${coverageSection}
    ${taskSection}
    ${runtimeSection}
    ${characters}
    ${acts || '<div class="outline-empty">暂无幕和场景。</div>'}
  `;
}

function setOutputView(view) {
  const showOutline = view === "outline";
  outlineOutput.hidden = !showOutline;
  yamlFrame.hidden = showOutline;
  outlineViewBtn.classList.toggle("active", showOutline);
  yamlViewBtn.classList.toggle("active", !showOutline);
  outlineViewBtn.setAttribute("aria-selected", String(showOutline));
  yamlViewBtn.setAttribute("aria-selected", String(!showOutline));
}

async function convert() {
  convertBtn.disabled = true;
  yamlOutput.textContent = "转换中...";
  setWarnings([]);
  setEngineMessage("");

  try {
    const response = await fetch("/api/convert", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        title: titleInput.value,
        mode: modeInput.value,
        density: densityInput.value,
        engine: engineInput.value,
        characters: charactersInput.value,
        themes: themesInput.value,
        text: novelInput.value
      })
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "转换失败");

    latestYaml = data.yaml;
    latestScript = data.script;
    yamlOutput.textContent = data.yaml;
    renderOutline(data.script);
    setStats(data.stats);
    setWarnings(data.warnings);
    setQuality(data.quality);
    if (data.meta?.ai?.requested && !data.meta.ai.used) {
      setEngineMessage(data.meta.ai.reason || "AI 增强不可用，已回退到规则引擎。");
    } else if (data.meta?.engine === "ai") {
      setEngineMessage(`AI 增强已启用：${data.meta.ai?.model || "模型"} / ${data.meta.ai?.provider || "provider"}`);
    } else {
      setEngineMessage("当前使用规则引擎，可在配置 OPENAI_API_KEY 后启用 AI 增强。");
    }
  } catch (error) {
    latestYaml = "";
    latestScript = null;
    yamlOutput.textContent = error instanceof Error ? error.message : "转换失败";
    renderOutline(null);
    setStats();
    setQuality();
    setEngineMessage("");
  } finally {
    convertBtn.disabled = false;
  }
}

function inferTitleFromFilename(fileName = "") {
  return fileName.replace(/\.(txt|md|markdown)$/i, "").replace(/[_-]+/g, " ").trim();
}

async function importNovelFile(event) {
  const files = [...(event.target.files || [])].sort((left, right) => left.name.localeCompare(right.name, "zh-CN", { numeric: true }));
  if (!files.length) return;

  const chunks = [];
  for (const file of files) {
    const text = (await file.text()).trim();
    if (!text) continue;
    chunks.push(files.length > 1 ? `# ${inferTitleFromFilename(file.name)}\n${text}` : text);
  }
  novelInput.value = chunks.join("\n\n").trim();
  if (!titleInput.value.trim()) {
    titleInput.value = files.length === 1 ? inferTitleFromFilename(files[0].name) : "多章节小说改编";
  }
  await analyzeInput();
  await convert();
}

async function copyYaml() {
  if (!latestYaml) return;
  await navigator.clipboard.writeText(latestYaml);
  copyBtn.textContent = "✓";
  window.setTimeout(() => {
    copyBtn.textContent = "⧉";
  }, 900);
}

async function downloadYaml() {
  if (!latestYaml || !latestScript) return;
  try {
    downloadBtn.disabled = true;
    await downloadExport(exportFormatInput.value);
  } catch (error) {
    setWarnings([error instanceof Error ? error.message : "导出失败"]);
  } finally {
    downloadBtn.disabled = false;
  }
}

async function downloadExport(format) {
  const response = await fetch("/api/export", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      format,
      script: latestScript,
      yaml: latestYaml
    })
  });
  const data = await response.json();
  if (!data.ok) throw new Error(data.error || "导出失败");

  const blob = new Blob([data.content], { type: data.mime_type || "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = data.filename || `${titleInput.value || "screenplay"}.screenplay.yaml`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function clearWorkspace() {
  latestYaml = "";
  latestScript = null;
  titleInput.value = "";
  charactersInput.value = "";
  themesInput.value = "";
  novelInput.value = "";
  yamlOutput.textContent = "等待转换...";
  renderOutline(null);
  fileInput.value = "";
  exportFormatInput.value = "yaml";
  engineInput.value = "rules";
  setStats();
  setWarnings([]);
  setQuality();
  setEngineMessage("");
  setAnalysis();
}

loadSampleBtn.addEventListener("click", () => {
  titleInput.value = "雾港来信";
  charactersInput.value = "林澈，沈雾，周栩";
  themesInput.value = "信任，真相，成长";
  novelInput.value = sampleNovel;
  convert();
});

convertBtn.addEventListener("click", convert);
fileInput.addEventListener("change", importNovelFile);
cleanupBtn.addEventListener("click", cleanupInput);
analyzeBtn.addEventListener("click", analyzeInput);
copyBtn.addEventListener("click", copyYaml);
downloadBtn.addEventListener("click", downloadYaml);
clearBtn.addEventListener("click", clearWorkspace);
yamlViewBtn.addEventListener("click", () => setOutputView("yaml"));
outlineViewBtn.addEventListener("click", () => setOutputView("outline"));

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const data = await response.json();
    if (data.ok) appConfig = data;
  } catch {
    appConfig = { ai: { enabled: false, model: "", provider: "" } };
  }

  const aiOption = engineInput.querySelector('option[value="ai"]');
  if (appConfig.ai.enabled) {
    aiOption.textContent = `AI 增强 (${appConfig.ai.model})`;
    aiOption.disabled = false;
  } else {
    aiOption.textContent = "AI 增强 (需配置)";
    aiOption.disabled = false;
  }
}

setStats();
setQuality();
setAnalysis();
renderOutline(null);
setOutputView("yaml");
loadConfig();
