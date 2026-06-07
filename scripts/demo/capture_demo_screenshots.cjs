const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const rootDir = path.resolve(__dirname, "../..");
const outputDir = path.join(rootDir, "_demo_work", "screenshots");

function browserExecutablePath() {
  const candidates = [
    process.env.PLAYWRIGHT_BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

async function waitForStat(page, selector, value) {
  await page.waitForFunction(
    ([targetSelector, targetValue]) => document.querySelector(targetSelector)?.textContent?.trim() === targetValue,
    [selector, value],
    { timeout: 10000 }
  );
}

async function screenshot(page, fileName) {
  await page.screenshot({ path: path.join(outputDir, fileName), fullPage: false });
}

(async () => {
  ensureDir(outputDir);
  const executablePath = browserExecutablePath();
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1
  });

  await page.goto("http://localhost:4173", { waitUntil: "networkidle" });
  await screenshot(page, "01-home.png");

  await page.click("#loadSampleBtn");
  await waitForStat(page, "#chapterStat", "3");
  await screenshot(page, "02-sample.png");

  await page.click("#analyzeBtn");
  await page.waitForSelector("#analysisSummary strong");
  await screenshot(page, "03-analysis.png");

  await page.click("#yamlViewBtn");
  await page.waitForFunction(() => document.querySelector("#yamlOutput")?.textContent?.includes("script:"));
  await screenshot(page, "04-yaml.png");

  await page.click("#outlineViewBtn");
  await page.waitForFunction(() => document.querySelector("#outlineOutput")?.textContent?.includes("来源覆盖"));
  await screenshot(page, "05-outline.png");

  await page.selectOption("#exportFormatInput", "outline_md");
  await screenshot(page, "06-export.png");

  await browser.close();
  console.log(`Captured demo screenshots in ${outputDir}`);
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
