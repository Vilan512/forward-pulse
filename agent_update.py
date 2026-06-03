#!/usr/bin/env python3
"""
ForwardPulse 自动化情报提炼 Agent
读取 raw_tweets.txt → 调用大模型 API → 生成结构化 data.json
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from openai import OpenAI

# ════════════════════════════════════════════════════════
# 配置项 - 从环境变量读取，本地开发请在 .env 中设置
# ════════════════════════════════════════════════════════
API_KEY    = os.environ.get("MIMO_API_KEY")               # 必须设置环境变量 MIMO_API_KEY
BASE_URL   = os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")
MODEL_NAME = os.environ.get("MIMO_MODEL_NAME", "mimo-v2.5-pro")

# ════════════════════════════════════════════════════════

SYSTEM_PROMPT = """你是一个极具前瞻性的硅谷顶尖科技/宏观金融独立分析师。你的思维极其冷酷、客观，擅长从杂乱的新闻中发现对未来 6-18 个月有破坏性影响的趋势。

死命令：每次提炼，你必须且只能输出精确的 4 篇文章。这 4 篇文章必须严格一一对应以下四个领域：【科技前沿】、【全球金融】、【地缘政治】、【人工智能】。每个领域恰好 1 篇，不多不少。

你必须严格输出如下 JSON 结构，绝对不要包含任何多余的 Markdown 标记（如 ```json 等）：

{
  "articles": [
    { "category": "科技前沿", "date": "YYYY.MM.DD HH:MM", "title": "标题", "summary": "摘要", "stars": "★★★★", "insight": "深度思考", "original_text": "核心原始英文段落", "full_translation": "完整中文翻译", "source_name": "信息来源名称", "source_url": "原文链接" },
    { "category": "全球金融", "date": "YYYY.MM.DD HH:MM", "title": "标题", "summary": "摘要", "stars": "★★★★", "insight": "深度思考", "original_text": "核心原始英文段落", "full_translation": "完整中文翻译", "source_name": "信息来源名称", "source_url": "原文链接" },
    { "category": "地缘政治", "date": "YYYY.MM.DD HH:MM", "title": "标题", "summary": "摘要", "stars": "★★★★", "insight": "深度思考", "original_text": "核心原始英文段落", "full_translation": "完整中文翻译", "source_name": "信息来源名称", "source_url": "原文链接" },
    { "category": "人工智能", "date": "YYYY.MM.DD HH:MM", "title": "标题", "summary": "摘要", "stars": "★★★★", "insight": "深度思考", "original_text": "核心原始英文段落", "full_translation": "完整中文翻译", "source_name": "信息来源名称", "source_url": "原文链接" }
  ]
}

字段规范：
category 只能从以下选项中选择：科技前沿、全球金融、地缘政治、人工智能。
输入数据中的分类标签（如 AI、全球金融与地缘政治、智库与趋势预测）仅作参考，你必须根据文章实际内容将其归入上述四个输出分类之一。
date 必须精确到小时，格式为 YYYY.MM.DD HH:MM（根据当前时间生成）。
stars 根据前瞻破坏性打分：★★★★★ = 颠覆级、★★★★ = 重大、★★★ = 值得关注。
[极高优先级 - original_text 引用规范]
你必须直接、完整地从 raw_tweets.txt 的输入文本中提取原文片段。严禁修改原文用词，严禁增加任何非原文信息，严禁进行任何形式的逻辑重组、润色或创作。如果原文内容本身很短，请如实记录。你的首要任务是保持原始文本的「事实完备性」和「引用严谨性」。
当原文信息量确实较小时，输出的 original_text 应包含该资讯的标题 + 现有正文片段，完整呈现原文所提供的全部内容，严禁在此基础上进行任何润色、重构或补充。

[极高优先级 - full_translation 翻译规范]
full_translation 必须是对 original_text 的 1:1 精准翻译。严禁增删原文信息，严禁添加原文中不存在的背景解释。做到忠实原文逻辑（信）、中文表达流畅不机翻（达）、用词精准符合行业调性（雅）。

source_name 为信息来源的简短名称（如 Reuters、MIT Tech Review、Federal Reserve、X/@sama）。
source_url 必须直接从 raw_tweets.txt 中对应条目的「链接:」字段提取。如果原文中没有提供链接字段，则填空字符串 ""。严禁编造或推断 URL。
"""


def read_raw_tweets(filepath: str) -> str:
    """读取原始推文文本"""
    path = Path(filepath)
    if not path.exists():
        print(f"[错误] 未找到数据源文件: {filepath}")
        sys.exit(1)
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        print("[错误] 数据源文件为空")
        sys.exit(1)
    print(f"[信息] 已读取 {len(text)} 字符的原始情报")
    return text


def call_llm(raw_text: str) -> dict:
    """调用大模型 API，返回结构化 JSON"""
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    now_str = datetime.now().strftime("%Y.%m.%d %H:%M")

    # 将动态时间注入 System Prompt，替换占位符
    dynamic_prompt = SYSTEM_PROMPT.replace("YYYY.MM.DD HH:MM", now_str)

    user_prompt = f"当前时间：{now_str}\n\n以下是今日的原始情报素材：\n\n{raw_text}"
    
    print(f"[信息] 正在调用 {MODEL_NAME} 提炼情报...")
    
    try:
        # 优先尝试 JSON 模式
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": dynamic_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2000,
        )
    except TypeError:
        # 模型不支持 response_format 参数，回退为普通模式
        print("[警告] 模型不支持 JSON 模式，使用普通模式（依赖 System Prompt 约束）")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": dynamic_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
    except Exception as e:
        print(f"[错误] API 请求异常: {e}")
        sys.exit(1)
    
    content = response.choices[0].message.content.strip()
    
    # 清理可能残留的 Markdown 代码块标记
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    print("[信息] 模型响应已接收，正在解析...")
    return json.loads(content)


def validate_and_merge(new_data: dict, output_path: str, max_articles: int = 200) -> None:
    """校验新数据（4篇文章），与旧数据合并，截断后写入 data.json"""
    # 校验新数据结构
    if "articles" not in new_data:
        raise ValueError("JSON 缺少 articles 字段")

    new_articles = new_data["articles"]
    if not isinstance(new_articles, list) or len(new_articles) != 4:
        raise ValueError(f"articles 必须恰好包含 4 篇，实际 {len(new_articles)} 篇")

    required_fields = ("category", "title", "summary", "stars", "insight")
    categories_seen = set()
    for i, article in enumerate(new_articles):
        for key in required_fields:
            if key not in article:
                raise ValueError(f"articles[{i}] 缺少字段: {key}")
        categories_seen.add(article["category"])

    # 补全日期（精确到小时）
    now_str = datetime.now().strftime("%Y.%m.%d %H:%M")
    for article in new_articles:
        if "date" not in article:
            article["date"] = now_str

    print(f"[信息] 本次提炼覆盖领域: {', '.join(sorted(categories_seen))}")

    # 读取旧数据（如果存在）
    out = Path(output_path)
    old_articles = []
    if out.exists():
        try:
            old_data = json.loads(out.read_text(encoding="utf-8"))
            if "articles" in old_data and isinstance(old_data["articles"], list):
                old_articles = old_data["articles"]
            # 兼容旧格式：如果存在 featured 也纳入
            if "featured" in old_data:
                old_articles.insert(0, old_data["featured"])
            print(f"[信息] 已加载旧数据，历史记录 {len(old_articles)} 条")
        except (json.JSONDecodeError, OSError):
            print("[警告] 旧 data.json 解析失败，将全新写入")

    # 合并：新 articles 插入到旧 articles 最顶部
    merged_articles = new_articles + old_articles
    merged_articles = merged_articles[:max_articles]

    # 构建最终数据（统一格式，无 featured）
    final = {"articles": merged_articles}

    out.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[成功] 前瞻情报提炼成功，已写入 {output_path}")
    for a in new_articles:
        print(f"       [{a['category']}] {a['title']}")
    print(f"       本次新增: {len(new_articles)} 篇")
    print(f"       历史累计: {len(merged_articles)} 篇（上限 {max_articles}）")


def main():
    print("=" * 50)
    print("  ForwardPulse 情报提炼 Agent")
    print("=" * 50)

    base_dir = Path(__file__).parent
    raw_path = base_dir / "raw_tweets.txt"
    out_path = base_dir / "data.json"
    
    raw_text = read_raw_tweets(str(raw_path))
    
    try:
        data = call_llm(raw_text)
    except json.JSONDecodeError as e:
        print(f"[错误] 模型返回的不是合法 JSON: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[错误] 未知异常: {e}")
        sys.exit(1)
    
    try:
        validate_and_merge(data, str(out_path))
    except (ValueError, OSError) as e:
        print(f"[错误] 数据校验或写入失败: {e}")
        sys.exit(1)
    
    print("=" * 50)
    print("  任务完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
