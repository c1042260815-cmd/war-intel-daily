#!/usr/bin/env python3
"""
美以伊战争情报日报 — 推送脚本
支持企业微信 Webhook 推送精简版日报 + 航运数据摘要
"""

import requests
import json
import os
import sys
import io
from pathlib import Path
from datetime import datetime

# Windows GBK 终端兼容
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# ============ 配置 ============

# 企业微信 Webhook 地址
WEWORK_WEBHOOK_URL = os.environ.get(
    "WEWORK_WEBHOOK_URL",
    "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=23e69792-b8d9-4c5f-85f8-aedd4d643379"
)

# 飞书 Webhook 地址（可选）
FEISHU_WEBHOOK_URL = os.environ.get("FEISHU_WEBHOOK_URL", "")

# 日报目录
REPORTS_DIR = Path(__file__).parent / "reports"


# ============ 企微推送 ============

def push_to_wework(markdown_text: str) -> bool:
    """推送 Markdown 精简版到企业微信群"""
    if not WEWORK_WEBHOOK_URL:
        print("⚠️ 未配置 WEWORK_WEBHOOK_URL 环境变量，跳过企微推送")
        return False

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": markdown_text
        }
    }

    try:
        resp = requests.post(
            WEWORK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        result = resp.json()
        if result.get("errcode") == 0:
            print("✅ 企微推送成功")
            return True
        else:
            print(f"❌ 企微推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 企微推送异常: {e}")
        return False


def push_to_wework_text(text: str) -> bool:
    """推送纯文本到企业微信群（支持更长内容）"""
    if not WEWORK_WEBHOOK_URL:
        return False

    payload = {
        "msgtype": "text",
        "text": {
            "content": text
        }
    }

    try:
        resp = requests.post(
            WEWORK_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        result = resp.json()
        if result.get("errcode") == 0:
            print("✅ 企微文本推送成功")
            return True
        else:
            print(f"❌ 企微文本推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 企微文本推送异常: {e}")
        return False


# ============ 飞书推送 ============

def push_to_feishu(markdown_text: str) -> bool:
    """推送 Markdown 精简版到飞书群"""
    if not FEISHU_WEBHOOK_URL:
        print("⚠️ 未配置 FEISHU_WEBHOOK_URL 环境变量，跳过飞书推送")
        return False

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "美以伊战争情报日报"},
                "template": "red"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": markdown_text
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }
                    ]
                }
            ]
        }
    }

    try:
        resp = requests.post(
            FEISHU_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        result = resp.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print("✅ 飞书推送成功")
            return True
        else:
            print(f"❌ 飞书推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 飞书推送异常: {e}")
        return False


# ============ 字节检查与分段 ============

def check_byte_limit(text: str, limit: int = 4096) -> bool:
    """检查文本是否在企微消息字节数限制内"""
    byte_count = len(text.encode('utf-8'))
    if byte_count <= limit:
        print(f"✅ 字节检查通过: {byte_count}/{limit} bytes")
        return True
    else:
        print(f"❌ 字节超出限制: {byte_count}/{limit} bytes (超 {byte_count - limit} bytes)")
        return False


def split_for_wework(text: str, limit: int = 4096):
    """将长文本按字节限制分段（避免在UTF-8多字节字符中间截断）"""
    segments = []
    while text:
        if len(text.encode('utf-8')) <= limit:
            segments.append(text)
            break
        # 找到不超过限制的最大安全截断点
        cut_pos = 0
        for i in range(min(len(text), limit), 0, -1):
            if len(text[:i].encode('utf-8')) <= limit:
                cut_pos = i
                break
        segments.append(text[:cut_pos])
        text = text[cut_pos:]
    return segments


# ============ 主入口 ============

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    summary_file = REPORTS_DIR / f"{today}-summary.md"

    # ---- 第一条消息：战争情报日报 ----
    if summary_file.exists():
        with open(summary_file, "r", encoding="utf-8") as f:
            content = f.read()

        if not check_byte_limit(content):
            # 超限则分段发送
            segments = split_for_wework(content)
            for i, seg in enumerate(segments):
                print(f"\n📨 推送日报第 {i+1}/{len(segments)} 段: {today}")
                push_to_wework(seg)
        else:
            print(f"\n📨 推送日报: {today}")
            push_to_wework(content)
    else:
        print(f"⚠️ 未找到今日摘要文件: {summary_file}，跳过日报推送")

    # ---- 第二条消息：霍尔木兹海峡航运摘要 ----
    shipping_summary = (
        f"⚓ **霍尔木兹海峡航运日报 | {today}**\n\n"
        f"> 战前日均: **~138艘** → 今日: **~{4}艘** (暴跌96.6%)\n\n"
        f"**3月累计通行: ~142艘** (正常水平应达4140艘)\n"
        f"**被困船只: ~2000艘 | 船员: ~20000人**\n\n"
        f"📊 通航船只中 **67%** 与伊朗直接关联\n"
        f"石油运输: ~100万桶/天 (正常2000万桶/天)\n\n"
        f"⚠️ 海峡状态: 管控通行（伊朗付费通行+护航制度）\n"
        f"📉 3月14日首次归零 | 运价涨至4倍 | 三大船司暂停订舱\n\n"
        f"🔗 完整数据: [航运追踪报告](本地reports目录)"
    )

    # 延迟发送第二条消息
    import time
    time.sleep(2)

    if check_byte_limit(shipping_summary):
        push_to_wework(shipping_summary)
    else:
        push_to_wework_text(shipping_summary)

    print("\n✅ 推送流程完成")


if __name__ == "__main__":
    main()
