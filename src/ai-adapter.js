import { convertNovelToScreenplay, splitChapters, buildConversionResult } from "./converter.js";
import { screenplaySchema } from "./schema.js";

const DEFAULT_MODEL = "gpt-4.1-mini";
const DEFAULT_BASE_URL = "https://api.openai.com/v1";
const DEFAULT_INPUT_CHAR_LIMIT = 24000;

function getAIConfig(env = process.env) {
  const apiKey = env.OPENAI_API_KEY || env.AI_API_KEY || "";
  return {
    enabled: Boolean(apiKey),
    apiKey,
    baseUrl: (env.OPENAI_BASE_URL || env.AI_BASE_URL || DEFAULT_BASE_URL).replace(/\/+$/, ""),
    model: env.OPENAI_MODEL || env.AI_MODEL || DEFAULT_MODEL,
    inputCharLimit: Number(env.AI_INPUT_CHAR_LIMIT || DEFAULT_INPUT_CHAR_LIMIT)
  };
}

export function getPublicAIConfig(env = process.env) {
  const config = getAIConfig(env);
  return {
    enabled: config.enabled,
    model: config.enabled ? config.model : "",
    provider: config.enabled ? new URL(config.baseUrl).hostname : ""
  };
}

function compactNovelText(text, limit) {
  const normalized = String(text || "").trim();
  if (normalized.length <= limit) return normalized;
  const half = Math.floor(limit / 2);
  return `${normalized.slice(0, half)}\n\n[...中间内容已截断，规则引擎初稿仍保留完整结构...]\n\n${normalized.slice(-half)}`;
}

function buildPrompt({ payload, ruleScript, rawText, config }) {
  return [
    {
      role: "system",
      content: [
        "你是专业的小说改编剧本助手。",
        "任务：在不改变 YAML Schema 的前提下，增强规则引擎生成的剧本结构。",
        "只返回 JSON，格式必须是 {\"script\": {...}}，不要 Markdown，不要解释。",
        "重点：把小说叙述转成可表演动作、对白、场景冲突和转折；保留 source_chapter 追溯信息。",
        "不要生成超出原文事实太远的新剧情，可以补充合理的剧作表达。"
      ].join("\n")
    },
    {
      role: "user",
      content: JSON.stringify(
        {
          requested_title: payload.title || "",
          adaptation_mode: payload.mode || "drama",
          density: payload.density || "balanced",
          user_characters: payload.characters || "",
          user_themes: payload.themes || "",
          schema: screenplaySchema,
          rule_engine_draft: ruleScript,
          novel_text_for_reference: compactNovelText(rawText, config.inputCharLimit)
        },
        null,
        2
      )
    }
  ];
}

function extractJsonObject(text) {
  const trimmed = String(text || "").trim();
  if (!trimmed) throw new Error("AI 返回为空。");
  if (trimmed.startsWith("{")) return JSON.parse(trimmed);

  const fenced = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fenced) return JSON.parse(fenced[1]);

  const start = trimmed.indexOf("{");
  const end = trimmed.lastIndexOf("}");
  if (start >= 0 && end > start) {
    return JSON.parse(trimmed.slice(start, end + 1));
  }

  throw new Error("AI 返回不是 JSON。");
}

function ensureArray(value, fallback = []) {
  return Array.isArray(value) ? value : fallback;
}

function normalizeAIScript(candidate, fallback) {
  const script = candidate && typeof candidate === "object" ? candidate : {};
  const source = script.source && typeof script.source === "object" ? script.source : {};
  const productionNotes = script.production_notes && typeof script.production_notes === "object" ? script.production_notes : {};

  return {
    ...fallback,
    ...script,
    schema_version: fallback.schema_version,
    title: script.title || fallback.title,
    source: {
      ...fallback.source,
      ...source,
      type: "novel",
      chapter_count: fallback.source.chapter_count,
      input_language: fallback.source.input_language
    },
    themes: ensureArray(script.themes, fallback.themes),
    characters: ensureArray(script.characters, fallback.characters),
    acts: ensureArray(script.acts, fallback.acts),
    production_notes: {
      ...fallback.production_notes,
      ...productionNotes,
      adaptation_warnings: ensureArray(productionNotes.adaptation_warnings, fallback.production_notes.adaptation_warnings),
      revision_suggestions: ensureArray(productionNotes.revision_suggestions, fallback.production_notes.revision_suggestions)
    }
  };
}

async function callOpenAICompatibleChat({ config, messages }) {
  const response = await fetch(`${config.baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.apiKey}`
    },
    body: JSON.stringify({
      model: config.model,
      messages,
      temperature: 0.4,
      response_format: { type: "json_object" }
    })
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`AI 请求失败：${response.status} ${detail.slice(0, 240)}`);
  }

  const body = await response.json();
  const content = body.choices?.[0]?.message?.content;
  return extractJsonObject(content);
}

export async function convertNovelToScreenplayOptionalAI(payload = {}, options = {}) {
  const ruleResult = convertNovelToScreenplay(payload);
  const requestedAI = payload.engine === "ai";
  const config = getAIConfig(options.env);

  if (!requestedAI) {
    return ruleResult;
  }

  if (!config.enabled) {
    return {
      ...ruleResult,
      meta: {
        ...ruleResult.meta,
        engine: "rules",
        ai: {
          requested: true,
          used: false,
          reason: "未配置 OPENAI_API_KEY，已自动回退到规则引擎。"
        }
      }
    };
  }

  try {
    const messages = buildPrompt({
      payload,
      ruleScript: ruleResult.script,
      rawText: payload.text || "",
      config
    });
    const aiDraft = await callOpenAICompatibleChat({ config, messages });
    const enhancedScript = normalizeAIScript(aiDraft.script, ruleResult.script);
    const chapters = splitChapters(payload.text || "");
    const enhanced = buildConversionResult({
      script: enhancedScript,
      chapters,
      rawText: payload.text || "",
      meta: {
        engine: "ai",
        ai: {
          requested: true,
          used: true,
          model: config.model,
          provider: new URL(config.baseUrl).hostname
        }
      }
    });

    return enhanced;
  } catch (error) {
    return {
      ...ruleResult,
      meta: {
        ...ruleResult.meta,
        engine: "rules",
        ai: {
          requested: true,
          used: false,
          reason: error instanceof Error ? error.message : "AI 增强失败，已自动回退到规则引擎。"
        }
      }
    };
  }
}
