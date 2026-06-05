# 提交与 Demo 检查清单

这份清单用于正式提交前自检，来源于 `作品提交.docx` 中的评审规则和提交规范。

## 必交内容

- 公开的 GitHub/Gitee 仓库：当前仓库为 `678xux/ai-novel-to-screenplay`，提交前按比赛要求调整可见性。
- README 文档：根目录 `README.md` 已包含功能说明、启动方式、测试命令、Schema 文档位置和依赖说明。
- Demo 视频：录制完成后，把可访问链接补到 README 的“Demo 视频”小节。

## 作品完整度与创新性

建议 demo 覆盖以下主流程：

1. 打开 `http://localhost:4173`，说明这是通用小说输入工具，不绑定示例作品。
2. 导入或粘贴 3 章以上小说文本，展示“清洗”和“分析”面板。
3. 选择改编模式、输出密度和转换引擎，点击“转换”。
4. 展示 YAML 输出，重点说明 `schema_version`、`source`、`characters`、`acts`、`scenes`、`beats` 和 `production_notes`。
5. 切换“大纲”视图，展示来源覆盖、修订任务、篇幅规划、角色、场景目标/阻碍/结果、道具/线索。
6. 展示 YAML/JSON/Markdown 导出，说明作者可以继续编辑和打磨初稿。

可强调的创新点：

- 来源章节覆盖报告：帮助检查下载小说是否漏转。
- 结构化修订任务：把 AI 初稿转成可执行打磨清单。
- 可选 AI adapter：无 API Key 时仍可用规则引擎，有 Key 时可增强内容。
- 可执行 YAML Schema 校验：文档和程序契约一致。

## 开发过程与质量

当前仓库已经按 PR 分步交付，主分支保持可运行。提交前可检查：

```bash
git log --oneline --decorate -12
npm run check
npm test
npm run e2e
python -m compileall app scripts
git diff --check
```

PR 规范自检：

- 每个 PR 只做一件事。
- PR 描述包含功能描述、实现思路和测试方式。
- README、Schema 文档、测试脚本与功能同步更新。
- 使用 Python 标准库实现本地后端，README 已说明无第三方运行时依赖。

## README 最后补充项

Demo 视频录制并上传后，在 README 中补入：

```md
## Demo 视频

- 视频链接：待补充
```

如果比赛要求仓库公开，请在提交前确认 GitHub 仓库可访问。
