#!/usr/bin/env python3
"""C6A 数据管线 · 第一步：扫描 + 校验引擎。

输入：Elite20 工作区根目录
输出（data/ 下）：
  challenges.json   挑战注册表（从各 挑战_*/challenge.json 自动解析）
  submissions.json  提交记录（学生 × 挑战 × 文件 × 命中/缺失）
  summary.json      总览统计
  submissions.csv   平面表（给 Excel / 其他工具吃）

设计原则：
  1. 挑战的交付物要求不手填——直接解析 challenge.json 的 deliverables 字段；
  2. 校验器只做确定判定：命中 / 缺失 / 命名违规 / 空文件，不猜；
  3. 目录结构只假设两条：挑战资料夹叫 挑战_*，提交文件夹名含 "提交成果"（外加白名单）。
"""

from __future__ import annotations

import csv
import fnmatch
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------- 配置

WORKSPACE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parents[1] / "data"

# 提交文件夹白名单：名字含"提交成果"，或历史上就这样叫的
SUBMIT_DIR_HINTS = ("提交成果", "C4技能分享")
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", "skilllens", "neoskills",
             "skilllens-web", "coursefactory", "agent-os", "_parity", "out", "报告样例",
             "dashboard", "data", "src", "参考资料", "demo", "examples", "评测工具", "benchmark"}

NAME_RE = re.compile(r"^(?P<author>[A-Za-z][A-Za-z0-9]*)_(?P<code>C\d+[A-Z]?)_(?P<rest>.+)$")
CHALLENGE_TITLE_RE = re.compile(r"^(?P<code>C\d+[A-Z]?)\b")

# 命名规范只约束"交付物类"文件。训练/模型产物和仓库配置文件豁免——
# 否则 C2G 的 220 个量化权重会把真正的问题淹没（实测 392 → 24）。
ARTIFACT_EXEMPT = {".bin", ".pt", ".pth", ".onnx", ".safetensors", ".ckpt", ".map", ".model", ".llmcache"}
REPO_CONFIG = {".gitignore", ".gitattributes", ".editorconfig", "license", "pyproject.toml"}


