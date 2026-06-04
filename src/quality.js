function textLength(text = "") {
  return Array.from(String(text).replace(/\s+/g, "")).length;
}

function makeCheck(id, label, passed, severity, message) {
  return {
    id,
    label,
    passed,
    severity,
    message
  };
}

export function validateScreenplayStructure(script) {
  const checks = [];

  checks.push(makeCheck(
    "schema_version",
    "Schema 版本",
    typeof script.schema_version === "string" && script.schema_version.length > 0,
    "error",
    "输出应包含 schema_version，方便后续升级和校验。"
  ));

  checks.push(makeCheck(
    "minimum_chapters",
    "章节数量",
    Number(script.source?.chapter_count || 0) >= 3,
    "error",
    "题目要求输入 3 个章节以上的小说文本。"
  ));

  checks.push(makeCheck(
    "characters",
    "角色列表",
    Array.isArray(script.characters) && script.characters.length > 0,
    "warning",
    "建议提供或识别至少 1 个主要角色。"
  ));

  checks.push(makeCheck(
    "acts",
    "幕结构",
    Array.isArray(script.acts) && script.acts.length > 0,
    "error",
    "输出应包含 acts，作为剧本的章节/幕骨架。"
  ));

  const scenes = script.acts?.flatMap((act) => act.scenes || []) || [];
  checks.push(makeCheck(
    "scenes",
    "场景结构",
    scenes.length > 0,
    "error",
    "输出应包含 scenes，作为剧本的核心编辑单位。"
  ));

  checks.push(makeCheck(
    "beats",
    "场景节拍",
    scenes.some((scene) => Array.isArray(scene.beats) && scene.beats.length > 0),
    "error",
    "每个场景应尽量拆出动作、对白或旁白节拍。"
  ));

  checks.push(makeCheck(
    "traceability",
    "来源追溯",
    scenes.every((scene) => typeof scene.source_chapter === "string" && scene.source_chapter.length > 0),
    "warning",
    "每个场景应保留 source_chapter，便于回到原小说核对。"
  ));

  return checks;
}

export function buildQualityReport({ chapters, script, rawText }) {
  const scenes = script.acts.flatMap((act) => act.scenes);
  const beats = scenes.flatMap((scene) => scene.beats);
  const dialogueBeats = beats.filter((beat) => beat.type === "dialogue");
  const chapterLengths = chapters.map((chapter) => textLength(chapter.text));
  const totalLength = textLength(rawText);
  const structureChecks = validateScreenplayStructure(script);
  const checks = [...structureChecks];

  const hasEnoughContent = totalLength >= 300;
  checks.push(makeCheck(
    "input_volume",
    "输入体量",
    hasEnoughContent,
    "warning",
    "输入文本较短时，生成结果更像提纲；真实测试建议使用完整章节。"
  ));

  checks.push(makeCheck(
    "dialogue_balance",
    "对白覆盖",
    dialogueBeats.length > 0,
    "info",
    "未识别到对白时，工具会先生成动作/旁白节拍，后续可人工补对白。"
  ));

  checks.push(makeCheck(
    "scene_density",
    "场景密度",
    scenes.length >= chapters.length,
    "info",
    "通常每章至少应生成 1 个场景；长章节可使用“细分”密度。"
  ));

  const failedCritical = checks.filter((check) => !check.passed && check.severity === "error").length;
  const failedWarning = checks.filter((check) => !check.passed && check.severity === "warning").length;
  const failedInfo = checks.filter((check) => !check.passed && check.severity === "info").length;
  const score = Math.max(0, 100 - failedCritical * 28 - failedWarning * 12 - failedInfo * 6);

  const suggestions = [];
  if (script.source.chapter_count < 3) suggestions.push("补充到至少 3 个章节后再提交比赛测试。");
  if (!script.characters.length) suggestions.push("在主要角色输入框填写主角和关键配角，提高对白归属准确率。");
  if (totalLength < 300) suggestions.push("使用更完整的章节文本，避免只输入梗概。");
  if (!dialogueBeats.length) suggestions.push("原文对白较少时，可在生成后人工添加角色对白。");
  if (scenes.length < chapters.length) suggestions.push("把输出密度切换为“细分”，让长章节拆出更多场景。");

  return {
    score,
    status: failedCritical ? "needs_fix" : failedWarning ? "review" : "ready",
    metrics: {
      input_chars: totalLength,
      chapter_count: chapters.length,
      average_chapter_chars: chapterLengths.length ? Math.round(chapterLengths.reduce((sum, len) => sum + len, 0) / chapterLengths.length) : 0,
      scene_count: scenes.length,
      beat_count: beats.length,
      dialogue_beat_count: dialogueBeats.length
    },
    checks,
    suggestions
  };
}
