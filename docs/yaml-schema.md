# 剧本 YAML Schema 设计文档

## 设计目标

本 Schema 用于承接“小说文本自动转换为剧本初稿”的结果。它不是只保存一段改写后的文本，而是把小说改编拆成作者后续最需要编辑的结构：角色、幕、场景、节拍、冲突、转折和制作备注。

设计时遵循四个原则：

1. 可编辑：作者可以直接修改角色、场景、对白和动作。
2. 可追溯：每个场景保留来源章节，方便回到原小说核对。
3. 可扩展：后续可以接入 AI 润色、分镜、预算、拍摄计划等模块。
4. 可验证：字段层级稳定，便于程序检查是否满足“3 章以上小说转结构化剧本”的要求。

## 顶层结构

```yaml
script:
  schema_version: 1.0.0
  title: 示例作品
  source: {}
  logline: 一句话故事梗概
  themes: []
  characters: []
  acts: []
  production_notes: {}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `schema_version` | string | 是 | Schema 版本号，方便未来升级。 |
| `title` | string | 是 | 剧本标题。 |
| `source` | object | 是 | 原小说来源信息。 |
| `logline` | string | 是 | 一句话故事梗概。 |
| `themes` | string[] | 是 | 主题关键词；没有用户输入时由工具提供默认主题。 |
| `characters` | object[] | 是 | 角色列表。 |
| `acts` | object[] | 是 | 幕结构；当前版本默认按章节映射为幕。 |
| `production_notes` | object | 是 | 运行时长、警告和修改建议。 |

## source

```yaml
source:
  type: novel
  chapter_count: 3
  input_language: zh-CN
  adaptation_mode: drama
```

### 设计原因

小说转剧本需要保留输入来源，否则后续很难判断结果是否满足题目要求。`chapter_count` 明确记录章节数，用于检查是否达到 3 章以上。`adaptation_mode` 用于区分影视剧、短剧、舞台剧等输出风格。

## characters

```yaml
characters:
  - id: char_01
    name: 林澈
    role: 主角/核心视角
    traits:
      - 固执
      - 敏感
    first_appearance: 第一章 雾港来信
    goal: 追寻核心真相并推动主要选择
    arc: 从被动卷入事件，到主动做出关键选择
    appearances:
      - scene_01_01
```

### 设计原因

剧本创作比小说更依赖人物调度和对白归属，因此角色被放在独立列表中，而不是散落在场景里。`id` 保证角色可被其他模块引用，`first_appearance` 让作者能快速回看人物第一次出现的位置。

`goal` 和 `arc` 用于把角色从“名单”提升为“可打磨的人物线”。自动结果允许先给出待确认的目标和弧光占位，作者后续可以继续改写。`appearances` 记录角色出现过的场景 id，方便检查某个角色是否长时间消失，也方便后续扩展为人物戏份统计。

## acts

```yaml
acts:
  - id: act_01
    title: 第一章 雾港来信
    source_chapters:
      - 第一章 雾港来信
    purpose: 建立人物、世界观与核心矛盾
    scenes: []
```

### 设计原因

“幕”是剧本结构的主要骨架。小说章节天然可以作为第一版幕结构，因此当前工具默认把章节映射为幕。这样既满足自动转换的稳定性，又方便作者后续把多个章节合并为一幕，或把一个章节拆成多个幕。

## scenes

```yaml
scenes:
  - id: scene_01_01
    title: 第一章 雾港来信 · 场景 1
    source_chapter: 第一章 雾港来信
    location: 码头
    time: 清晨
    mood: 紧张
    summary: 林澈收到匿名信并决定前往旧灯塔。
    objective: 推动人物完成关键行动：林澈收到匿名信并决定前往旧灯塔。
    obstacle: 林澈必须在警告和真相之间做选择。
    outcome: 售票亭电话响起，提示信不是给他的。
    beats: []
    conflict: 林澈必须在警告和真相之间做选择。
    turning_point: 售票亭电话响起，提示信不是给他的。
    props:
      - 匿名信
    notes:
      - 建议人工校准场景边界。
