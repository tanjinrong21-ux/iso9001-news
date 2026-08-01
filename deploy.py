#!/usr/bin/env python3
"""
ISO 9001 News — 自动部署流水线
===============================
1. 运行 Web 采集 → 获取最新 ISO 9001 新闻
2. 合并手动维护数据 + 网络采集数据
3. 生成 index.html
4. Git commit + push 到 GitHub Pages
5. 验证部署状态

用法：
  python deploy.py           # 完整流水线
  python deploy.py --dry-run # 只生成不推送
  python deploy.py --no-push # 生成+commit，不push
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

# ============================
# 配置
# ============================
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_FILE = os.path.join(REPO_DIR, "index_template.html")
OUTPUT_FILE = os.path.join(REPO_DIR, "index.html")
GH_USER = "tanjinrong21-ux"
GH_REPO = "iso9001-news"
PAGES_URL = f"https://{GH_USER}.github.io/{GH_REPO}/"

# 已知新闻源（手动维护，作为基础数据）
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
        "summary": "2026 年将迎来质量与合规标准的重大交汇。AS9100 将更名为 IA9100 并与 ISO 9001:2026 同步；IATF 16949 也在现代化更新。美国国防供应商面临 NIST 和 CMMC 的额外要求。",
        "date": "2026-04-05",
        "tags": ["analysis", "revision"]
    },
    {
        "source": "Smithers",
        "url": "https://www.smithers.com/resources/2026/january/iso-9001-news-preparing-for-the-2026-revision",
        "title": "ISO 9001 新闻：2026 修订准备与气候变化修正案",
        "summary": "2026 修订将强化协调结构（HS）以确保跨标准术语一致性，对整合管理体系（IMS）是利好。2024 年 2 月的气候行动修正案（Amd 1:2024）已立即生效，无需过渡期。",
        "date": "2026-01-25",
        "tags": ["revision", "analysis"]
    },
    {
        "source": "ISO 27001 中文网",
        "url": "http://www.iso27001.org.cn/fuwu/iso/iso9001/show_988.html",
        "title": "ISO 9001:2026 版标准的重要内容和变化（中文）",
        "summary": "11 项关键变化：道德与诚信、使命愿景价值观和质量文化、气候变化、风险与机遇概念更新、新兴技术（AI/元宇宙/VR/聊天机器人）、成文信息可获得性、QA 角色提升、相关方沟通、顾客体验扩展、服务与产品区别。",
        "date": "2024-12-10",
        "tags": ["cn", "revision"]
    },
    {
        "source": "ISO",
        "url": "https://www.iso.org/standard/62085.html",
        "title": "ISO 9001:2015 现行标准页面 — ISO 官方",
        "summary": "ISO 9001:2015 现行版本。ISO/TC 176/SC 2 正在推进 2026 版修订，新版预计 2026 年 9 月发布。全球应用最广泛的质量管理体系标准，超过 100 万组织获认证。",
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


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def merge_news(manual, scraped):
    """合并去重，按日期降序。"""
    seen = set()
    merged = []
    for item in scraped + manual:
        if item["url"] not in seen:
            seen.add(item["url"])
            merged.append(item)
    merged.sort(key=lambda x: x["date"], reverse=True)
    return merged


def generate_html(news_data):
    """注入数据到 HTML 模板。"""
    if not os.path.exists(TEMPLATE_FILE):
        log(f"❌ 模板文件不存在: {TEMPLATE_FILE}")
        return False

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    json_data = json.dumps(news_data, ensure_ascii=False)
    html = html.replace("__NEWS_DATA_PLACEHOLDER__", json_data)

    now = datetime.now(timezone(timedelta(hours=8)))
    update_str = now.strftime("%Y-%m-%d %H:%M CST")
    html = html.replace("__UPDATE_TIME__", update_str)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    log(f"✅ 生成 {OUTPUT_FILE} ({len(news_data)} 条新闻, 更新时间 {update_str})")
    return True


def git_commit_and_push(dry_run=False, no_push=False):
    """提交并推送。"""
    if dry_run:
        log("🔍 Dry-run 模式，跳过 git 操作")
        return True

    os.chdir(REPO_DIR)

    # 检查是否有变更
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True
    )
    if not result.stdout.strip():
        log("📭 没有变更，跳过 commit")
        return True

    subprocess.run(["git", "add", "index.html"], check=True)

    now = datetime.now(timezone(timedelta(hours=8)))
    msg = f"Auto-update: {now.strftime('%Y-%m-%d %H:%M CST')} — {len(json.loads(open(OUTPUT_FILE).read().split('NEWS_DATA = ')[1].split(';')[0]))} items"
    subprocess.run(["git", "commit", "-m", msg], check=True)
    log(f"📝 Commit: {msg}")

    if no_push:
        log("⏸️ 跳过 push（--no-push）")
        return True

    # Push
    try:
        result = subprocess.run(
            ["git", "push", "origin", "master"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            log("✅ Push 成功")
            return True
        else:
            log(f"❌ Push 失败: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        log("❌ Push 超时")
        return False


def verify_deployment():
    """验证 GitHub Pages 部署状态。"""
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{GH_USER}/{GH_REPO}/pages"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            status = data.get("status", "unknown")
            url = data.get("html_url", PAGES_URL)
            log(f"🌐 Pages 状态: {status} → {url}")
            return status == "built"
        else:
            log(f"⚠️ 无法查询 Pages 状态: {result.stderr.strip()}")
            return False
    except Exception as e:
        log(f"⚠️ 验证异常: {e}")
        return False


def main():
    dry_run = "--dry-run" in sys.argv
    no_push = "--no-push" in sys.argv

    log("🚀 ISO 9001 News 部署流水线启动")
    log(f"   仓库: {GH_USER}/{GH_REPO}")
    log(f"   站点: {PAGES_URL}")

    # Step 1: 采集新闻（当前使用手动维护数据 + 网络采集占位）
    # TODO: 集成 web_extract 自动采集
    log("🔍 采集新闻...")
    scraped = []  # 后续接入 web_extract 动态采集
    news = merge_news(MANUAL_SOURCES, scraped)
    log(f"   手动维护: {len(MANUAL_SOURCES)} | 网络采集: {len(scraped)} | 合计: {len(news)}")

    # Step 2: 生成 HTML
    log("📄 生成 HTML...")
    if not generate_html(news):
        sys.exit(1)

    # Step 3: Git push
    log("📤 推送到 GitHub...")
    if not git_commit_and_push(dry_run=dry_run, no_push=no_push):
        log("⚠️ Push 失败，但 HTML 已生成")
        if not dry_run:
            sys.exit(1)

    # Step 4: 验证
    if not dry_run and not no_push:
        log("🔍 验证部署...")
        time.sleep(5)
        verify_deployment()

    log("🏁 完成")


if __name__ == "__main__":
    main()
