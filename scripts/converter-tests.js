import assert from "node:assert/strict";
import { convertNovelToScreenplay, splitChapters } from "../src/converter.js";
import { convertNovelToScreenplayOptionalAI, getPublicAIConfig } from "../src/ai-adapter.js";

const cases = [
  {
    name: "Chinese chapter markers",
    text: `第一章 风起
林青说：“走。”

第二章 入城
夜晚，林青到了城门。

第三章 选择
黎明，林青决定留下。`,
    expectedChapters: 3
  },
  {
    name: "English Chapter markers",
    text: `Chapter 1 The Call
Mina said, "I have to go."

Chapter 2 The Door
At night, the old door opened.

Chapter 3 The List
Mina found the list before dawn.`,
    expectedChapters: 3
  },
  {
    name: "Numbered markdown-like markers",
    text: `1. 雨夜
阿禾说：“别回头。”

2. 地下室
阿禾发现墙上的地图。

3. 出口
清晨，阿禾推开门。`,
    expectedChapters: 3
  }
];

for (const item of cases) {
  const chapters = splitChapters(item.text);
  assert.equal(chapters.length, item.expectedChapters, item.name);

  const result = convertNovelToScreenplay({
    title: item.name,
    text: item.text,
    characters: "林青，Mina，阿禾"
  });

  assert.equal(result.ok, true, item.name);
  assert.equal(result.stats.chapters, item.expectedChapters, item.name);
  assert.ok(result.stats.scenes >= item.expectedChapters, item.name);
  assert.ok(result.yaml.includes("script:"), item.name);
  assert.ok(result.yaml.includes("acts:"), item.name);
  assert.ok(result.quality.score > 0, item.name);
  assert.equal(result.quality.metrics.chapter_count, item.expectedChapters, item.name);
}

const shortResult = convertNovelToScreenplay({
  title: "Short input",
  text: `第一章 只有一章
主角说：“还不够。”`
});

assert.equal(shortResult.stats.chapters, 1);
assert.ok(shortResult.warnings.some((warning) => warning.includes("少于 3")));
assert.equal(shortResult.quality.status, "needs_fix");

const fallbackResult = await convertNovelToScreenplayOptionalAI(
  {
    title: "AI fallback",
    engine: "ai",
    text: cases[0].text,
    characters: "林青"
  },
  {
    env: {}
  }
);

assert.equal(fallbackResult.ok, true);
assert.equal(fallbackResult.meta.engine, "rules");
assert.equal(fallbackResult.meta.ai.requested, true);
assert.equal(fallbackResult.meta.ai.used, false);

const publicConfigWithoutKey = getPublicAIConfig({});
assert.equal(publicConfigWithoutKey.enabled, false);
assert.equal(publicConfigWithoutKey.model, "");

const publicConfigWithKey = getPublicAIConfig({
  OPENAI_API_KEY: "test-key",
  OPENAI_MODEL: "test-model",
  OPENAI_BASE_URL: "https://example.com/v1"
});
assert.equal(publicConfigWithKey.enabled, true);
assert.equal(publicConfigWithKey.model, "test-model");
assert.equal(publicConfigWithKey.provider, "example.com");

console.log("Converter tests passed.");