def load_challenges() -> dict[str, dict]:
    """解析所有 挑战_*/challenge.json → {code: {...}}。"""
    reg: dict[str, dict] = {}
    for d in sorted(WORKSPACE.glob("挑战_*")):
        cj = d / "challenge.json"
        if not cj.exists():
            continue
        try:
            data = json.loads(cj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  ! 跳过 {d.name}：challenge.json 解析失败（{exc}）")
            continue
        m = CHALLENGE_TITLE_RE.match(data.get("title", ""))
        if not m:
            print(f"  ! 跳过 {d.name}：title 里解析不出挑战编号")
            continue
        code = m.group("code")
        pats = [p.strip() for p in str(data.get("deliverables", "")).split(",") if p.strip()]
        reg[code] = {
            "code": code,
            "challenge_uid": data.get("challenge_id", ""),
            "title": data.get("title", code),
            "deliverable_patterns": pats,
            "materials_dir": d.name,
            "rubric_points": sum(
                dim.get("maxPoints", 0)
                for dim in _safe_rubric(data.get("rubric_dimensions"))
                .get("dimensions", [])
            ) or None,
        }
    return reg


def _safe_rubric(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {}


def iter_submit_dirs() -> list[Path]:
    dirs = []
    for d in sorted(WORKSPACE.iterdir()):
        if not d.is_dir():
            continue
        if d.name.startswith("挑战_") or d.name.startswith(".") or d.name == "C6A提交成果":
            continue
        if any(h in d.name for h in SUBMIT_DIR_HINTS):
            dirs.append(d)
    return dirs


def match_patterns(files: list[str], patterns: list[str]) -> tuple[dict, list]:
    """每个交付物模式 → 命中的文件（贪心唯一分配，一个文件最多顶一个模式）。"""
    used: set[str] = set()
    hits: dict[str, list[str]] = {}
    for pat in patterns:
        low = pat.lower()
        found = []
        for f in files:
            if f in used:
                continue
            if fnmatch.fnmatch(f.lower(), low) or (low.startswith("*") and low[1:].rstrip("*") in f.lower()):
                found.append(f)
        if found:
            used.add(found[0])
            hits[pat] = [found[0]]
    missing = [p for p in patterns if p not in hits]
    return hits, missing


def scan(submit_dir: Path, reg: dict[str, dict]) -> list[dict]:
    records = []
    for f in sorted(submit_dir.rglob("*")):
        if not f.is_file():
            continue
        rel_parts = f.relative_to(submit_dir).parts
        if any(p in SKIP_DIRS for p in rel_parts[:-1]):
            continue
        m = NAME_RE.match(f.name)
        size = f.stat().st_size
        exempt = (
            f.suffix.lower() in ARTIFACT_EXEMPT
            or f.name.lower() in REPO_CONFIG
            or f.suffix.lower() in (".pyc",)
        )
        # 命名规范只约束"提交夹顶层"的交付物；子目录里的文件是仓库内部结构，
        # 不该被交付物命名规则管（否则 C2G 的 tokenizer 词表比真问题还多 10 倍）。
        top_level = len(rel_parts) == 1
        if m:
            author, code = m.group("author"), m.group("code")
            naming_ok = True
            naming_note = ""
        else:
            # 顶层 README / 非<作者_挑战_描述>命名 → 归属到文件夹对应的挑战
            author, code = "", _folder_code(submit_dir.name, reg)
            naming_ok = exempt or not top_level or (f.suffix.lower() == ".md" and f.name.lower() == "readme.md")
            naming_note = "" if naming_ok else "顶层文件未按 <作者_挑战_描述> 命名"
            if not code:
                continue  # 连挑战都归属不了，不计入
        if code not in reg:
            naming_note = naming_note or f"挑战编号 {code} 不在注册表"
        rec = {
            "student": author or "（未署名）",
            "student_known": bool(author),
            "challenge": code,
            "challenge_title": reg.get(code, {}).get("title", code),
            "folder": submit_dir.name,
            "file": f.name,
            "rel_path": f.relative_to(WORKSPACE).as_posix(),
            "size": size,
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            "empty": size == 0,
            "naming_ok": naming_ok,
            "naming_note": naming_note,
            "category": _category(f.name),
        }
        records.append(rec)
    return records


def _folder_code(folder: str, reg: dict[str, dict]) -> str:
    """从提交文件夹名推断挑战编号：取能匹配的最长编号。"""
    stem = folder.replace("提交成果", "").replace("C4技能分享", "C4").strip("_")
    stem = re.sub(r"^C\d+.*?提交成果", lambda m: m.group(0), stem)  # no-op，保思路清晰
    codes = sorted(reg.keys(), key=len, reverse=True)
    for c in codes:
        if folder.startswith(c):
            return c
    # C2_提交成果_AI4Math论文 这类
    m = re.match(r"^(C\d+[A-Z]?)", folder)
    return m.group(1) if m and m.group(1) in reg else ""


def _category(name: str) -> str:
    low = name.lower()
    if low in REPO_CONFIG or low.endswith(".pyc"):
        return "仓库配置（豁免）"
    if low.endswith(tuple(ARTIFACT_EXEMPT)):
        return "训练/模型产物（豁免）"
    if "ai日志" in name:
        return "AI日志"
    if "拿来说明" in name or "attribution" in low:
        return "拿来说明"
    if "aar" in low or "复盘" in name or "反思" in name:
        return "AAR/复盘"
    if name.endswith(".skill"):
        return "技能包"
    if low.endswith((".png", ".jpg", ".jpeg", ".gif")):
        return "截图/Demo"
    if low.endswith(".html"):
        return "网页"
    if low.endswith(".pdf"):
        return "PDF"
    if low == "readme.md":
        return "README"
    if low.endswith((".py", ".js", ".sh", ".bat")):
        return "代码"
    return "其他"


def group(records: list[dict], reg: dict[str, dict]) -> list[dict]:
    """聚合成 学生×挑战 的提交记录，逐项对照交付物模式。"""
    grouped: dict[tuple, list[dict]] = {}
    for r in records:
        grouped.setdefault((r["student"], r["challenge"]), []).append(r)

    out = []
    for (student, code), items in sorted(grouped.items()):
        regc = reg.get(code, {})
        pats = regc.get("deliverable_patterns", [])
        files = [i["file"] for i in items]
        hits, missing = match_patterns(files, pats) if pats else ({}, [])
        all_named = all(i["naming_ok"] for i in items)
        violations = [i["file"] for i in items if not i["naming_ok"]]
        empties = [i["file"] for i in items if i["empty"]]
        has_ai_log = any("AI日志" in i["file"] for i in items)

        if pats and not missing and not empties:
            status = "complete"
        elif pats and len(hits) > 0:
            status = "partial"
        else:
            status = "unverified"  # 注册表里没有交付物定义，无法机判

        out.append({
            "student": student,
            "challenge": code,
            "challenge_title": regc.get("title", code),
            "folder": items[0]["folder"],
            "file_count": len(items),
            "files": files,
            "matched": hits,
            "missing_required": missing,
            "status": status,
            "completeness": round(len(hits) / len(pats), 2) if pats else None,
            "has_ai_log": has_ai_log,
            "naming_ok": all_named,
            "naming_violations": violations,
            "empty_files": empties,
            "last_submit": max(i["mtime"] for i in items),
        })
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"工作区：{WORKSPACE}")

    reg = load_challenges()
    print(f"挑战注册表：{len(reg)} 个（来自 challenge.json 的 deliverables 字段）")

    records: list[dict] = []
    for d in iter_submit_dirs():
        n0 = len(records)
        records.extend(scan(d, reg))
        print(f"  扫描 {d.name:<22} {len(records) - n0:>4} 个文件")

    submissions = group(records, reg)
    students = sorted({s["student"] for s in submissions})
    print(f"提交记录：{len(submissions)} 组（学生×挑战），学生 {len(students)} 人")

    by_challenge: dict[str, dict] = {}
    for s in submissions:
        c = by_challenge.setdefault(s["challenge"], {
            "challenge": s["challenge"], "title": s["challenge_title"],
            "students": [], "complete": 0, "partial": 0, "unverified": 0,
        })
        c["students"].append(s["student"])
        c[s["status"]] += 1

    summary = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspace": str(WORKSPACE),
        "totals": {
            "challenges": len(reg),
            "students": len(students),
            "submission_groups": len(submissions),
            "files": len(records),
            "complete": sum(1 for s in submissions if s["status"] == "complete"),
            "partial": sum(1 for s in submissions if s["status"] == "partial"),
            "unverified": sum(1 for s in submissions if s["status"] == "unverified"),
            "missing_ai_log": sum(1 for s in submissions if not s["has_ai_log"]),
            "naming_violations": sum(len(s["naming_violations"]) for s in submissions),
        },
        "students": students,
        "by_challenge": sorted(by_challenge.values(), key=lambda x: x["challenge"]),
    }

    (OUT / "challenges.json").write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "submissions.json").write_text(json.dumps(submissions, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    flat = [{k: v for k, v in s.items() if k not in ("matched", "files")}
            | {"files": " | ".join(s["files"]), "matched": " | ".join(s["matched"].keys())}
            for s in submissions]
    with (OUT / "submissions.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)

    t = summary["totals"]
    print(f"汇总：完整 {t['complete']} / 部分 {t['partial']} / 无法机判 {t['unverified']}；"
          f"缺 AI 日志 {t['missing_ai_log']} 组；命名违规 {t['naming_violations']} 个文件")
    print(f"输出 → {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