```

### 设计原因

场景是剧本最核心的编辑单位。每个场景包含地点、时间、情绪、摘要、冲突、转折和道具，原因如下：

- `location` 与 `time` 对拍摄和舞台调度非常关键。
- `summary` 让作者快速扫读整集结构。
- `objective`、`obstacle`、`outcome` 对应场景目标、阻碍和结果，方便作者判断每场是否有明确戏剧推进。
- `conflict` 与 `turning_point` 帮助作者判断场景是否有戏剧推进。
- `props` 为后续分镜、拍摄计划和美术准备保留扩展空间。
- `source_chapter` 保证改编结果能追溯回原文。

## beats

```yaml
beats:
  - id: scene_01_01_beat_01
    type: action
    text: 林澈站在废弃售票亭前，手里捏着一封没有署名的信。
    camera: 中景
    hook: 保留反转/悬念，适合短剧卡点
    stage_direction: 用灯光、走位和停顿呈现
  - id: scene_01_01_beat_02
    type: dialogue
    speaker: 周栩
    text: 你真的要去旧灯塔？
    emotion: 紧张
```

### 设计原因

节拍是场景内部的最小可编辑单位。小说段落通常混合动作、心理描写和对白，如果只输出完整场景文本，作者仍然需要重新拆分。使用 `beats` 可以把内容拆成动作、对白、旁白和转场：

- `action` 用于可表演动作。
- `dialogue` 用于角色对白。
- `narration` 用于暂时无法视觉化的心理或背景信息。
- `transition` 用于转场提示。

`camera` 和 `emotion` 不是强制字段，但可以辅助作者继续发展分镜和表演提示。

当 `adaptation_mode` 为 `short` 时，节拍可包含 `hook`，用于提示短剧卡点、反转或追看点。当 `adaptation_mode` 为 `stage` 时，节拍可包含 `stage_direction`，用于提示灯光、走位、停顿和上下场调度。

## production_notes

```yaml
production_notes:
  estimated_runtime_minutes: 18
  adaptation_warnings:
    - 输入章节少于 3 个，不满足比赛题目要求。
  revision_suggestions:
    - 复核角色名与对白归属。
    - 把小说心理描写改写成可表演动作。
```

### 设计原因

自动转换不应该假装一次完成专业剧本。`production_notes` 明确告诉作者哪些地方需要复核，例如章节数量不足、角色识别不确定、心理描写需要视觉化。这样工具更符合“AI 辅助创作”的定位：先给出可用初稿，再引导作者打磨。

## 完整示例

```yaml
script:
  schema_version: 1.0.0
  title: 雾港来信
  source:
    type: novel
    chapter_count: 3
    input_language: zh-CN
    adaptation_mode: drama
  logline: 林澈收到匿名信后前往旧灯塔，逐步发现父亲失踪背后的雾港秘密。
  themes:
    - 信任
    - 真相
    - 成长
  characters:
    - id: char_01
      name: 林澈
      role: 主角/核心视角
      traits: []
      first_appearance: 第一章 雾港来信
      goal: 追寻核心真相并推动主要选择
      arc: 从被动卷入事件，到主动做出关键选择
      appearances:
        - scene_01_01
  acts:
    - id: act_01
      title: 第一章 雾港来信
      source_chapters:
        - 第一章 雾港来信
      purpose: 建立人物、世界观与核心矛盾
      scenes:
        - id: scene_01_01
          title: 第一章 雾港来信 · 场景 1
          source_chapter: 第一章 雾港来信
          location: 码头
          time: 清晨
          mood: 紧张
          summary: 林澈收到匿名信并决定前往旧灯塔。
          objective: 推动人物完成关键行动：林澈收到匿名信并决定前往旧灯塔。
          obstacle: 林澈必须在警告和真相之间做选择。
          outcome: 售票亭电话响起，提示信不是给他的。
          beats:
            - id: scene_01_01_beat_01
              type: action
              text: 林澈站在废弃售票亭前，手里捏着一封没有署名的信。
              camera: 中景
            - id: scene_01_01_beat_02
              type: dialogue
              speaker: 周栩
              text: 你真的要去旧灯塔？
              emotion: 紧张
          conflict: 林澈必须在警告和真相之间做选择。
          turning_point: 售票亭电话响起，提示信不是给他的。
          props:
            - 匿名信
          notes:
            - 建议人工校准场景边界。
  production_notes:
    estimated_runtime_minutes: 18
    adaptation_warnings: []
    revision_suggestions:
      - 复核角色名与对白归属。
      - 把小说心理描写改写成可表演动作。
```
