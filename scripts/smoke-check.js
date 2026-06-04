import { convertNovelToScreenplay } from "../src/converter.js";
import { readFileSync } from "node:fs";

const sample = readFileSync("examples/three-chapter-novel.txt", "utf8");

const result = convertNovelToScreenplay({
  title: "烟雾测试",
  text: sample,
  characters: "林澈，沈雾，周栩",
  themes: "真相，选择"
});

const requiredFragments = [
  "schema_version: 1.0.0",
  "chapter_count: 3",
  "acts:",
  "scenes:",
  "beats:",
  "characters:"
];

const missing = requiredFragments.filter((fragment) => !result.yaml.includes(fragment));

if (missing.length) {
  console.error(`Smoke check failed. Missing: ${missing.join(", ")}`);
  process.exit(1);
}

if (result.stats.chapters < 3 || result.stats.scenes < 3 || result.stats.beats < 3) {
  console.error("Smoke check failed. Generated structure is too small.");
  process.exit(1);
}

console.log("Smoke check passed.");
console.log(JSON.stringify(result.stats, null, 2));
console.log(JSON.stringify(result.meta, null, 2));
