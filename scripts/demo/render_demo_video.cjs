const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

const rootDir = path.resolve(__dirname, "../..");
const workDir = path.join(rootDir, "_demo_work");
const screenshotDir = path.join(workDir, "screenshots");
const timelinePath = path.join(workDir, "timeline.json");
const audioPath = path.join(workDir, "demo-narration.wav");
const outPath = path.join(rootDir, "docs", "demo", "ai-novel-to-screenplay-demo.webm");

function browserExecutablePath() {
  const candidates = [
    process.env.PLAYWRIGHT_BROWSER_EXECUTABLE,
    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
  ].filter(Boolean);
  return candidates.find((candidate) => fs.existsSync(candidate));
}

function dataUrl(filePath, mimeType) {
  return `data:${mimeType};base64,${fs.readFileSync(filePath).toString("base64")}`;
}

function mimeFromName(fileName) {
  if (fileName.endsWith(".png")) return "image/png";
  if (fileName.endsWith(".jpg") || fileName.endsWith(".jpeg")) return "image/jpeg";
  return "application/octet-stream";
}

(async () => {
  const timeline = JSON.parse(fs.readFileSync(timelinePath, "utf8"));
  const images = {};
  for (const segment of timeline) {
    const imagePath = path.join(screenshotDir, segment.image);
    images[segment.image] = dataUrl(imagePath, mimeFromName(segment.image));
  }
  const audioDataUrl = dataUrl(audioPath, "audio/wav");

  const executablePath = browserExecutablePath();
  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: ["--autoplay-policy=no-user-gesture-required"]
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  await page.exposeFunction("saveVideoBytes", async (items, mimeType) => {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, Buffer.from(items));
    fs.writeFileSync(path.join(path.dirname(outPath), "demo-video-mime.txt"), `${mimeType}\n`);
  });

  await page.setContent("<!doctype html><html><body style='margin:0;background:#0b1020'><canvas id='canvas' width='1280' height='720'></canvas></body></html>");
  const result = await page.evaluate(async ({ timeline, images, audioDataUrl }) => {
    const canvas = document.querySelector("#canvas");
    const ctx = canvas.getContext("2d");
    const width = canvas.width;
    const height = canvas.height;

    function loadImage(src) {
      return new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = reject;
        image.src = src;
      });
    }

    function wrapText(text, maxWidth, maxLines = 2) {
      const chars = [...text];
      const lines = [];
      let line = "";
      for (const char of chars) {
        const test = line + char;
        if (ctx.measureText(test).width > maxWidth && line) {
          lines.push(line);
          line = char;
          if (lines.length >= maxLines - 1) break;
        } else {
          line = test;
        }
      }
      if (line && lines.length < maxLines) lines.push(line);
      return lines;
    }

    function activeSegment(time) {
      return timeline.find((item) => time >= item.start && time <= item.end)
        || timeline.find((item) => time < item.start)
        || timeline[timeline.length - 1];
    }

    const loadedImages = {};
    for (const [name, src] of Object.entries(images)) {
      loadedImages[name] = await loadImage(src);
    }

    const audioContext = new AudioContext();
    const audioBuffer = await fetch(audioDataUrl).then((response) => response.arrayBuffer()).then((buffer) => audioContext.decodeAudioData(buffer));
    const destination = audioContext.createMediaStreamDestination();
    const source = audioContext.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(destination);

    const canvasStream = canvas.captureStream(18);
    const stream = new MediaStream([
      ...canvasStream.getVideoTracks(),
      ...destination.stream.getAudioTracks()
    ]);

    const candidates = [
      "video/webm;codecs=vp9,opus",
      "video/webm;codecs=vp8,opus",
      "video/webm"
    ];
    const mimeType = candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) || "";
    const chunks = [];
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType, videoBitsPerSecond: 1_600_000 } : { videoBitsPerSecond: 1_600_000 });
    recorder.ondataavailable = (event) => {
      if (event.data && event.data.size) chunks.push(event.data);
    };

    const totalDuration = timeline[timeline.length - 1].end + 0.8;
    const startAt = performance.now();
    let finished = false;

    function draw() {
      const time = (performance.now() - startAt) / 1000;
      const segment = activeSegment(time);
      const image = loadedImages[segment.image];

      ctx.fillStyle = "#0b1020";
      ctx.fillRect(0, 0, width, height);
      ctx.drawImage(image, 0, 0, width, height);

      const gradient = ctx.createLinearGradient(0, 0, 0, 150);
      gradient.addColorStop(0, "rgba(2, 6, 23, 0.76)");
      gradient.addColorStop(1, "rgba(2, 6, 23, 0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, width, 150);

      ctx.fillStyle = "rgba(14, 165, 233, 0.94)";
      ctx.fillRect(32, 26, 332, 40);
      ctx.fillStyle = "#ffffff";
      ctx.font = "600 22px Microsoft YaHei, sans-serif";
      ctx.fillText("AI 小说转剧本工具 Demo", 50, 53);

      ctx.fillStyle = "rgba(2, 6, 23, 0.82)";
      ctx.fillRect(0, height - 126, width, 126);
      ctx.fillStyle = "#f8fafc";
      ctx.font = "600 30px Microsoft YaHei, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      const lines = wrapText(segment.text, width - 140, 2);
      const firstY = height - 78 - (lines.length - 1) * 18;
      lines.forEach((line, index) => ctx.fillText(line, width / 2, firstY + index * 40));
      ctx.textAlign = "left";

      if (time < totalDuration) {
        requestAnimationFrame(draw);
      } else if (!finished) {
        finished = true;
        recorder.stop();
      }
    }

    const stopped = new Promise((resolve) => {
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: recorder.mimeType || "video/webm" });
        const buffer = await blob.arrayBuffer();
        await window.saveVideoBytes([...new Uint8Array(buffer)], recorder.mimeType || "video/webm");
        resolve({ mimeType: recorder.mimeType || "video/webm", size: buffer.byteLength, duration: totalDuration });
      };
    });

    await audioContext.resume();
    recorder.start(1000);
    source.start();
    draw();
    return stopped;
  }, { timeline, images, audioDataUrl });

  await browser.close();
  console.log(`Created ${outPath}`);
  console.log(JSON.stringify(result, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
