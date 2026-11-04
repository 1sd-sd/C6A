#!/usr/bin/env python3
"""C6A 数据管线 · 第二步：Excel 报表（五个 Sheet）。

总览   学生×挑战矩阵 + 完成率
按学生 每个学生的全部提交明细
按挑战 每个挑战的全部学生与状态
时间线 全部提交记录按时间倒序
缺失项 所有缺必填项 / 缺 AI 日志 / 命名违规的条目（标红）

用法：python make_excel.py   （读取 ../data/*.json，输出 ../lishengdan_C6A_report.xlsx）
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE.parent / "lishengdan_C6A_report.xlsx"

# ── 样式 ──
HEAD_FILL = PatternFill("solid", fgColor="1F3B57")
HEAD_FONT = Font(color="FFFFFF", bold=True, size=10.5)
OK_FILL = PatternFill("solid", fgColor="D9EAD9")
WARN_FILL = PatternFill("solid", fgColor="FCE8B2")
BAD_FILL = PatternFill("solid", fgColor="F4C7C3")
GRAY_FILL = PatternFill("solid", fgColor="EFEFEF")
THIN = Side(style="thin", color="D0D0D0")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
WRAP = Alignment(vertical="top", wrap_text=True)
CENTER = Alignment(horizontal="center", vertical="center")


def style_header(ws, row, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill = HEAD_FILL
        cell.font = HEAD_FONT
        cell.alignment = CENTER
        cell.border = BORDER


def autosize(ws, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


STATUS_TEXT = {"complete": "✅ 完整", "partial": "⚠️ 部分", "unverified": "— 无法机判"}
STATUS_FILL = {"complete": OK_FILL, "partial": WARN_FILL, "unverified": GRAY_FILL}


def main() -> int:
    submissions = json.loads((DATA / "submissions.json").read_text(encoding="utf-8"))
    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    challenges = json.loads((DATA / "challenges.json").read_text(encoding="utf-8"))

    wb = Workbook()

    # ───────────────────────── Sheet 1 总览 ─────────────────────────
    ws = wb.active
    ws.title = "总览"
    t = summary["totals"]
    ws["A1"] = f"Elite20 提交数据总览 · 生成于 {summary['generated_at'][:16]}"
    ws["A1"].font = Font(bold=True, size=13)
    ws["A2"] = (f"挑战 {t['challenges']} · 学生 {t['students']} · 提交组 {t['submission_groups']} · "
                f"文件 {t['files']} · ✅完整 {t['complete']} · ⚠️部分 {t['partial']} · "
                f"—无法机判 {t['unverified']} · 缺AI日志 {t['missing_ai_log']} 组 · 命名违规 {t['naming_violations']} 个文件")
    ws["A2"].font = Font(size=10, color="666666")

    codes = sorted(challenges.keys())
    students = summary["students"]
    grid = {(s["student"], s["challenge"]): s for s in submissions}

    head_row = 4
    ws.cell(row=head_row, column=1, value="学生 \\ 挑战")
    for j, code in enumerate(codes, 2):
        ws.cell(row=head_row, column=j, value=code)
    style_header(ws, head_row, len(codes) + 1)

    for i, stu in enumerate(students, head_row + 1):
        ws.cell(row=i, column=1, value=stu).font = Font(bold=True)
        ws.cell(row=i, column=1).border = BORDER
        done = 0
        for j, code in enumerate(codes, 2):
            s = grid.get((stu, code))
            cell = ws.cell(row=i, column=j)
            cell.border = BORDER
            cell.alignment = CENTER
            if not s:
                cell.value = ""
                continue
            cell.value = STATUS_TEXT[s["status"]]
            cell.fill = STATUS_FILL[s["status"]]
            if s["status"] == "complete":
                done += 1
        rate = ws.cell(row=i, column=len(codes) + 2, value=f"{done}/{len(codes)}")
        rate.font = Font(bold=True)
        rate.border = BORDER
        rate.alignment = CENTER
    ws.cell(row=head_row, column=len(codes) + 2, value="完成数").fill = HEAD_FILL
    ws.cell(row=head_row, column=len(codes) + 2).font = HEAD_FONT
    ws.cell(row=head_row, column=len(codes) + 2).alignment = CENTER
    ws.freeze_panes = "B5"
    autosize(ws, [16] + [9] * len(codes) + [9])

    # ───────────────────────── Sheet 2 按学生 ─────────────────────────
    ws2 = wb.create_sheet("按学生")
    cols = ["学生", "挑战", "状态", "完整度", "文件数", "缺必填项", "AI日志", "命名违规", "最后提交", "文件夹"]
    ws2.append(cols)
    style_header(ws2, 1, len(cols))
    for s in sorted(submissions, key=lambda x: (x["student"], x["challenge"])):
        ws2.append([
            s["student"], s["challenge"], STATUS_TEXT[s["status"]],
            s["completeness"] if s["completeness"] is not None else "—",
            s["file_count"], "、".join(s["missing_required"]) or "—",
            "✅" if s["has_ai_log"] else "❌ 缺",
            "、".join(s["naming_violations"]) or "—",
            s["last_submit"], s["folder"],
        ])
        r = ws2.max_row
        ws2.cell(row=r, column=3).fill = STATUS_FILL[s["status"]]
        if not s["has_ai_log"]:
            ws2.cell(row=r, column=7).fill = BAD_FILL
        for c in range(1, len(cols) + 1):
            ws2.cell(row=r, column=c).border = BORDER
            ws2.cell(row=r, column=c).alignment = WRAP
    ws2.freeze_panes = "A2"
    ws2.auto_filter.ref = f"A1:J{ws2.max_row}"
    autosize(ws2, [12, 7, 11, 8, 7, 30, 8, 30, 17, 24])

    # ───────────────────────── Sheet 3 按挑战 ─────────────────────────
    ws3 = wb.create_sheet("按挑战")
    cols3 = ["挑战", "标题", "状态分布", "参与学生", "交付物要求（来自 challenge.json）"]
    ws3.append(cols3)
    style_header(ws3, 1, len(cols3))
    for code in codes:
        c = challenges[code]
        rows = [s for s in submissions if s["challenge"] == code]
        dist = " / ".join(f"{STATUS_TEXT[st]}×{sum(1 for r in rows if r['status'] == st)}"
                          for st in ("complete", "partial", "unverified") if any(r["status"] == st for r in rows)) or "无提交"
        ws3.append([code, c["title"], dist, "、".join(sorted({r["student"] for r in rows})) or "—",
                    "；".join(c["deliverable_patterns"]) or "（challenge.json 未定义）"])
        for cidx in range(1, len(cols3) + 1):
            ws3.cell(row=ws3.max_row, column=cidx).border = BORDER
            ws3.cell(row=ws3.max_row, column=cidx).alignment = WRAP
    autosize(ws3, [7, 34, 26, 22, 60])

    # ───────────────────────── Sheet 4 时间线 ─────────────────────────
    ws4 = wb.create_sheet("时间线")
    cols4 = ["最后提交", "学生", "挑战", "状态", "文件数", "文件夹"]
    ws4.append(cols4)
    style_header(ws4, 1, len(cols4))
    for s in sorted(submissions, key=lambda x: x["last_submit"], reverse=True):
        ws4.append([s["last_submit"], s["student"], s["challenge"], STATUS_TEXT[s["status"]], s["file_count"], s["folder"]])
        r = ws4.max_row
        ws4.cell(row=r, column=4).fill = STATUS_FILL[s["status"]]
        for c in range(1, len(cols4) + 1):
            ws4.cell(row=r, column=c).border = BORDER
    ws4.freeze_panes = "A2"
    autosize(ws4, [17, 12, 8, 11, 8, 26])

    # ───────────────────────── Sheet 5 缺失项 ─────────────────────────
    ws5 = wb.create_sheet("缺失项")
    cols5 = ["问题类型", "学生", "挑战", "详情", "文件夹"]
    ws5.append(cols5)
    style_header(ws5, 1, len(cols5))
    n_issues = 0

    def issue(kind, s, detail):
        nonlocal n_issues
        ws5.append([kind, s["student"], s["challenge"], detail, s["folder"]])
        r = ws5.max_row
        fill = BAD_FILL if kind != "无法机判" else GRAY_FILL
        ws5.cell(row=r, column=1).fill = fill
        for c in range(1, len(cols5) + 1):
            ws5.cell(row=r, column=c).border = BORDER
            ws5.cell(row=r, column=c).alignment = WRAP
        n_issues += 1

    for s in sorted(submissions, key=lambda x: (x["challenge"], x["student"])):
        for m in s["missing_required"]:
            issue("缺必填交付物", s, m)
        if not s["has_ai_log"]:
            issue("缺 AI 日志", s, "评审硬性要求，缺此项无法评审")
        for v in s["naming_violations"]:
            issue("命名违规", s, v)
        for e in s["empty_files"]:
            issue("空文件", s, e)
    ws5.freeze_panes = "A2"
    ws5.auto_filter.ref = f"A1:E{ws5.max_row}"
    autosize(ws5, [14, 12, 8, 52, 26])

    wb.save(OUT)
    print(f"已写出 {OUT}（5 个 Sheet，{n_issues} 条缺失项）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
