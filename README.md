# C6A 提交成果 · Elite20 提交数据仪表盘

> **挑战**：C6A 提交数据仪表盘 ｜ **完成级别**：Level 1–4（自动扫描 + 校验引擎 + 多课程可扩展）
> **日期**：2026-11-04 ｜ **作者**：lishengdan

---

## 一句话

**输入**工作区根目录，**输出**"谁交了什么 / 齐不齐 / 缺什么 / 哪里违规"——三份 JSON + CSV、五表 Excel、双击即开的本地仪表盘。

## 30 秒跑通

```bash
cd C6A提交成果/src
python scan_submissions.py    # 扫描 + 校验 → data/
python make_excel.py          # → lishengdan_C6A_report.xlsx
python make_dashboard.py      # → dashboard/index.html
```

或者直接**双击 `dashboard/index.html`**（数据已内嵌，无需服务器、无需联网）。

## 目录

```
C6A提交成果/
├── data/                              # 结构化数据（JSON×3 + CSV）
├── dashboard/index.html + data.js     # 本地仪表盘（离线可用）
├── src/                               # 扫描器 / Excel 生成器 / 仪表盘生成器
├── 截图/lishengdan_C6A_仪表盘_总览.png # 真实渲染截图
├── lishengdan_C6A_report.xlsx         # Excel 五表
├── lishengdan_C6A_方案设计.md
├── lishengdan_C6A_教学说明.md
├── lishengdan_C6A_AAR.md
├── lishengdan_C6A_AI日志.md
└── lishengdan_C6A_拿来说明.md
```

## 真实数据（本次扫描结果，2026-11-04）

| 指标 | 数值 |
|---|---|
| 挑战注册表 | 19 个（自动解析自 challenge.json 的 deliverables 字段） |
| 扫描范围 | 11 个提交文件夹 / 499 个文件 |
| 提交组（学生×挑战） | 22 组 |
| ✅ 交付物齐全 | 4 组 |
| ⚠️ 部分提交 | 11 组 |
| — 无法机判 | 7 组（challenge.json 未定义交付物，校验器拒绝瞎猜） |
| 缺 AI 日志 | 10 组（评审硬性项，仪表盘红框高亮） |
| 命名违规 | 8 个文件（首版 392 → 修正校验范围后，剩下的全是真问题） |

## 关键设计

1. **校验器是 challenge.json 的执行器**——交付物标准不手填，换一届课程零代码改动。
2. **三态判定 + 明确的"无法机判"**，不打没有依据的分。
3. **命名规范只约束提交夹顶层的交付物**（首版 392 个假阳性 → 8 个真问题的教训写进了 AAR）。
4. **JSON 是唯一中间格式**：Excel 与网页互不依赖，均可独立重生成。
5. 仪表盘**离线可用**（数据内嵌 data.js，file:// 双击即开），文件可点击直达。

## 如实说明

本机工作区只有 lishengdan 一人的提交，因此矩阵是 2 行（含"未署名"归组）。
系统按多人设计：student 是数据模型一等字段，下一期课程把文件夹放进工作区重跑三条命令即可。
