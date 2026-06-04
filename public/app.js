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
const charactersInput = document.querySelector("#charactersInput");
const themesInput = document.querySelector("#themesInput");
const novelInput = document.querySelector("#novelInput");
const yamlOutput = document.querySelector("#yamlOutput");
const warningBox = document.querySelector("#warningBox");
const convertBtn = document.querySelector("#convertBtn");
const loadSampleBtn = document.querySelector("#loadSampleBtn");
const fileInput = document.querySelector("#fileInput");
const copyBtn = document.querySelector("#copyBtn");
const downloadBtn = document.querySelector("#downloadBtn");

let latestYaml = "";

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

async function convert() {
  convertBtn.disabled = true;
  yamlOutput.textContent = "转换中...";
  setWarnings([]);

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
        characters: charactersInput.value,
        themes: themesInput.value,
        text: novelInput.value
      })
    });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "转换失败");

    latestYaml = data.yaml;
    yamlOutput.textContent = data.yaml;
    setStats(data.stats);
    setWarnings(data.warnings);
  } catch (error) {
    latestYaml = "";
    yamlOutput.textContent = error instanceof Error ? error.message : "转换失败";
    setStats();
  } finally {
    convertBtn.disabled = false;
  }
}

function inferTitleFromFilename(fileName = "") {
  return fileName.replace(/\.(txt|md|markdown)$/i, "").replace(/[_-]+/g, " ").trim();
}

async function importNovelFile(event) {
  const [file] = event.target.files || [];
  if (!file) return;

  const text = await file.text();
  novelInput.value = text.trim();
  if (!titleInput.value.trim()) {
    titleInput.value = inferTitleFromFilename(file.name);
  }
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

function downloadYaml() {
  if (!latestYaml) return;
  const blob = new Blob([latestYaml], { type: "text/yaml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${titleInput.value || "screenplay"}.screenplay.yaml`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
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
copyBtn.addEventListener("click", copyYaml);
downloadBtn.addEventListener("click", downloadYaml);

setStats();
