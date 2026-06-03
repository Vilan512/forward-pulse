#!/usr/bin/env python3
"""
ForwardPulse 信息源自动化收割器
RSS 智库嗅探 + X/推特模拟抓取 → 清洗融合 → 写入 raw_tweets.txt

依赖安装: pip install feedparser
"""

import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("[错误] 缺少 feedparser 库，请先执行: pip install feedparser")
    sys.exit(1)

# ════════════════════════════════════════════════════════
# 配置：RSS 数据源 (name → {url, category})
# ════════════════════════════════════════════════════════
RSS_FEEDS = {
    "MIT_Tech_AI": {
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "category": "AI",
    },
    "VentureBeat_AI": {
        "url": "https://venturebeat.com/category/ai/feed/",
        "category": "AI",
    },
    "HuggingFace": {
        "url": "https://huggingface.co/blog/feed.xml",
        "category": "AI",
    },
    "Project_Syndicate": {
        "url": "https://www.project-syndicate.org/rss",
        "category": "全球金融与地缘政治",
    },
    "McKinsey": {
        "url": "https://www.mckinsey.com/insights/rss",
        "category": "智库与趋势预测",
    },
}

# 抓取时间窗口（小时）
HOURS_WINDOW = 24


# ════════════════════════════════════════════════════════
# 模块 A：RSS 智库嗅探
# ════════════════════════════════════════════════════════
def clean_html(raw_html: str, max_len: int = 2000) -> str:
    """去除 HTML 标签，保留纯文本"""
    clean = re.sub(r'<[^>]+>', '', raw_html or '')
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean[:max_len]


def fetch_rss_feeds() -> list[dict]:
    """遍历 RSS 源，抓取最近 N 小时内的文章"""
    results = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_WINDOW)

    for name, config in RSS_FEEDS.items():
        url = config["url"]
        category = config["category"]
        print(f"[信息] 正在嗅探 {name}: {url}")
        try:
            feed = feedparser.parse(url)
            count = 0
            for entry in feed.entries:
                # 解析发布时间
                published = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                    published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                # 时间窗口过滤（无时间戳的条目也保留）
                if published and published < cutoff:
                    continue

                title = clean_html(getattr(entry, 'title', ''))

                # 逐级提取尽可能丰富的正文内容
                raw_body = ''
                # 优先取 content（全文），其次 summary，最后 description
                if hasattr(entry, 'content') and entry.content:
                    raw_body = entry.content[0].get('value', '')
                if not raw_body or len(clean_html(raw_body)) < 100:
                    raw_body = getattr(entry, 'summary', '') or getattr(entry, 'description', '')
                body = clean_html(raw_body)

                link = getattr(entry, 'link', '') or ''

                if title:
                    results.append({
                        'source': name,
                        'category': category,
                        'title': title,
                        'body': body,
                        'url': link,
                        'time': published.strftime('%Y-%m-%d %H:%M') if published else '未知时间',
                    })
                    count += 1

            print(f"[成功] 抓取 {name} {count} 条最新资讯")
        except Exception as e:
            print(f"[警告] {name} 抓取失败: {e}")

    return results


# ════════════════════════════════════════════════════════
# 模块 B：X/推特 模拟抓取
# ════════════════════════════════════════════════════════
def fetch_twitter_whitelist(accounts: list[str]) -> list[dict]:
    """
    从白名单账号抓取最新动态。

    当前为模拟数据框架。接入真实 API 时，替换下方 hardcoded 部分：
    - 方案1: X API v2 (Bearer Token) → GET /2/tweets/search/recent
    - 方案2: 第三方代理 (如 RapidAPI Twitter API)
    - 方案3: Nitter RSS 转发 (开源方案，无需 API Key)
    """
    print(f"[信息] 正在抓取 X/推特白名单 ({len(accounts)} 个账号)...")

    # ── 模拟数据（接入真实 API 后删除以下部分）──
    mock_tweets = [
        {
            'source': 'X/@sama',
            'category': 'AI',
            'title': 'Sam Altman: AGI timeline keeps accelerating',
            'summary': 'Just had a look at our latest internal benchmarks. The gap between current models and human-level reasoning on complex tasks is closing faster than any of our 2024 projections suggested. We might need to revisit what "AGI" even means before we get there.',
            'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
        },
        {
            'source': 'X/@VitalikButerin',
            'category': '全球金融与地缘政治',
            'title': 'Vitalik: Crypto needs to solve real problems or die',
            'summary': 'Spent the weekend talking to policymakers in 3 countries. The narrative that crypto is just speculation is becoming entrenched. If we dont ship killer apps for remittances, identity, and DAO governance in the next 18 months, the regulatory window slams shut permanently.',
            'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
        },
        {
            'source': 'X/@elaboratepool',
            'category': 'AI',
            'title': 'Satya Nadella: The next platform shift is embodied AI',
            'summary': 'We are entering the era where AI doesnt just generate text and images — it manipulates atoms. Robotics foundation models are where LLMs were in 2020. The companies that crack the sim-to-real transfer problem will define the next decade of manufacturing.',
            'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
        },
    ]

    print(f"[成功] 抓取 X/推特白名单 {len(mock_tweets)} 条动态")
    return mock_tweets


# ════════════════════════════════════════════════════════
# 模块 C：数据融合与导出
# ════════════════════════════════════════════════════════
def assemble_and_export(rss_data: list[dict], twitter_data: list[dict], output_path: str) -> None:
    """将多源数据格式化拼接，写入 raw_tweets.txt"""
    all_items = rss_data + twitter_data

    if not all_items:
        print("[警告] 本次收割无任何有效数据，raw_tweets.txt 未更新")
        return

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = []
    lines.append(f"# ForwardPulse 原始情报收割 — {now_str}")
    lines.append(f"# 共计 {len(all_items)} 条来自 {len(set(i['source'] for i in all_items))} 个信息源")
    lines.append("")

    for item in all_items:
        lines.append(f"[来源: {item['source']}] [分类: {item.get('category', '未分类')}] [时间: {item['time']}]")
        lines.append(f"标题: {item['title']}")
        if item.get('url'):
            lines.append(f"链接: {item['url']}")
        body = item.get('body', '') or item.get('summary', '')
        if body:
            lines.append(f"正文: {body}")
        lines.append("")

    content = '\n'.join(lines)
    out = Path(output_path)
    out.write_text(content, encoding='utf-8')

    print(f"[成功] 数据融合完成，已写入 {output_path}")
    print(f"       总计: {len(all_items)} 条")
    print(f"       RSS:  {len(rss_data)} 条")
    print(f"       X:    {len(twitter_data)} 条")


# ════════════════════════════════════════════════════════
# 主流程
# ════════════════════════════════════════════════════════
def main():
    print("=" * 50)
    print("  ForwardPulse 信息源收割器")
    print("=" * 50)

    base_dir = Path(__file__).parent
    output_path = base_dir / "raw_tweets.txt"

    # 模块 A
    rss_data = fetch_rss_feeds()

    # 模块 B（白名单账号列表，可扩展）
    whitelist = [
        "sama",
        "VitalikButerin",
        "elaboratepool",
    ]
    twitter_data = fetch_twitter_whitelist(whitelist)

    # 模块 C
    assemble_and_export(rss_data, twitter_data, str(output_path))

    print("=" * 50)
    print("  收割完成，可运行 agent_update.py 进行情报提炼")
    print("=" * 50)


if __name__ == "__main__":
    main()
