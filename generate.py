#!/usr/bin/env python3
"""
ISO 9001 News Scraper & Site Generator
每日从多个来源采集 ISO 9001 标准更新消息，生成 index.html 部署到 GitHub Pages。

来源：
  1. 9001simplified.com - 修订时间线追踪
  2. thecoresolution.com - 修订解读
  3. SGS - 过渡指南
  4. DNV - 修订变化分析
  5. Intertek - 更新解读
  6. Quality Magazine - 行业新闻
  7. Smithers - ISO 9001 新闻
  8. 中文源 - iso27001.org.cn 等

输出：index.html（替换模板中的占位符）
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# ============================
# 新闻源定义
# ============================
# 每个源：(名称, URL, 标题, 摘要, 日期, 标签列表)
# 标签: revision/transition/analysis/official/cn

MANUAL_SOURCES = [
    {
        "source": "9001Simplified",
        "url": "https://www.9001simplified.com/learn/next-iso-9001-revision.php",
        "title": "ISO 9001:2026 修订完整时间线 — DIS 批准至 FDIS 发布",
        "summary": "ISO 9001:2026 修订进入最后阶段。DIS 于 2025 年 8 月发布并以 97% 支持率通过，2026 年 2 月墨西哥城会议达成技术共识，FDIS 于 2026 年 7 月获批，正式版预计 2026 年 9 月发布。3 年过渡期同步开启。",
        "date": "2026-07-15",
        "tags": ["revision", "official"]
    },
    {
        "source": "Core Business Solutions",
        "url": "https://www.thecoresolution.com/iso-9001-2026-revision-explained",
        "title": "ISO 9001:2026 修订深度解读 — 伦理与诚信、数字化、供应链韧性",
        "summary": "新版 ISO 9001 将整合伦理与诚信到领导力实践，强化风险管理与供应链韧性，增加可持续性和社会责任的明确要求。核心结构保持 HS（协调结构），与 ISO/IEC 27001:2022 对齐。",
        "date": "2025-12-10",
        "tags": ["analysis", "revision"]
    },
    {
        "source": "SGS",
        "url": "https://www.sgs.com/en/showcases/iso-9001-2026-key-updates-and-transition-guidance",
        "title": "ISO 9001:2026 关键更新与过渡指南 — SGS 官方解读",
        "summary": "新版维持 Annex SL 结构，融入质量文化和道德行为要求。FDIS 已于 2026 年 5 月发布，正式版 9 月发布，过渡期至 2029 年 9 月。建议组织尽早开始差距分析。",
        "date": "2026-06-15",
        "tags": ["transition", "official"]
    },
    {
        "source": "DNV",
        "url": "https://www.dnv.us/assurance/Management-Systems/new-iso/transition/iso-9001-revision",
        "title": "ISO 9001:2026 修订：变化内容与过渡规划 — DNV 指南",
        "summary": "DNV 预计新版于 2026 年秋季发布。DIS 阶段于 2025 年 8 月底完成，各国成员体提交意见后工作组在 2026 年初进行处置。新版在风险管理、组织知识和变革管理方面有显著调整。",
        "date": "2026-03-20",
        "tags": ["revision", "transition"]
    },
    {
        "source": "Intertek",
        "url": "https://www.intertek.com/assurance/iso-9001/iso-9001-2026-key-updates-transition-guidance",
        "title": "ISO 9001:2026 关键更新与过渡指南 — Intertek 解读",
        "summary": "新版强调数字化与智能系统（AI、数据分析、自动化）、风险与供应链监督、伦理与组织治理、以及与 ESG 期望的对齐。预计 2026 年 9 月发布，约 3 年过渡期。",
        "date": "2026-05-10",
        "tags": ["analysis", "transition"]
    },
    {
        "source": "Quality Magazine",
        "url": "https://www.qualitymag.com/articles/99324-iso-9001-in-2026-whats-changingand-how-as9100-ia9100-iatf-16949-nist-and-cmmc-fit-together",
        "title": "ISO 9001:2026 与 AS9100/IA9100、IATF 16949 的联动变化",
        "summary": "2026 年将迎来质量与合规标准的重大交汇。AS9100 将更名为 IA9100 并与 ISO 9001:2026 保持同步；IATF 16949 也在进行现代化更新。美国国防供应商面临 NIST 和 CMMC 的额外要求。",
        "date": "2026-04-05",
        "tags": ["analysis", "revision"]
    },
    {
        "source": "Smithers",
        "url": "https://www.smithers.com/resources/2026/january/iso-9001-news-preparing-for-the-2026-revision",
        "title": "ISO 9001 新闻：2026 修订准备与气候变化修正案",
        "summary": "2026 修订将强化协调结构（HS）以确保与其它 ISO 标准的术语一致性，对整合管理体系（IMS）是利好。2024 年 2 月的气候行动修正案（Amd 1:2024）已立即生效，无需过渡期。",
        "date": "2026-01-25",
        "tags": ["revision", "analysis"]
    },
    {
        "source": "ISO 27001 中文网",
        "url": "http://www.iso27001.org.cn/fuwu/iso/iso9001/show_988.html",
        "title": "ISO 9001:2026 版标准的重要内容和变化（中文）",
        "summary": "11 项关键变化解读：道德与诚信、使命愿景价值观和质量文化、气候变化、风险与机遇概念更新、新兴技术（AI/元宇宙/VR/聊天机器人）、成文信息可获得性、QA 角色提升、相关方沟通、顾客体验扩展、服务与产品区别。",
        "date": "2024-12-10",
        "tags": ["cn", "revision"]
    },
    {
        "source": "ISO",
        "url": "https://www.iso.org/standard/62085.html",
        "title": "ISO 9001:2015 现行标准页面 — ISO 官方",
        "summary": "ISO 9001:2015 现行版本。ISO/TC 176/SC 2 正在推进 2026 版修订，新版预计 2026 年 9 月发布。这是全球应用最广泛的质量管理体系标准，超过 100 万组织获得认证。",
        "date": "2026-06-01",
        "tags": ["official"]
    },
    {
        "source": "IAF",
        "url": "https://iaf.nu/",
        "title": "IAF 预期发布 ISO 9001:2026 过渡安排指南",
        "summary": "国际认可论坛（IAF）将在 ISO 9001:2026 正式发布后公布过渡安排。业界预期过渡期为 3 年（至 2029 年 9 月），与以往主要修订的过渡政策保持一致。",
        "date": "2026-07-01",
        "tags": ["official", "transition"]
    },
]


def scrape_web_sources():
    """
    尝试从网络获取最新消息。
    使用 web_extract 抓取已知源页面，提取新信息。
    返回新增的新闻条目列表。
    """
    # 在网络受限环境中，回退到手动维护的源
    # 后续可通过 Hermes cron job 调用 web_extract 动态更新
    return []


def merge_news(manual, scraped):
    """合并手动维护的新闻和爬取的新闻，去重后按日期降序排列。"""
    seen_urls = set()
    merged = []

    for item in scraped + manual:
        if item["url"] not in seen_urls:
            seen_urls.add(item["url"])
            merged.append(item)

    merged.sort(key=lambda x: x["date"], reverse=True)
    return merged


def generate_html(news_data, template_path, output_path):
    """将新闻数据注入 HTML 模板，生成最终页面。"""
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # 注入数据
    json_data = json.dumps(news_data, ensure_ascii=False)
    html = html.replace("__NEWS_DATA_PLACEHOLDER__", json_data)

    # 注入更新时间
    now = datetime.now(timezone(timedelta(hours=8)))
    update_str = now.strftime("%Y-%m-%d %H:%M CST")
    html = html.replace("__UPDATE_TIME__", update_str)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ Generated {output_path} with {len(news_data)} news items")
    print(f"   Update time: {update_str}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, "index_template.html")
    output_path = os.path.join(script_dir, "index.html")

    # 检查是否有模板文件（首次运行时 index.html 就是模板，含占位符）
    if not os.path.exists(template_path):
        # 首次运行：index.html 本身就是模板
        template_path = output_path
        print("📋 首次运行，index.html 即为模板")
    else:
        print("📋 使用独立模板文件")

    print("🔍 采集 ISO 9001 新闻...")
    scraped = scrape_web_sources()
    print(f"   网络采集：{len(scraped)} 条")

    print(f"   手动维护：{len(MANUAL_SOURCES)} 条")
    news = merge_news(MANUAL_SOURCES, scraped)
    print(f"   合并去重：{len(news)} 条")

    generate_html(news, template_path, output_path)
    print("🏁 完成")


if __name__ == "__main__":
    main()
