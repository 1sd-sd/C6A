#!/usr/bin/env python3
"""C6A 数据管线 · 第三步：本地仪表盘。

读取 ../data/*.json，生成 dashboard/index.html + dashboard/data.js。
data.js 用 <script> 而不是 fetch —— 这样双击 HTML（file:// 协议）也能打开，
不需要起本地服务器。
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE.parent / "dashboard"

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Elite20 提交数据仪表盘</title>
<style>
:root{--bg:#f6f4ef;--panel:#fffdf9;--ink:#1c1b18;--muted:#7b776e;--line:#e4dfd4;--accent:#2f5d8a;
--ok:#2f7d45;--okbg:#dcefe0;--warn:#a86a00;--warnbg:#fbf1dc;--bad:#ac2d24;--badbg:#f7e2df;--graybg:#eceae4}
*{box-sizing:border-box}html,body{margin:0}
body{background:var(--bg);color:var(--ink);font:14px/1.6 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;padding-bottom:60px}
.wrap{max-width:1240px;margin:0 auto;padding:24px 20px}
h1{font-size:21px;margin:0 0 2px}.sub{color:var(--muted);font-size:12.5px;margin-bottom:18px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:18px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.stat b{display:block;font-size:22px;letter-spacing:-.5px}
.stat span{font-size:12px;color:var(--muted)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:18px;margin-bottom:16px}
.panel h2{font-size:14.5px;margin:0 0 12px}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:12px}
select{padding:6px 9px;border:1px solid var(--line);border-radius:8px;background:#fff;font-size:12.5px;color:var(--ink)}
.chip{border:1px solid var(--line);background:#fff;border-radius:999px;padding:4px 11px;font-size:12px;cursor:pointer;color:var(--muted)}
.chip.on{background:var(--accent);border-color:var(--accent);color:#fff}
table{border-collapse:collapse;width:100%;font-size:12.3px}
th{background:#f3efe6;font-weight:600;color:var(--muted);font-size:11.5px;padding:7px 8px;border:1px solid var(--line);position:sticky;top:0}
td{border:1px solid var(--line);padding:6px 8px;text-align:center;cursor:pointer}
td.rowhead{font-weight:600;text-align:left;cursor:default;background:#fbf9f4}
td.s0{background:#fff}td.s1{background:var(--okbg);color:var(--ok);font-weight:600}
td.s2{background:var(--warnbg);color:var(--warn);font-weight:600}td.s3{background:var(--graybg);color:var(--muted)}
td.hot{box-shadow:inset 0 0 0 2px var(--bad)}
td:hover{outline:2px solid var(--accent);outline-offset:-2px}
.matrixwrap{overflow:auto;max-height:420px}
.detail{font-size:13px}
.detail h3{margin:0 0 4px;font-size:15px}
.detail .row{margin:5px 0}
.tag{display:inline-block;font-size:11px;border-radius:6px;padding:1px 7px;margin-right:6px}
.tag.ok{background:var(--okbg);color:var(--ok)}.tag.warn{background:var(--warnbg);color:var(--warn)}
.tag.bad{background:var(--badbg);color:var(--bad)}.tag.gray{background:var(--graybg);color:var(--muted)}
ul.files{list-style:none;margin:6px 0 0;padding:0;max-height:220px;overflow:auto;border:1px solid var(--line);border-radius:9px;background:#fffefb}
ul.files li{display:flex;justify-content:space-between;gap:10px;padding:4px 10px;border-bottom:1px solid #f1ede4;font-size:12px}
ul.files li a{color:var(--accent);text-decoration:none}ul.files li a:hover{text-decoration:underline}
.muted{color:var(--muted);font-size:12px}
.timeline{font-size:12.6px}
.tl{display:flex;gap:10px;padding:6px 2px;border-bottom:1px dashed var(--line);align-items:baseline}
.tl .t{color:var(--muted);font-variant-numeric:tabular-nums;flex:none;width:130px}
.tl .who{font-weight:600;flex:none;width:100px}
.legend{display:flex;gap:14px;font-size:11.5px;color:var(--muted);margin-top:8px;flex-wrap:wrap}
.legend i{display:inline-block;width:11px;height:11px;border-radius:3px;margin-right:4px;vertical-align:-1px}
.foot{color:var(--muted);font-size:11.5px;text-align:center;margin-top:20px}
</style>
</head>
<body><div class="wrap">
<h1>Elite20 提交数据仪表盘</h1>
<div class="sub" id="genAt"></div>

<div class="stats" id="stats"></div>

<div class="panel">
  <h2>完成度矩阵 · 点击格子看明细</h2>
  <div class="filters">
    <select id="fStudent"><option value="">全部学生</option></select>
    <select id="fChallenge"><option value="">全部挑战</option></select>
    <span class="chip on" data-st="">全部状态</span>
    <span class="chip" data-st="complete">✅ 完整</span>
    <span class="chip" data-st="partial">⚠️ 部分</span>
    <span class="chip" data-st="unverified">— 无法机判</span>
  </div>
  <div class="matrixwrap"><table id="matrix"></table></div>
  <div class="legend">
    <span><i style="background:var(--okbg)"></i>交付物齐全</span>
    <span><i style="background:var(--warnbg)"></i>部分提交</span>
    <span><i style="background:var(--graybg)"></i>注册表未定义交付物，无法机判</span>
    <span><i style="border:2px solid var(--bad);background:#fff"></i>缺 AI 日志（评审硬性项）</span>
  </div>
</div>

<div class="panel detail" id="detail" style="display:none"></div>

<div class="panel">
  <h2>提交时间线（按最后提交倒序）</h2>
  <div class="timeline" id="timeline"></div>
</div>

<div class="foot">数据由 src/scan_submissions.py 自动扫描生成 · 校验规则来自各挑战 challenge.json 的 deliverables 字段 · 纯静态页，可离线打开</div>
</div>
<script src="data.js"></script>
<script>
const D = window.DASH_DATA;
document.getElementById('genAt').textContent = '生成于 ' + D.generated_at.replace('T',' ').slice(0,16) + ' · 工作区 ' + D.workspace;
const ST = {complete:['✅ 完整',1],partial:['⚠️ 部分',2],unverified:['— 机判',3]};
const SCLS = {complete:'s1',partial:'s2',unverified:'s3'};

// stats
const t = D.totals;
document.getElementById('stats').innerHTML = [
  ['挑战', t.challenges],['学生', t.students],['提交组', t.submission_groups],['文件', t.files],
  ['✅ 完整', t.complete],['⚠️ 部分', t.partial],['— 无法机判', t.unverified],
  ['缺 AI 日志', t.missing_ai_log],['命名违规', t.naming_violations]
].map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');

// filters
const selS = document.getElementById('fStudent'), selC = document.getElementById('fChallenge');
D.students.forEach(s=>selS.add(new Option(s,s)));
D.by_challenge.forEach(c=>selC.add(new Option(c.challenge+' '+c.title.slice(0,18), c.challenge)));
let stFilter='';
document.querySelectorAll('.chip').forEach(ch=>ch.addEventListener('click',()=>{
  document.querySelectorAll('.chip').forEach(x=>x.classList.remove('on'));
  ch.classList.add('on'); stFilter=ch.dataset.st; renderMatrix(); renderTimeline();
}));
selS.addEventListener('change',()=>{renderMatrix();renderTimeline();});
selC.addEventListener('change',()=>{renderMatrix();renderTimeline();});

const grid={}; D.submissions.forEach(s=>grid[s.student+'|'+s.challenge]=s);

function renderMatrix(){
  const codes=D.by_challenge.map(c=>c.challenge);
  const stus=D.students.filter(s=>!selS.value||s===selS.value);
  const cs=codes.filter(c=>!selC.value||c===selC.value);
  let h='<tr><th style="text-align:left">学生 \\ 挑战</th>'+cs.map(c=>'<th>'+c+'</th>').join('')+'</tr>';
  stus.forEach(stu=>{
    h+='<tr><td class="rowhead">'+stu+'</td>';
    cs.forEach(c=>{
      const s=grid[stu+'|'+c];
      if(!s){h+='<td class="s0" title="未提交"></td>';return;}
      if(stFilter&&s.status!==stFilter){h+='<td class="s0" style="opacity:.35"></td>';return;}
      const cls=SCLS[s.status]+(s.has_ai_log?'':' hot');
      h+=`<td class="${cls}" data-k="${stu}|${c}" title="${s.challenge_title}\n${ST[s.status][0]} · ${s.file_count} 个文件${s.has_ai_log?'':'\n❌ 缺 AI 日志'}">${s.file_count}</td>`;
    });
    h+='</tr>';
  });
  document.getElementById('matrix').innerHTML=h;
  document.querySelectorAll('#matrix td[data-k]').forEach(td=>
    td.addEventListener('click',()=>showDetail(td.dataset.k)));
}

function showDetail(k){
  const s=grid[k]; if(!s)return;
  const box=document.getElementById('detail');
  const stTag = s.status==='complete'?'<span class="tag ok">交付物齐全</span>'
    : s.status==='partial'?'<span class="tag warn">部分提交 · 缺 '+s.missing_required.length+' 项</span>'
    : '<span class="tag gray">challenge.json 未定义交付物，无法机判</span>';
  box.style.display='block';
  box.innerHTML=`
    <h3>${s.student} · ${s.challenge} <span class="muted">${s.challenge_title}</span></h3>
    <div class="row">${stTag}
      ${s.has_ai_log?'<span class="tag ok">AI 日志 ✓</span>':'<span class="tag bad">缺 AI 日志</span>'}
      <span class="tag ${s.naming_ok?'ok':'warn'}">${s.naming_ok?'命名规范 ✓':'命名违规 '+s.naming_violations.length+' 个'}</span>
      ${s.empty_files.length?'<span class="tag bad">空文件 '+s.empty_files.length+'</span>':''}
      <span class="tag gray">最后提交 ${s.last_submit}</span>
    </div>
    ${s.missing_required.length?`<div class="row"><b>缺必填：</b>${s.missing_required.map(m=>'<span class="tag bad">'+m+'</span>').join(' ')}</div>`:''}
    ${s.naming_violations.length?`<div class="row"><b>命名违规：</b>${s.naming_violations.map(m=>'<span class="tag warn">'+m+'</span>').join(' ')}</div>`:''}
    <div class="row muted">交付物要求（来自 challenge.json）：${(D.challenges[s.challenge]&&D.challenges[s.challenge].deliverable_patterns.join('；'))||'未定义'}</div>
    <ul class="files">${s.files_rel.map(f=>`<li><a href="../${encodeURI(f.rel)}" target="_blank">${f.name}</a><span class="muted">${f.cat}</span></li>`).join('')}</ul>`;
  box.scrollIntoView({behavior:'smooth',block:'nearest'});
}

function renderTimeline(){
  const rows=D.submissions.filter(s=>
    (!selS.value||s.student===selS.value)&&(!selC.value||s.challenge===selC.value)&&(!stFilter||s.status===stFilter))
    .sort((a,b)=>b.last_submit.localeCompare(a.last_submit));
  document.getElementById('timeline').innerHTML=rows.map(s=>
    `<div class="tl"><span class="t">${s.last_submit}</span><span class="who">${s.student}</span>
     <span class="tag ${SCLS[s.status]}">${ST[s.status][0]}</span>
     <span><b>${s.challenge}</b> · ${s.challenge_title}</span>
     <span class="muted">${s.file_count} 个文件 · ${s.folder}</span></div>`).join('')||'<div class="muted">无记录</div>';
}
renderMatrix(); renderTimeline();
</script></body></html>
"""


