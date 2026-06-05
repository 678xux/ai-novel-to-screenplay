# 使用说明

本文档用于本地运行、功能演示和比赛评审复现。工具目标是把 3 个章节以上的小说文本转换为结构化剧本 YAML，帮助小说作者快速获得可继续编辑和打磨的剧本初稿。

## 环境要求

- Python 3.11 或更高版本。
- Node.js/npm 只用于运行 `package.json` 中的便捷命令。
- 默认规则引擎不需要第三方 Python 包，也不需要 API Key。

## 启动 Web 工具

在项目根目录运行：

```bash
npm start
```

启动后访问：

```text
http://localhost:4173
```

## Web 使用流程

1. 在左侧填写作品名、主要角色和主题。
2. 粘贴小说正文，或点击右上角“导入”选择一个或多个 `.txt` / `.md` 文件。
3. 输入文本应包含 3 个章节以上，推荐使用 `第一章`、`第二章`、`Chapter 1`、`1. 标题` 等章节标题。
4. 如果文本来自网络下载，先点击“清洗”，移除广告、网址、分隔线、目录提示和重复空行。
5. 点击“分析”，检查章节数、字数、段落数、对白数和格式风险。
6. 选择改编模式：
   - `影视剧`：生成镜头提示，适合常规影视剧初稿。
   - `短剧`：强化场尾钩子和反转提示。
   - `舞台剧`：生成舞台调度、灯光和停顿提示。
7. 选择输出密度：
   - `紧凑`：场景更少，适合先看整体结构。
   - `均衡`：默认推荐。
   - `细分`：场景更多，适合进一步拆分分镜或舞台调度。
8. 点击“转换”，右侧生成 YAML 剧本。
9. 在右侧切换 `YAML` 和 `大纲` 视图：
   - `YAML` 用于保存、提交和后续程序处理。
   - `大纲` 用于人工快速检查来源覆盖、修订任务、篇幅规划、角色、场景和节拍。
10. 选择导出格式并点击下载，可导出 YAML、JSON 或 Markdown 大纲。

## 命令行转换

不打开浏览器时，也可以直接把小说文件转换为剧本文件：

```bash
python scripts/convert_file.py examples/three-chapter-novel.txt --title "雾港来信" --characters "林澈，沈雾，周栩" --themes "信任，真相，成长"
```

导出 JSON：

```bash
python scripts/convert_file.py examples/three-chapter-novel.txt --format json
```

导出 Markdown 大纲：

```bash
python scripts/convert_file.py examples/three-chapter-novel.txt --format outline_md
```

指定输出文件：

```bash
python scripts/convert_file.py examples/three-chapter-novel.txt -o output.screenplay.yaml
```

常用参数：

```text
--mode drama|short|stage
--density compact|balanced|detailed
--engine rules|ai
--characters "角色A，角色B"
--themes "主题A，主题B"
```

## 可选 AI 增强

默认使用本地规则引擎，方便比赛演示和离线复现。

如需启用 AI 增强，在启动服务或运行命令行前设置：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="gpt-4.1-mini"
npm start
```

OpenAI-compatible 服务也可设置：

```powershell
$env:OPENAI_BASE_URL="https://api.openai.com/v1"
```

AI 增强只在既定 YAML Schema 内优化内容；如果 API 不可用，会自动回退到规则引擎。

## 输出内容说明

生成结果包含：

- `schema_version`：当前 YAML Schema 版本。
- `source`：来源类型、章节数、语言和改编模式。
- `logline`：故事梗概。
- `themes`：主题列表。
- `characters`：角色、功能、目标、弧光和出场轨迹。
- `acts`：按章节组织的幕。
- `scenes`：场景标题、地点、时间、情绪、摘要、目标、阻碍、结果、冲突和转折。
- `beats`：动作、对白、旁白和转场节拍。
- `props`：场景中的关键道具和线索。
- `production_notes.runtime_plan`：总时长、场均时长和节奏建议。
- `production_notes.source_coverage`：每个来源章节是否已转换为可编辑场景。
- `production_notes.revision_tasks`：下一步人工打磨任务清单。

完整 Schema 见：

```text
docs/yaml-schema.md
```

## 质量检查

提交或录制 demo 前建议运行：

```bash
npm run check
npm test
npm run e2e
python -m compileall app scripts
git diff --check
```

这些检查会覆盖核心转换、Schema 校验、示例输入、清洗、分析、导出和端到端 API 行为。

## Demo 录制建议

1. 打开 `http://localhost:4173`。
2. 点击“示例”快速展示完整流程，或导入自己下载的 3 章以上小说文本。
3. 展示“清洗”和“分析”，说明工具面向真实下载文本。
4. 点击“转换”，展示右侧 YAML。
5. 切换“大纲”，重点展示来源覆盖、修订任务、篇幅规划、角色弧光、场景目标/阻碍/结果。
6. 分别导出 YAML、JSON 或 Markdown 大纲。
7. 说明无 API Key 时规则引擎可稳定运行，有 API Key 时可启用 AI 增强。

