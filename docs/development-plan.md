# 开发过程与质量计划

比赛评分把“开发过程与质量”列为 40%，所以本项目按持续交付方式推进，而不是最后一次性导入代码。

## 目标

- 主分支始终可运行。
- 每个 PR 只做一件事，标题、功能描述、实现思路、测试方式完整。
- commit 分布围绕真实功能推进，避免临尾集中提交。
- README、Schema 文档、测试脚本与功能同步更新。

## 建议 PR 顺序

1. 项目初始化与本地 HTTP 服务
   - 范围：`package.json`、`server.js`、基础静态页面。
   - 测试：访问本地端口，确认页面可打开。

2. 小说解析与 YAML 转换核心
   - 范围：`src/converter.js`、`src/schema.js`。
   - 测试：三章小说输入可以生成 `script.acts.scenes.beats`。

3. 通用输入工作台
   - 范围：`public/index.html`、`public/styles.css`、`public/app.js`。
   - 测试：粘贴任意小说、导入 TXT/Markdown、复制和下载 YAML。

4. Schema 文档与设计说明
   - 范围：`docs/yaml-schema.md`。
   - 测试：文档字段与实际 YAML 输出一致。

5. 通用性测试与质量门禁
   - 范围：`scripts/smoke-check.js`、`scripts/converter-tests.js`。
   - 测试：`npm run check`、`npm test`。

6. AI 增强转换
   - 范围：新增 AI adapter，把规则引擎结果作为初稿上下文。
   - 测试：无 API Key 时仍可使用规则引擎，有 API Key 时可生成更自然的场景和对白。
   - 状态：通过 `feature/optional-ai-adapter` 分支实现，支持自动回退和配置检测。

7. Python 后端迁移
   - 范围：将服务端、转换器、质量报告和 AI adapter 迁移到 Python 标准库实现。
   - 测试：`npm run check`、`npm test`，浏览器验证静态页面/API 行为不变。
   - 目的：减少运行时依赖，便于评委和作者在本地复现。

8. 多文件导入与输入分析
   - 范围：支持多 TXT/Markdown 文件按文件名排序合并，新增 `/api/analyze` 输入分析接口和前端分析面板。
   - 测试：样本章节分析、少于 3 章警告、无章节标题警告、浏览器导入/分析/转换回归。
   - 目的：服务真实小说下载测试场景，降低作者整理输入文本的门槛。

9. 剧本大纲预览
   - 范围：新增 YAML / 大纲输出视图切换，把结构化结果渲染为可扫读的角色、幕、场景、冲突、转折和节拍列表。
   - 测试：浏览器验证转换后大纲可显示角色和场景，YAML 视图仍可复制/下载。
   - 目的：提升作者打磨效率，让工具不只是输出机器可读 YAML，也提供人类可读的剧本检查视图。

## PR 描述模板

```md
## 标题
一句话说明本 PR 新增/修改了什么。

## 功能描述
说明该功能的作用、入口和使用方式。

## 实现思路
说明核心模块、技术选型、数据流和边界处理。

## 测试方式
- [ ] npm run check
- [ ] npm test
- [ ] 浏览器打开 http://localhost:4173 手动验证
```

## 当前质量门禁

```bash
npm run check
npm test
```

后续接入更复杂 AI 能力后，应增加：

- YAML Schema 校验。
- 更长小说样本的转换快照测试。
- 前端导入、复制、下载的浏览器自动化测试。
- 错误输入、超长输入和无章节标题输入的边界测试。
- AI adapter 的 mock 响应测试，覆盖模型返回异常、空 JSON 和 Schema 字段缺失。
