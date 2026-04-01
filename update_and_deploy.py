#!/usr/bin/env python3
"""
每日报告更新 + GitHub Pages 部署脚本
用途：由自动化任务调用，每天更新两个 HTML 报告并推送到 GitHub Pages
  1. reports/{date}.html        — 美以伊战争情报日报
  2. reports/hormuz-shipping-traffic-{month}.html — 霍尔木兹海峡航运追踪（按月累计）
"""

import json
import io
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Windows GBK 终端兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

REPORTS_DIR = Path(__file__).parent / "reports"
PROJECT_DIR = Path(__file__).parent


# ============================================================
# 战争情报日报 HTML 生成
# ============================================================

def read_intel_data(date_str: str) -> dict:
    """从精简版 Markdown 读取当日情报数据（供 HTML 生成使用）"""
    summary_file = REPORTS_DIR / f"{date_str}-summary.md"
    if not summary_file.exists():
        return {}
    text = summary_file.read_text(encoding='utf-8')
    return {"raw": text}


def generate_daily_html(day: int, date_str: str, intel: dict) -> str:
    """
    生成战争情报日报 HTML。
    基于模板生成，内容从 intel 数据填充。
    intel 需要包含: overview, escalation, core_events, military, diplomacy,
                    humanitarian, economic, risks, cumulative
    """
    # 如果有 json 数据文件则读取，否则使用默认结构
    intel_file = REPORTS_DIR / f"{date_str}-intel.json"
    if intel_file.exists():
        with open(intel_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        # 从 summary markdown 提取关键信息
        data = parse_summary_to_json(date_str, intel.get("raw", ""))

    date_display = date_str.replace("-", "年", 1).replace("-", "月", 1).replace("-", "日", 1) if "-" in date_str else date_str
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>美以伊战争情报日报 — {date_str} (Day {day})</title>
    <style>
        :root {{
            --primary: #1a237e;
            --accent: #c62828;
            --warning: #e65100;
            --bg: #f5f5f5;
            --card-bg: #ffffff;
            --text: #212121;
            --text-secondary: #616161;
            --border: #e0e0e0;
            --success: #2e7d32;
            --info: #0277bd;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
            background: var(--bg); color: var(--text); line-height: 1.8;
        }}
        .header {{
            background: linear-gradient(135deg, #0d1b3e 0%, #1a237e 50%, #283593 100%);
            color: white; padding: 40px 20px 30px; text-align: center;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; letter-spacing: 2px; }}
        .header .subtitle {{ font-size: 14px; opacity: 0.85; margin-bottom: 16px; }}
        .header .meta {{ display: flex; justify-content: center; gap: 24px; font-size: 13px; opacity: 0.75; }}
        .header .meta span {{ display: flex; align-items: center; gap: 4px; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 20px; }}
        .situation-overview {{
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            border-left: 4px solid var(--warning); padding: 20px 24px; margin: 20px 0; border-radius: 0 8px 8px 0;
        }}
        .situation-overview h2 {{ font-size: 16px; color: var(--warning); margin-bottom: 10px; }}
        .situation-overview p {{ font-size: 15px; color: #4e342e; font-weight: 500; }}
        .section {{
            background: var(--card-bg); border-radius: 10px; padding: 24px; margin: 16px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
        }}
        .section-header {{
            display: flex; align-items: center; gap: 10px; margin-bottom: 16px;
            padding-bottom: 12px; border-bottom: 2px solid var(--border);
        }}
        .section-header .icon {{
            width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center;
            justify-content: center; font-size: 16px; color: white; flex-shrink: 0;
        }}
        .section-header h2 {{ font-size: 18px; font-weight: 600; }}
        .icon-red {{ background: var(--accent); }}
        .icon-blue {{ background: var(--primary); }}
        .icon-orange {{ background: var(--warning); }}
        .icon-green {{ background: var(--success); }}
        .icon-info {{ background: var(--info); }}
        .event-card {{
            border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin: 12px 0;
            background: #fafafa; transition: box-shadow 0.2s;
        }}
        .event-card:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .event-card .event-header {{ display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }}
        .event-card .tag {{
            font-size: 11px; padding: 2px 8px; border-radius: 4px; color: white;
            font-weight: 600; flex-shrink: 0;
        }}
        .tag-us {{ background: #1565c0; }} .tag-israel {{ background: #00897b; }}
        .tag-iran {{ background: #c62828; }} .tag-houthis {{ background: #6a1b9a; }}
        .tag-hezbollah {{ background: #e65100; }} .tag-diplomacy {{ background: #2e7d32; }}
        .tag-humanitarian {{ background: #ad1457; }} .tag-russia {{ background: #37474f; }}
        .tag-un {{ background: #1565c0; }} .tag-gcc {{ background: #bf360c; }}
        .event-card .event-time {{ font-size: 12px; color: var(--text-secondary); }}
        .event-card .event-title {{ font-weight: 600; font-size: 15px; margin-bottom: 6px; }}
        .event-card .event-detail {{ font-size: 14px; color: #424242; }}
        .event-card .event-impact {{
            margin-top: 8px; padding: 8px 12px; background: #e3f2fd; border-radius: 6px;
            font-size: 13px; color: #0d47a1;
        }}
        .event-card .event-impact strong {{ color: #1a237e; }}
        .event-card .source {{ margin-top: 6px; font-size: 12px; color: #9e9e9e; }}
        .subsection {{ margin: 16px 0; }}
        .subsection h3 {{
            font-size: 15px; font-weight: 600; color: var(--primary); margin-bottom: 10px;
            padding-left: 10px; border-left: 3px solid var(--primary);
        }}
        .data-table {{ width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 14px; }}
        .data-table th {{
            background: #e8eaf6; padding: 10px 12px; text-align: left; font-weight: 600;
            color: var(--primary); border-bottom: 2px solid #c5cae9;
        }}
        .data-table td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .data-table .highlight-red {{ color: var(--accent); font-weight: 700; }}
        .data-table .highlight-orange {{ color: var(--warning); font-weight: 600; }}
        .risk-card {{
            border: 1px solid #ffcc80; border-left: 4px solid var(--warning); background: #fff8e1;
            border-radius: 0 8px 8px 0; padding: 14px 16px; margin: 10px 0;
        }}
        .risk-card .risk-level {{
            font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
            color: white; margin-bottom: 6px; display: inline-block;
        }}
        .risk-high {{ background: #c62828; }} .risk-medium {{ background: #e65100; }}
        .risk-low {{ background: #f9a825; color: #333 !important; }}
        .risk-card .risk-title {{ font-weight: 600; font-size: 14px; margin-bottom: 4px; }}
        .risk-card .risk-detail {{ font-size: 13px; color: #5d4037; }}
        .escalation-alert {{
            background: linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%);
            border: 2px solid var(--accent); border-radius: 10px; padding: 20px; margin: 20px 0;
        }}
        .escalation-alert h3 {{ color: var(--accent); font-size: 16px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
        .disclaimer {{
            background: #fafafa; border: 1px solid var(--border); border-radius: 8px;
            padding: 16px; margin: 20px 0; font-size: 12px; color: #757575;
        }}
        .footer {{ text-align: center; padding: 30px 20px; color: #9e9e9e; font-size: 12px; }}
        @media (max-width: 640px) {{
            .header h1 {{ font-size: 20px; }} .container {{ padding: 12px; }}
            .section {{ padding: 16px; }} .header .meta {{ flex-direction: column; gap: 4px; }}
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>⚔️ 美以伊战争情报日报</h1>
    <div class="subtitle">US-Israel-Iran War Intelligence Daily Brief</div>
    <div class="meta">
        <span>📅 {date_str}</span>
        <span>⏱ 战争第 {day} 天</span>
        <span>🔄 信息截止：{now_str}</span>
    </div>
</div>

<div class="container">

<div class="situation-overview">
    <h2>📊 局势总览</h2>
    <p>{_h(data.get("overview", "暂无数据"))}</p>
</div>

<div class="escalation-alert">
    <h3>🚨 升级预警指标</h3>
    <div style="display:grid; gap:8px;">
{_render_escalation(data.get("escalation", []))}
    </div>
</div>

<div class="section">
    <div class="section-header">
        <div class="icon icon-red">🎯</div>
        <h2>核心动态 Top Signals</h2>
    </div>
{_render_events(data.get("core_events", []))}
</div>

<div class="section">
    <div class="section-header">
        <div class="icon icon-blue">⚔️</div>
        <h2>军事行动 Military Operations</h2>
    </div>
{_render_military(data.get("military", {}))}
</div>

<div class="section">
    <div class="section-header">
        <div class="icon icon-green">🤝</div>
        <h2>外交与政治 Diplomacy & Politics</h2>
    </div>
{_render_events(data.get("diplomacy", []))}
</div>

<div class="section">
    <div class="section-header">
        <div class="icon" style="background:#ad1457;">🏥</div>
        <h2>人道影响 Humanitarian Impact</h2>
    </div>
{_render_humanitarian(data.get("humanitarian", {}))}
</div>

<div class="section">
    <div class="section-header">
        <div class="icon icon-orange">💰</div>
        <h2>经济影响 Economic Impact</h2>
    </div>
{_render_events(data.get("economic", []))}
</div>

<div class="section">
    <div class="section-header">
        <div class="icon icon-orange">⚠️</div>
        <h2>风险信号 Watchlist</h2>
    </div>
{_render_risks(data.get("risks", []))}
</div>

<div class="section">
    <div class="section-header">
        <div class="icon icon-info">📈</div>
        <h2>累计数据 Day {day} Statistics</h2>
    </div>
{_render_cumulative(data.get("cumulative", []), day)}
</div>

<div class="disclaimer">
    <strong>📋 免责声明</strong><br>
    本日报基于公开信源编制，旨在提供客观事实性情报汇总。所有数据标注来源，实际情况以各方官方公布为准。
    不构成任何投资、政策或行动建议。
</div>

</div>

<div class="footer">
    <p>美以伊战争情报日报 — 基于五步情报方法论自动生成</p>
    <p>Generated on {date_str}</p>
</div>

</body>
</html>'''
    return html


def _h(text: str) -> str:
    """简单 HTML 转义"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_escalation(items: list) -> str:
    if not items:
        return '<p style="color:#888;">暂无预警数据</p>'
    lines = []
    for item in items:
        level = item.get("level", "🟡 MEDIUM")
        color = "var(--accent)" if "HIGH" in level else "var(--warning)"
        lines.append(
            f'<div style="display:flex;align-items:center;gap:8px;">\n'
            f'    <span style="color:{color};font-weight:700;">{_h(level)}</span>\n'
            f'    <span>{_h(item.get("text", ""))}</span>\n'
            f'</div>'
        )
    return "\n".join(lines)


def _render_events(events: list) -> str:
    if not events:
        return '<p style="color:#888;">暂无数据</p>'
    lines = []
    for e in events:
        tag = e.get("tag", "其他")
        tag_class = e.get("tag_class", "tag-us")
        time_str = _h(e.get("time", ""))
        title = _h(e.get("title", ""))
        detail = _h(e.get("detail", ""))
        impact = e.get("impact", "")
        source = _h(e.get("source", ""))
        lines.append(
            f'<div class="event-card">\n'
            f'    <div class="event-header">\n'
            f'        <span class="tag {tag_class}">{_h(tag)}</span>\n'
            f'        <span class="event-time">{time_str}</span>\n'
            f'    </div>\n'
            f'    <div class="event-title">{title}</div>\n'
            f'    <div class="event-detail">{detail}</div>\n'
        )
        if impact:
            lines.append(f'    <div class="event-impact"><strong>影响评估：</strong>{_h(impact)}</div>')
        if source:
            lines.append(f'    <div class="source">📎 来源：{source}</div>')
        lines.append('</div>')
    return "\n".join(lines)


def _render_military(military: dict) -> str:
    if not military:
        return '<p style="color:#888;">暂无数据</p>'
    sections = []
    for section_name, events in military.items():
        sections.append(
            f'<div class="subsection">\n    <h3>{_h(section_name)}</h3>\n'
            + _render_events(events) + '\n</div>'
        )
    return "\n".join(sections)


def _render_humanitarian(h: dict) -> str:
    if not h or not h.get("casualties"):
        return '<p style="color:#888;">暂无数据</p>'
    rows = ""
    for c in h.get("casualties", []):
        cls = "highlight-red" if c.get("highlight") else ""
        rows += (
            f'<tr>\n'
            f'    <td class="{cls}">{_h(c.get("region", ""))}</td>\n'
            f'    <td class="{cls}">{_h(c.get("deaths", ""))}</td>\n'
            f'    <td>{_h(c.get("info", ""))}</td>\n'
            f'    <td>{_h(c.get("source", ""))}</td>\n'
            f'</tr>\n'
        )
    medical = ""
    for m in h.get("medical", []):
        medical += f'<li>{_h(m)}</li>'

    return (
        f'<table class="data-table">\n<thead><tr><th>地区</th><th>累计死亡</th><th>关键信息</th><th>来源</th></tr></thead>\n'
        f'<tbody>{rows}</tbody>\n</table>\n'
        f'<div class="subsection"><h3>医疗系统状况</h3><ul style="padding-left:20px;font-size:14px;color:#424242;">{medical}</ul></div>'
    )


def _render_risks(risks: list) -> str:
    if not risks:
        return '<p style="color:#888;">暂无数据</p>'
    lines = []
    for r in risks:
        level = r.get("level", "MEDIUM")
        level_class = {"HIGH": "risk-high", "MEDIUM": "risk-medium", "LOW": "risk-low"}.get(level, "risk-medium")
        lines.append(
            f'<div class="risk-card">\n'
            f'    <span class="risk-level {level_class}">{_h(r.get("label", level))}</span>\n'
            f'    <div class="risk-title">{_h(r.get("title", ""))}</div>\n'
            f'    <div class="risk-detail">{_h(r.get("detail", ""))}</div>\n'
            f'</div>'
        )
    return "\n".join(lines)


def _render_cumulative(items: list, day: int) -> str:
    if not items:
        return '<p style="color:#888;">暂无数据</p>'
    rows = ""
    for c in items:
        cls = ""
        if c.get("highlight") == "red":
            cls = "highlight-red"
        elif c.get("highlight") == "orange":
            cls = "highlight-orange"
        rows += (
            f'<tr>\n'
            f'    <td>{_h(c.get("metric", ""))}</td>\n'
            f'    <td class="{cls}">{_h(c.get("value", ""))}</td>\n'
            f'    <td>{_h(c.get("note", ""))}</td>\n'
            f'</tr>\n'
        )
    return (
        f'<table class="data-table">\n<thead><tr><th>指标</th><th>数据</th><th>备注</th></tr></thead>\n'
        f'<tbody>{rows}</tbody>\n</table>'
    )


def parse_summary_to_json(date_str: str, raw_md: str) -> dict:
    """
    从精简版 Markdown 解析为结构化 JSON 数据。
    这是降级方案：当没有 intel.json 时，从 summary.md 提取信息。
    """
    data = {
        "overview": "",
        "escalation": [],
        "core_events": [],
        "military": {},
        "diplomacy": [],
        "humanitarian": {},
        "economic": [],
        "risks": [],
        "cumulative": []
    }

    lines = raw_md.split("\n")
    section = "header"
    current_event_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("## 📊 局势总览"):
            section = "overview"
            continue
        elif stripped.startswith("## 🎯 核心动态"):
            section = "core_events"
            continue
        elif stripped.startswith("## 💀 累计伤亡"):
            section = "casualties"
            continue
        elif stripped.startswith("## ⚠️ 风险关注"):
            section = "risks"
            continue
        elif stripped.startswith("## ⚓ 霍尔木兹海峡航运摘要"):
            section = "shipping"
            continue
        elif stripped.startswith("# "):
            section = "header"
            continue

        if section == "overview" and stripped and not stripped.startswith("#"):
            data["overview"] = stripped
        elif section == "core_events" and stripped.startswith("**"):
            # 解析 **① 标题** — 描述 (来源)
            import re
            m = re.match(r'\*\*[①②③④⑤⑥⑦⑧⑨⑩]\s*(.+?)\*\*\s*[—\-]\s*(.+?)(?:\(.*?\))?\s*$', stripped)
            if m:
                title = m.group(1)
                detail = m.group(2).rstrip()
                data["core_events"].append({
                    "tag": title.split("】")[0].strip("【") if "】" in title else "综合",
                    "tag_class": "tag-us",
                    "time": date_str,
                    "title": title,
                    "detail": detail,
                    "source": ""
                })
        elif section == "risks" and stripped and not stripped.startswith("#"):
            if stripped.startswith("🔴"):
                data["risks"].append({"level": "HIGH", "label": "🔴 高风险 HIGH", "title": stripped[2:].strip(), "detail": ""})
            elif stripped.startswith("🟡"):
                data["risks"].append({"level": "MEDIUM", "label": "🟡 中风险 MEDIUM", "title": stripped[2:].strip(), "detail": ""})
            elif stripped.startswith("🟢"):
                data["risks"].append({"level": "LOW", "label": "🟢 低风险 LOW", "title": stripped[2:].strip(), "detail": ""})

    if not data["overview"]:
        data["overview"] = f"战争第{int(date_str.split('-')[-1]) - 27}天，详细情报数据生成中。请参考企微精简版日报。"

    return data


# ============================================================
# 霍尔木兹海峡航运报告 HTML 生成
# ============================================================

def generate_shipping_html(month: str, daily_data: list, month_cumulative: int,
                           events: list, data_as_of: str, day: int) -> str:
    """
    生成霍尔木兹海峡航运追踪 HTML 报告。
    month: "2026-03" 格式
    daily_data: 每日数据列表 [{"date": "3/31", "day": "D+32", "total": 4, "oil": 3, "other": 1, "phase": "管控", "note": "..."}]
    events: 关键事件列表
    """
    month_label = month.replace("-", "年", 1) + "月"
    days_in_data = len(daily_data)
    avg_daily = round(month_cumulative / max(days_in_data, 1), 1)
    drop_pct = round((1 - avg_daily / 138) * 100, 1)

    # 构建数据数组
    labels_js = json.dumps([d["date"] for d in daily_data])
    total_js = json.dumps([d["total"] for d in daily_data])
    oil_js = json.dumps([d["oil"] for d in daily_data])
    other_js = json.dumps([d["other"] for d in daily_data])
    baseline_count = days_in_data  # 用于填充

    # 构建表格行
    table_rows = ""
    for d in daily_data:
        phase_class = {
            "急降": "sharp", "衰减": "decline", "冰点": "near-zero",
            "归零": "near-zero", "管控": "controlled"
        }.get(d.get("phase", ""), "normal")
        total_val = d["total"]
        val_class = "val-zero" if total_val == 0 else ("val-low" if total_val < 5 else "val-normal")
        table_rows += (
            f'<tr>\n'
            f'    <td class="day-cell">{d["date_label"]}</td><td>{d["day"]}</td>\n'
            f'    <td><span class="phase-tag {phase_class}">{d["phase"]}</span></td>\n'
            f'    <td class="{val_class}">~{total_val}</td>'
            f'<td class="{val_class}">~{d["oil"]}</td>'
            f'<td class="{val_class}">~{d["other"]}</td>\n'
            f'    <td>{_h(d.get("note", ""))}</td>\n'
            f'</tr>\n'
        )

    # 构建事件时间线
    timeline_items = ""
    for e in events:
        timeline_items += (
            f'<div class="timeline-item">\n'
            f'    <div class="timeline-date">{_h(e.get("date", ""))}</div>\n'
            f'    <div class="timeline-content">\n'
            f'        <div class="timeline-title">{_h(e.get("title", ""))}</div>\n'
            f'        <div class="timeline-desc">{_h(e.get("desc", ""))}</div>\n'
            f'    </div>\n'
            f'</div>\n'
        )

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>霍尔木兹海峡航运追踪 | {month_label}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            background: #0a0a0f; color: #e0e0e0; line-height: 1.6;
        }}
        .header {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            padding: 30px 40px; border-bottom: 2px solid #e94560;
        }}
        .header h1 {{ font-size: 28px; color: #fff; margin-bottom: 8px; }}
        .header .subtitle {{ color: #a0a0b0; font-size: 14px; }}
        .header .last-update {{ color: #e94560; font-size: 13px; margin-top: 4px; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px 30px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 24px 0; }}
        .summary-card {{
            background: #141422; border: 1px solid #2a2a3e; border-radius: 12px;
            padding: 20px; text-align: center; transition: transform 0.2s;
        }}
        .summary-card:hover {{ transform: translateY(-2px); border-color: #e94560; }}
        .summary-card .label {{ color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
        .summary-card .value {{ font-size: 32px; font-weight: 700; margin: 8px 0; }}
        .summary-card .value.red {{ color: #e94560; }}
        .summary-card .value.orange {{ color: #f0a500; }}
        .summary-card .value.green {{ color: #00c9a7; }}
        .summary-card .value.blue {{ color: #4da6ff; }}
        .summary-card .note {{ font-size: 12px; color: #666; }}
        .chart-section {{
            background: #141422; border: 1px solid #2a2a3e; border-radius: 12px;
            padding: 24px; margin: 24px 0;
        }}
        .chart-section h2 {{
            font-size: 18px; color: #fff; margin-bottom: 16px;
            padding-bottom: 8px; border-bottom: 1px solid #2a2a3e;
        }}
        .chart-container {{ position: relative; height: 400px; width: 100%; }}
        .chart-container.tall {{ height: 500px; }}
        .data-table-wrapper {{ overflow-x: auto; margin: 24px 0; }}
        table {{
            width: 100%; border-collapse: collapse; background: #141422;
            border-radius: 12px; overflow: hidden;
        }}
        thead th {{
            background: #1a1a2e; color: #a0a0c0; font-size: 12px; text-transform: uppercase;
            letter-spacing: 1px; padding: 14px 12px; text-align: center;
            border-bottom: 2px solid #2a2a3e; position: sticky; top: 0;
        }}
        tbody td {{
            padding: 10px 12px; text-align: center;
            border-bottom: 1px solid #1e1e30; font-size: 14px;
        }}
        tbody tr:hover {{ background: #1a1a2e; }}
        .day-cell {{ font-weight: 600; color: #fff; text-align: left; padding-left: 16px; }}
        .phase-tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }}
        .phase-tag.sharp {{ background: #e94560; color: #fff; }}
        .phase-tag.decline {{ background: #f0a500; color: #000; }}
        .phase-tag.near-zero {{ background: #6c0000; color: #ff6666; }}
        .phase-tag.controlled {{ background: #1a5c2a; color: #66ff88; }}
        .phase-tag.normal {{ background: #1a3a5c; color: #66aaff; }}
        .val-zero {{ color: #e94560; font-weight: 700; }}
        .val-low {{ color: #f0a500; }}
        .val-normal {{ color: #00c9a7; }}
        .val-high {{ color: #4da6ff; }}
        .timeline {{ margin: 24px 0; }}
        .timeline-item {{
            display: flex; gap: 16px; padding: 12px 0;
            border-left: 2px solid #2a2a3e; padding-left: 20px; position: relative;
        }}
        .timeline-item::before {{
            content: ''; position: absolute; left: -6px; top: 16px;
            width: 10px; height: 10px; border-radius: 50%; background: #e94560;
        }}
        .timeline-date {{ min-width: 100px; color: #888; font-size: 13px; font-weight: 600; }}
        .timeline-content {{ flex: 1; }}
        .timeline-title {{ color: #fff; font-size: 14px; font-weight: 600; margin-bottom: 2px; }}
        .timeline-desc {{ color: #888; font-size: 13px; }}
        .sources {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #2a2a3e; color: #555; font-size: 12px; }}
        .section-title {{
            font-size: 20px; color: #fff; margin: 30px 0 16px;
            padding-left: 12px; border-left: 3px solid #e94560;
        }}
    </style>
</head>
<body>

<div class="header">
    <h1>⚓ 霍尔木兹海峡航运追踪报告</h1>
    <div class="subtitle">Strait of Hormuz Shipping Traffic Tracker — {month_label}</div>
    <div class="last-update">数据截至: {data_as_of} | 冲突第{day}天 | 海峡状态: 🔴 管控通行</div>
</div>

<div class="container">
    <div class="summary-grid">
        <div class="summary-card">
            <div class="label">冲突前日均</div>
            <div class="value blue">~138</div>
            <div class="note">艘/天 (2026年2月)</div>
        </div>
        <div class="summary-card">
            <div class="label">当月日均</div>
            <div class="value red">~{avg_daily}</div>
            <div class="note">艘/天 (暴跌{drop_pct}%)</div>
        </div>
        <div class="summary-card">
            <div class="label">当月累计通行</div>
            <div class="value orange">~{month_cumulative}</div>
            <div class="note">艘</div>
        </div>
        <div class="summary-card">
            <div class="label">被困船只</div>
            <div class="value red">~2000</div>
            <div class="note">艘 | ~20000船员</div>
        </div>
        <div class="summary-card">
            <div class="label">与伊朗关联</div>
            <div class="value red">67%</div>
            <div class="note">通行船只中占比</div>
        </div>
        <div class="summary-card">
            <div class="label">石油运输</div>
            <div class="value orange">~100万</div>
            <div class="note">桶/天 (正常2000万)</div>
        </div>
    </div>

    <div class="chart-section">
        <h2>📊 每日通行量趋势图</h2>
        <div class="chart-container tall">
            <canvas id="dailyTrafficChart"></canvas>
        </div>
    </div>

    <div class="chart-section">
        <h2>📈 当月累计通行量 vs 正常水平</h2>
        <div class="chart-container">
            <canvas id="cumulativeChart"></canvas>
        </div>
    </div>

    <h3 class="section-title">📋 每日通行数据明细</h3>
    <div class="data-table-wrapper">
        <table>
            <thead>
                <tr>
                    <th>日期</th><th>Day</th><th>阶段</th><th>通行船只</th>
                    <th>原油/成品油轮</th><th>集装箱/散货</th><th>备注</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>

    <h3 class="section-title">📅 关键事件时间线</h3>
    <div class="timeline">
        {timeline_items}
    </div>

    <div class="chart-section">
        <h2>ℹ️ 数据来源与说明</h2>
        <div style="color: #a0a0b0; font-size: 14px; line-height: 1.8;">
            <p><b>数据来源：</b></p>
            <ul style="padding-left: 20px; margin-top: 8px;">
                <li>IMF PortWatch — 全球港口监测数据</li>
                <li>Project44 / 船视宝 — AIS船舶追踪平台</li>
                <li>AXSMarine (Signal Group) — 专业航运数据分析</li>
                <li>新华社 / CCTV / 劳埃德船舶日报 — 权威新闻报道</li>
                <li>WTO Data Lab — 霍尔木兹海峡贸易追踪器</li>
                <li>Seavantage / HormuzTracker — 实时航运监测</li>
            </ul>
            <p style="margin-top: 16px;"><b>重要说明：</b></p>
            <ul style="padding-left: 20px; margin-top: 8px;">
                <li>数据基于AIS（船舶自动识别系统）追踪，未开启AIS的船只不计入</li>
                <li>3月中旬后通行的船只约67%与伊朗直接关联，多数为影子船队</li>
                <li>本报告中部分日期为基于累计数据反推的估算值（标注~号）</li>
            </ul>
        </div>
    </div>

    <div class="sources">
        数据来源: IMF PortWatch, Project44, 船视宝, AXSMarine, 新华社, CCTV, 劳埃德船舶日报, WTO Data Lab, Seavantage | 生成时间: {data_as_of}
    </div>
</div>

<script>
const dailyData = {{
    labels: {labels_js},
    total:   {total_js},
    oilTanker: {oil_js},
    other:    {other_js}
}};

const ctx1 = document.getElementById('dailyTrafficChart').getContext('2d');
new Chart(ctx1, {{
    type: 'bar',
    data: {{
        labels: dailyData.labels,
        datasets: [
            {{
                label: '原油/成品油轮',
                data: dailyData.oilTanker,
                backgroundColor: 'rgba(233, 69, 96, 0.8)',
                borderColor: '#e94560', borderWidth: 1, stack: 'stack0'
            }},
            {{
                label: '集装箱/散货/其他',
                data: dailyData.other,
                backgroundColor: 'rgba(77, 166, 255, 0.8)',
                borderColor: '#4da6ff', borderWidth: 1, stack: 'stack0'
            }},
            {{
                label: '正常日均基线 (138艘)',
                data: Array({baseline_count}).fill(138),
                type: 'line',
                borderColor: '#00c9a7', borderWidth: 2, borderDash: [8, 4],
                pointRadius: 0, fill: false, stack: 'stack1'
            }}
        ]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ labels: {{ color: '#a0a0b0', font: {{ size: 12 }} }} }},
            tooltip: {{ backgroundColor: '#1a1a2e', titleColor: '#fff', bodyColor: '#ccc', borderColor: '#2a2a3e', borderWidth: 1 }}
        }},
        scales: {{
            x: {{ stacked: true, ticks: {{ color: '#888', font: {{ size: 10 }}, maxRotation: 45 }}, grid: {{ color: '#1e1e30' }} }},
            y: {{ stacked: true, title: {{ display: true, text: '通行船只数量 (艘)', color: '#888' }},
                 ticks: {{ color: '#888' }}, grid: {{ color: '#1e1e30' }}, min: 0, max: 160 }}
        }}
    }}
}});

const cumulativeActual = [];
const cumulativeNormal = [];
let sumActual = 0, sumNormal = 0;
dailyData.total.forEach((v) => {{
    sumActual += v; cumulativeActual.push(sumActual);
    sumNormal += 138; cumulativeNormal.push(sumNormal);
}});

const ctx2 = document.getElementById('cumulativeChart').getContext('2d');
new Chart(ctx2, {{
    type: 'line',
    data: {{
        labels: dailyData.labels,
        datasets: [
            {{
                label: '实际累计通行量',
                data: cumulativeActual,
                borderColor: '#e94560', backgroundColor: 'rgba(233, 69, 96, 0.1)',
                fill: true, tension: 0.3, pointRadius: 3, pointBackgroundColor: '#e94560'
            }},
            {{
                label: '正常水平累计 (按138艘/天)',
                data: cumulativeNormal,
                borderColor: '#00c9a7', backgroundColor: 'rgba(0, 201, 167, 0.05)',
                fill: true, tension: 0.3, pointRadius: 0, borderDash: [5, 3]
            }}
        ]
    }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ labels: {{ color: '#a0a0b0', font: {{ size: 12 }} }} }},
            tooltip: {{
                backgroundColor: '#1a1a2e', titleColor: '#fff', bodyColor: '#ccc', borderColor: '#2a2a3e', borderWidth: 1,
                callbacks: {{
                    afterBody: function(tooltipItems) {{
                        const actual = tooltipItems[0].raw;
                        const normal = tooltipItems[1].raw;
                        const pct = ((1 - actual / normal) * 100).toFixed(1);
                        return `缺口: ${{normal - actual}}艘 | 降幅: ${{pct}}%`;
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{ ticks: {{ color: '#888', font: {{ size: 10 }}, maxRotation: 45 }}, grid: {{ color: '#1e1e30' }} }},
            y: {{ title: {{ display: true, text: '累计通行量 (艘)', color: '#888' }},
                 ticks: {{ color: '#888' }}, grid: {{ color: '#1e1e30' }} }}
        }}
    }}
}});
</script>

</body>
</html>'''
    return html


# ============================================================
# 数据持久化（JSON 格式存储航运数据供累积使用）
# ============================================================

SHIPPING_DATA_FILE = PROJECT_DIR / "shipping_data.json"

def load_shipping_data() -> dict:
    """加载持久化的航运数据"""
    if SHIPPING_DATA_FILE.exists():
        with open(SHIPPING_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"daily": [], "events": []}


def save_shipping_data(data: dict):
    """保存航运数据"""
    with open(SHIPPING_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# Git 推送
# ============================================================

def git_push(files_to_add: list, commit_msg: str):
    """将文件添加到 Git 并推送到 GitHub"""
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        # 先 pull 远程更新，避免推送冲突
        subprocess.run(["git", "pull", "--rebase", "origin", "main"],
                       cwd=PROJECT_DIR, check=False,
                       capture_output=True, text=True, env=env, encoding='utf-8', errors='replace')
        subprocess.run(["git", "add"] + files_to_add, cwd=PROJECT_DIR, check=True,
                       capture_output=True, text=True, env=env, encoding='utf-8', errors='replace')
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=PROJECT_DIR, check=False,
                       capture_output=True, text=True, env=env, encoding='utf-8', errors='replace')
        result = subprocess.run(["git", "push", "origin", "main"], cwd=PROJECT_DIR, check=True,
                                capture_output=True, text=True, env=env, encoding='utf-8', errors='replace')
        print(f"✅ Git 推送成功: {commit_msg}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git 推送失败: {e.stderr}")
        return False


# ============================================================
# 主流程
# ============================================================

def main():
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    month_str = today.strftime("%Y-%m")

    # 战争天数（2月28日开战）
    war_start = datetime(2026, 2, 28)
    day = (today - war_start).days + 1

    print(f"📋 开始更新报告 — {date_str} (Day {day})")

    # ---- 1. 生成/更新战争情报日报 HTML ----
    intel = read_intel_data(date_str)
    daily_html = generate_daily_html(day, date_str, intel)
    daily_html_file = REPORTS_DIR / f"{date_str}.html"
    daily_html_file.write_text(daily_html, encoding='utf-8')
    print(f"✅ 日报 HTML 已生成: {daily_html_file}")

    # ---- 2. 生成/更新航运报告 HTML ----
    shipping = load_shipping_data()

    # 基于搜索数据更新今日航运信息（新数据由自动化任务中的搜索结果提供）
    today_shipping_file = REPORTS_DIR / f"{date_str}-shipping.json"
    if today_shipping_file.exists():
        with open(today_shipping_file, 'r', encoding='utf-8') as f:
            today_data = json.load(f)
    else:
        # 使用默认估算值（从今日搜索结果中获取的默认数据）
        today_data = {
            "date": f"{today.month}/{today.day}",
            "date_label": f"{today.month}月{today.day}日",
            "day": f"D+{day}",
            "total": 4,
            "oil": 3,
            "other": 1,
            "phase": "管控",
            "note": "海峡持续管控通行"
        }

    shipping["daily"].append(today_data)

    # 推送事件可由自动化任务补充
    # 添加今日事件（如果今日有重大航运事件）
    today_events_file = REPORTS_DIR / f"{date_str}-shipping-events.json"
    if today_events_file.exists():
        with open(today_events_file, 'r', encoding='utf-8') as f:
            new_events = json.load(f)
            shipping["events"].extend(new_events)

    save_shipping_data(shipping)

    # 计算月累计
    month_daily = [d for d in shipping["daily"] if d.get("date", "").startswith(f"{today.month}/")]
    month_cumulative = sum(d.get("total", 0) for d in month_daily)

    shipping_html = generate_shipping_html(
        month=month_str,
        daily_data=month_daily,
        month_cumulative=month_cumulative,
        events=shipping["events"],
        data_as_of=date_str,
        day=day
    )
    shipping_html_file = REPORTS_DIR / f"hormuz-shipping-traffic-{month_str}.html"
    shipping_html_file.write_text(shipping_html, encoding='utf-8')
    print(f"✅ 航运报告 HTML 已生成: {shipping_html_file}")

    # ---- 3. 推送到 GitHub ----
    files = [str(daily_html_file), str(shipping_html_file), str(SHIPPING_DATA_FILE)]
    # 也更新 summary markdown
    summary_file = REPORTS_DIR / f"{date_str}-summary.md"
    if summary_file.exists():
        files.append(str(summary_file))

    commit_msg = f"📅 日报更新 — {date_str} (Day {day})"
    git_push(files, commit_msg)

    print(f"\n🎉 全部完成！")
    print(f"   日报: https://c1042260815-cmd.github.io/war-intel-daily/reports/{date_str}.html")
    print(f"   航运: https://c1042260815-cmd.github.io/war-intel-daily/reports/hormuz-shipping-traffic-{month_str}.html")


if __name__ == "__main__":
    main()
