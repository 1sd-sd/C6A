# lishengdan_C6A_方案设计

> **交付物**：Elite20 提交数据仪表盘（扫描器 + 校验引擎 + Excel 五表 + 本地网站）
> **一句话**：**输入**工作区根目录，**输出**"谁交了什么 / 齐不齐 / 违规没 / 下一步补什么"——JSON + Excel + 可点击的网页。
> **完成级别**：Level 1–4（含自动扫描、命名校验、缺项引擎、多课程可扩展）

---

## 一、问题：数据在哪里

Elite20 的提交散落在 11 个文件夹里。开始设计前先量了一下：

- **挑战资料夹** `挑战_*`：24 个，每个里有 `challenge.json`，其中 **`deliverables` 字段定义了交付物模式**（如 `README.md,*repo链接*,*AI日志*,*拿来说明*`）——这是免费的"标准答案"，不该手填
- **提交文件夹**：11 个，499 个文件，最深 4 层，含 220 个模型权重文件和大量仓库内部结构
- **学生署名**：只有文件名前缀（`lishengdan_C5_repo链接.md`）；README、训练产物等没有署名

**最关键的发现**：`challenge.json` 里已经有交付物定义。校验引擎应该是"challenge.json 的执行器"，而不是另一套独立标准——这样换一届课程、加一个新挑战，不需要改一行代码。

## 二、架构

```
挑战_*/challenge.json ──► 挑战注册表（19 个，deliverables 模式）
                                        │
提交文件夹（11 个，499 文件） ──► 扫描器 ─┴─► 学生×挑战 分组
  scan_submissions.py                   │
                        ┌───────────────┼────────────────┐
                        ▼               ▼                ▼
                   交付物命中/缺失    命名规范校验      空文件/AI日志检查
                        └───────┬───────┴────────────────┘
                                ▼
                    data/{challenges,submissions,summary}.json + submissions.csv
                    ┌─────────────┼──────────────┐
                    ▼             ▼              ▼
              make_excel.py   make_dashboard.py   （其他工具可直接吃 JSON）
              Excel 五张表    本地仪表盘(data.js 内嵌，双击即开)
```

三个脚本各干一件事，JSON 是唯一中间格式——Excel 和网页都不碰扫描逻辑。

## 三、核心技术决策（含踩坑）

### 1. 校验器只做三态判定，不猜

| 状态 | 判定条件 |
|---|---|
| ✅ complete | challenge.json 的每个交付物模式都有文件命中，且无空文件 |
| ⚠️ partial | 命中了至少一个模式，但有缺失 |
| — unverified | 该挑战的 challenge.json 没定义 deliverables（19 个里有 7 个），**明确说"无法机判"而不是装作合格** |

没有"分数"——没有 rubric 执行器之前给分就是编造。这是刻意的能力边界。

### 2. 命名规范的约束范围：只管"提交夹顶层的交付物"

第一版跑出 **392 个"违规"**，一眼就是假的。拆开看：C2G 的 220 个是量化权重（.bin/.pt），
C4C 的 50 个是仓库内部 json。**命名规范约束的是提交的交付物，不是仓库的内部结构**——
这个区别不写清楚，校验器就是一个噪音发生器。

最终规则（实测 392 → 8）：
- 只检查提交夹**顶层**文件
- 豁免：训练/模型产物（.bin/.pt/.pth/.onnx/.safetensors/.map）、仓库配置（.gitignore/.gitattributes/LICENSE 等）、.pyc
- 豁免的决定公开写进代码注释和数据分类（"训练/模型产物（豁免）"），不偷偷放水

剩下的 8 个全是真问题：C2 顶层 7 个文件（AAR.md / paper.pdf…）没按 `<作者_挑战_描述>` 命名，C2A 的 SUBMISSION.md 同理。

### 3. 一个文件最多顶一个交付物模式（贪心唯一分配）

README 不能同时算"README"和"使用说明"。每个模式按顺序匹配，命中即占用，防止完整性虚高。
（这个设计来自我 C4A 评审器的同一套教训。）

### 4. 仪表盘用 `data.js` 而不是 `fetch('data.json')`

`file://` 协议下 fetch 会被浏览器拦（CORS），双击打不开就得起服务器——验收成本 +1。
用 `<script src="data.js">` 内嵌 `window.DASH_DATA`，**双击即开、离线可用**。

### 5. 文件链接是相对路径

明细页每个文件可点击打开（`../C5提交成果/...`）。注意：**链接相对工作区根目录**，
把 `dashboard/` 单独拷走链接会失效——这是"本地仪表盘"的边界，写进了教学说明。

## 四、数据模型

```jsonc
// submissions.json（每组 = 学生×挑战）
{
  "student": "lishengdan",
  "challenge": "C4A",
  "challenge_title": "C4A 技能提交自动评审",
  "folder": "C4A提交成果",
  "file_count": 38,
  "files": ["lishengdan_C4A_AI日志.md", "..."],
  "matched": {"README.md": ["README.md"]},          // 模式 → 命中文件
  "missing_required": [],                            // 未命中的模式
  "status": "complete",                              // complete | partial | unverified
  "completeness": 1.0,
  "has_ai_log": true,
  "naming_ok": true,
  "naming_violations": [],
  "empty_files": [],
  "last_submit": "2026-10-04 14:12"
}
```

## 五、与挑战要求的对照

| Level | 要求 | 实现 |
|---|---|---|
| 1 数据收集与结构化 | JSON/CSV + 说明 | scan_submissions.py → 3 个 JSON + 1 个 CSV |
| 2 Excel 报表 | 五张 Sheet + 条件格式 | make_excel.py（openpyxl，红黄绿条件填充，缺 AI 日志标红） |
| 3 本地网站 | 总览/详情/筛选/文件链接/缺失提醒 | make_dashboard.py（矩阵热力图 + 点格看明细 + 时间线） |
| 4 自动化 | 自动扫描 + 校验引擎 + 多课程扩展 | 扫描即校验；新增挑战只需放入带 challenge.json 的资料夹，零代码改动 |

## 六、局限（如实）

1. **只能机判结构和命名**，判不了质量——质量是 C4A 评审器的职责，这里刻意不越界。
2. `unverified` 的 7 个挑战是因为 challenge.json 没写 deliverables 字段，不是扫描器偷懒。
3. 文件链接依赖工作区相对位置。
4. 学生识别靠文件名前缀，两个人用同一个前缀会被合并（当前数据只有 lishengdan + 未署名，无此问题）。
