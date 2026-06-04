import { SCRIPT_SCHEMA_VERSION } from "./schema.js";
import { buildQualityReport } from "./quality.js";

const CHAPTER_PATTERN = /(?:^|\n)\s*((?:#{1,6}\s*)?(?:(?:第\s*[零〇一二三四五六七八九十百千万\d]+\s*[章节回幕卷部])|(?:[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+)|(?:卷\s*[零〇一二三四五六七八九十百千万\d]+)|(?:\d{1,4}\s*[.、]\s*(?:章|节|回|幕)?\s*[^\n]{0,40}))[^\n]*)/g;
const DIALOGUE_PATTERN = /[“"]([^”"]{2,})[”"]/g;
const SPEAKER_PATTERN = /([\u4e00-\u9fa5A-Za-z0-9_·]{1,8})\s*(?:说|问|喊|叫|道|低声说|笑道|答道|喃喃|怒道|提醒|解释)/;
const LOCATION_PATTERN = /(客厅|书房|卧室|医院|学校|街道|巷子|办公室|咖啡馆|餐厅|车站|机场|码头|城门|宫殿|战场|森林|山洞|屋内|门外|天台|走廊|庭院|村口|河边|窗前)/;
const TIME_PATTERN = /(清晨|早晨|上午|中午|午后|下午|傍晚|黄昏|夜晚|深夜|黎明|雨夜|雪夜)/;
const EMOTION_PATTERN = /(愤怒|惊讶|沉默|犹豫|恐惧|紧张|温柔|冷静|焦急|悲伤|欣喜|坚定|疲惫|慌乱|压抑|释然)/;
const NON_NAME_PHRASES = new Set([
  "压低声音",
  "沉默片刻",
  "冷静地",
  "愤怒地",
  "紧张地",
  "低声",
  "沙哑",
  "熟悉",
  "有人",
  "有人低声",
  "两人",
  "三人",
  "门外",
  "黑暗里",
  "录音里"
]);

function normalizeText(text = "") {
  return String(text)
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/\u3000/g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .trim();
}

function cleanChapterTitle(title) {
  return title.replace(/^#{1,6}\s*/, "").replace(/\s+/g, " ").trim();
}

export function splitChapters(text) {
  const normalized = normalizeText(text);
  const matches = [...normalized.matchAll(CHAPTER_PATTERN)];

  if (matches.length === 0) {
    return [
      {
        id: "chapter_01",
        title: "未识别章节",
        text: normalized
      }
    ];
  }

  return matches.map((match, index) => {
    const start = match.index + match[0].indexOf(match[1]);
    const next = matches[index + 1];
    const end = next ? next.index + next[0].indexOf(next[1]) : normalized.length;
    const chunk = normalized.slice(start, end).trim();
    const [titleLine = `章节 ${index + 1}`, ...bodyLines] = chunk.split("\n");

    return {
      id: `chapter_${String(index + 1).padStart(2, "0")}`,
      title: cleanChapterTitle(titleLine),
      text: bodyLines.join("\n").trim()
    };
  });
}

export function splitParagraphs(text) {
  return normalizeText(text)
    .split(/\n+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function sentenceSplit(text) {
  return normalizeText(text)
    .split(/(?<=[。！？!?；;])\s*/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function parseNameList(value = "") {
  return normalizeText(value)
    .split(/[,，\n、]/)
    .map((name) => name.trim())
    .filter(Boolean);
}

function isLikelyName(value) {
  const clean = value.trim();
  return (
    clean &&
    clean.length <= 8 &&
    !NON_NAME_PHRASES.has(clean) &&
    !/^\d+$/.test(clean) &&
    !/(有人|声音|低声|压低|片刻|黑暗|门外|录音|电话|信纸|海风|灯光|雨水|墙上|档案|父亲|熟悉|沙哑)/.test(clean) &&
    !/[地的]$/.test(clean)
  );
}

function extractSpeaker(paragraph, knownNames = []) {
  const beforeQuote = paragraph.split(/[“"]/)[0] || paragraph;
  const knownHits = knownNames
    .map((name) => ({ name, index: beforeQuote.lastIndexOf(name) }))
    .filter((item) => item.index >= 0)
    .sort((left, right) => right.index - left.index);

  if (knownHits.length) {
    return knownHits[0].name;
  }

  const openingSubject = beforeQuote.match(/^([\u4e00-\u9fa5A-Za-z0-9_·]{2,6})(?:从|站|望|看|接|喊|问|说|道|答|笑|走|跑|转|拿|发现|解释|提醒|决定|翻|把|没有|迅速|突然)/);
  if (openingSubject && isLikelyName(openingSubject[1])) {
    return openingSubject[1];
  }

  const match = beforeQuote.match(SPEAKER_PATTERN) || paragraph.match(SPEAKER_PATTERN);
  if (match && isLikelyName(match[1])) {
    return match[1];
  }

  return "";
}

function extractCharacters(chapters, userCharacters = "") {
  const candidates = new Map();
  const add = (name, source) => {
    const clean = name.trim();
    if (!isLikelyName(clean)) return;
    candidates.set(clean, candidates.get(clean) || source);
  };

  const knownNames = parseNameList(userCharacters);
  knownNames.forEach((name) => add(name, "用户设定"));

  chapters.forEach((chapter) => {
    splitParagraphs(chapter.text).forEach((paragraph) => {
      const speaker = extractSpeaker(paragraph, knownNames);
      if (speaker) add(speaker, chapter.title);
    });
  });

  return [...candidates.entries()].slice(0, 12).map(([name, source], index) => ({
    id: `char_${String(index + 1).padStart(2, "0")}`,
    name,
    role: index === 0 ? "主角/核心视角" : "角色",
    traits: [],
    first_appearance: source
  }));
}

function pickMatch(text, pattern, fallback) {
  const match = text.match(pattern);
  return match ? match[1] : fallback;
}

function inferMood(text) {
  const emotion = pickMatch(text, EMOTION_PATTERN, "");
  if (emotion) return emotion;
  if (/追|逃|爆炸|冲|杀|危险|尖叫|枪|刀/.test(text)) return "紧张";
  if (/回忆|想起|沉默|雨|夜|离开/.test(text)) return "压抑";
  if (/笑|阳光|拥抱|重逢|庆祝/.test(text)) return "温暖";
  return "克制";
}

function summarize(text, maxLength = 92) {
  const first = sentenceSplit(text)[0] || normalizeText(text);
  if (first.length <= maxLength) return first;
  return `${first.slice(0, maxLength - 1)}…`;
}

function createBeats(paragraphs, sceneId, knownNames = []) {
  const beats = [];

  paragraphs.forEach((paragraph) => {
    const dialogues = [...paragraph.matchAll(DIALOGUE_PATTERN)];
    if (dialogues.length) {
      const speaker = extractSpeaker(paragraph, knownNames);
      const actionText = paragraph.replace(DIALOGUE_PATTERN, "").trim();
      if (actionText) {
        beats.push({
          id: `${sceneId}_beat_${String(beats.length + 1).padStart(2, "0")}`,
          type: "action",
          text: summarize(actionText, 120),
          camera: "中景"
        });
      }

      dialogues.forEach((dialogue) => {
        beats.push({
          id: `${sceneId}_beat_${String(beats.length + 1).padStart(2, "0")}`,
          type: "dialogue",
          speaker: speaker || "待定角色",
          text: dialogue[1].trim(),
          emotion: pickMatch(paragraph, EMOTION_PATTERN, "待细化")
        });
      });
      return;
    }

    sentenceSplit(paragraph).slice(0, 3).forEach((sentence) => {
      beats.push({
        id: `${sceneId}_beat_${String(beats.length + 1).padStart(2, "0")}`,
        type: /回忆|心想|想到|意识到/.test(sentence) ? "narration" : "action",
        text: summarize(sentence, 120),
        camera: /看见|望向|盯着|发现/.test(sentence) ? "特写" : "中景"
      });
    });
  });

  return beats.slice(0, 12);
}

function chunkParagraphs(paragraphs, chunkSize) {
  const chunks = [];
  for (let index = 0; index < paragraphs.length; index += chunkSize) {
    chunks.push(paragraphs.slice(index, index + chunkSize));
  }
  return chunks.length ? chunks : [[]];
}

function chapterToScenes(chapter, chapterIndex, density, knownNames = []) {
  const paragraphs = splitParagraphs(chapter.text);
  const chunkSize = density === "detailed" ? 4 : density === "compact" ? 8 : 6;
  const groups = chunkParagraphs(paragraphs, chunkSize);

  return groups.map((group, sceneIndex) => {
    const sceneText = group.join("\n");
    const sceneId = `scene_${String(chapterIndex + 1).padStart(2, "0")}_${String(sceneIndex + 1).padStart(2, "0")}`;
    const beats = createBeats(group, sceneId, knownNames);

    return {
      id: sceneId,
      title: `${chapter.title} · 场景 ${sceneIndex + 1}`,
      source_chapter: chapter.title,
      location: pickMatch(sceneText, LOCATION_PATTERN, "待定地点"),
      time: pickMatch(sceneText, TIME_PATTERN, "待定时间"),
      mood: inferMood(sceneText),
      summary: summarize(sceneText || chapter.title),
      beats,
      conflict: summarize(sceneText.match(/[^。！？!?]*(?:冲突|争执|危险|秘密|误会|选择|背叛|阻止|追问)[^。！？!?]*/)?.[0] || "本场冲突需要二次打磨。", 80),
      turning_point: summarize(sceneText.match(/[^。！？!?]*(?:突然|终于|决定|发现|转身|离开|出现|揭开)[^。！？!?]*/)?.[0] || "转折点待编剧确认。", 80),
      props: [],
      notes: ["由小说段落自动拆分，建议人工校准场景边界。"]
    };
  });
}

function buildActs(chapters, density, knownNames = []) {
  return chapters.map((chapter, index) => ({
    id: `act_${String(index + 1).padStart(2, "0")}`,
    title: chapter.title,
    source_chapters: [chapter.title],
    purpose: index === 0 ? "建立人物、世界观与核心矛盾" : index === chapters.length - 1 ? "推进高潮并留下后续打磨空间" : "升级冲突并推动人物选择",
    scenes: chapterToScenes(chapter, index, density, knownNames)
  }));
}

function yamlScalar(value) {
  if (value === null || value === undefined) return "''";
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  const text = String(value);
  if (!text) return "''";
  if (/^[A-Za-z0-9_\-./: ]+$/.test(text) && !/^(true|false|null|yes|no)$/i.test(text)) {
    return text;
  }
  return JSON.stringify(text);
}

export function toYaml(value, indent = 0) {
  const pad = " ".repeat(indent);
  if (Array.isArray(value)) {
    if (!value.length) return `${pad}[]`;
    return value
      .map((item) => {
        if (item && typeof item === "object" && !Array.isArray(item)) {
          const entries = Object.entries(item);
          if (!entries.length) return `${pad}- {}`;
          const [firstKey, firstValue] = entries[0];
          const rest = entries.slice(1);
          const firstLine = `${pad}- ${firstKey}: ${firstValue && typeof firstValue === "object" ? "\n" + toYaml(firstValue, indent + 4) : yamlScalar(firstValue)}`;
          const restLines = rest
            .map(([key, child]) => `${pad}  ${key}: ${child && typeof child === "object" ? "\n" + toYaml(child, indent + 4) : yamlScalar(child)}`)
            .join("\n");
          return restLines ? `${firstLine}\n${restLines}` : firstLine;
        }
        return `${pad}- ${item && typeof item === "object" ? "\n" + toYaml(item, indent + 2) : yamlScalar(item)}`;
      })
      .join("\n");
  }

  if (value && typeof value === "object") {
    return Object.entries(value)
      .map(([key, child]) => `${pad}${key}: ${child && typeof child === "object" ? "\n" + toYaml(child, indent + 2) : yamlScalar(child)}`)
      .join("\n");
  }

  return `${pad}${yamlScalar(value)}`;
}

function validate(script) {
  const warnings = [];
  const chapters = script.source.chapter_count;
  if (chapters < 3) {
    warnings.push("输入章节少于 3 个，不满足比赛题目要求。");
  }
  if (!script.acts.length) {
    warnings.push("未生成幕/章节结构。");
  }
  if (!script.acts.some((act) => act.scenes.length)) {
    warnings.push("未生成场景。");
  }
  if (!script.characters.length) {
    warnings.push("未识别到角色，建议在角色输入框中补充主要人物。");
  }
  return warnings;
}

export function buildConversionResult({ script, chapters, rawText, meta = {} }) {
  const warnings = validate(script);
  script.production_notes.adaptation_warnings = warnings;
  const quality = buildQualityReport({ chapters, script, rawText });

  return {
    ok: true,
    yaml: toYaml({ script }),
    script,
    quality,
    warnings,
    stats: {
      chapters: script.source.chapter_count,
      characters: script.characters.length,
      scenes: script.acts.reduce((total, act) => total + act.scenes.length, 0),
      beats: script.acts.reduce((total, act) => total + act.scenes.reduce((sceneTotal, scene) => sceneTotal + scene.beats.length, 0), 0)
    },
    meta
  };
}

export function convertNovelToScreenplay(payload = {}) {
  const title = normalizeText(payload.title) || "未命名小说改编";
  const text = normalizeText(payload.text);
  const density = payload.density || "balanced";

  if (!text) {
    throw new Error("请先输入小说文本。");
  }

  const chapters = splitChapters(text);
  const knownNames = parseNameList(payload.characters || "");
  const characters = extractCharacters(chapters, payload.characters || "");
  const acts = buildActs(chapters, density, knownNames);
  const script = {
    schema_version: SCRIPT_SCHEMA_VERSION,
    title,
    source: {
      type: "novel",
      chapter_count: chapters.length,
      input_language: "zh-CN",
      adaptation_mode: payload.mode || "drama"
    },
    logline: summarize(chapters.map((chapter) => chapter.text).join("\n"), 110),
    themes: normalizeText(payload.themes)
      ? normalizeText(payload.themes).split(/[,，、\n]/).map((item) => item.trim()).filter(Boolean)
      : ["人物选择", "冲突升级", "情感转折"],
    characters,
    acts,
    production_notes: {
      estimated_runtime_minutes: Math.max(8, Math.round(chapters.length * (density === "detailed" ? 9 : density === "compact" ? 4 : 6))),
      adaptation_warnings: validate({ source: { chapter_count: chapters.length }, acts, characters }),
      revision_suggestions: [
        "复核角色名与对白归属。",
        "把小说心理描写改写成可表演动作。",
        "为每场补充明确的场景目标、阻碍与转折。"
      ]
    }
  };

  return buildConversionResult({
    script,
    chapters,
    rawText: text,
    meta: {
      engine: "rules"
    }
  });
}