def main() -> int:
    OUT.mkdir(exist_ok=True)
    summary = json.loads((DATA / "summary.json").read_text(encoding="utf-8"))
    submissions = json.loads((DATA / "submissions.json").read_text(encoding="utf-8"))
    challenges = json.loads((DATA / "challenges.json").read_text(encoding="utf-8"))

    for s in submissions:
        s["files_rel"] = []  # 由文件级记录重建（含分类与相对链接）
    # 重新扫描一遍文件级明细，把分类与相对路径带进组里
    import sys
    sys.path.insert(0, str(HERE))
    from scan_submissions import iter_submit_dirs, scan, WORKSPACE  # noqa: E402

    cat_of, rel_of = {}, {}
    for d in iter_submit_dirs():
        for r in scan(d, challenges):
            cat_of[(r["student"], r["challenge"], r["file"])] = r["category"]
            rel_of[(r["student"], r["challenge"], r["file"])] = r["rel_path"]
    for s in submissions:
        s["files_rel"] = [
            {"name": f, "cat": cat_of.get((s["student"], s["challenge"], f), "其他"),
             "rel": rel_of.get((s["student"], s["challenge"], f), "")}
            for f in s["files"]
        ]

    payload = {
        "generated_at": summary["generated_at"],
        "workspace": summary["workspace"],
        "totals": summary["totals"],
        "students": summary["students"],
        "by_challenge": summary["by_challenge"],
        "challenges": challenges,
        "submissions": submissions,
    }
    (OUT / "data.js").write_text(
        "window.DASH_DATA = " + json.dumps(payload, ensure_ascii=False) + ";", encoding="utf-8"
    )
    (OUT / "index.html").write_text(HTML, encoding="utf-8")
    print(f"已生成 {OUT / 'index.html'}（双击即可打开，无需服务器）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
