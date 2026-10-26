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
        "source": "ACCREDIA（意大利认可机构）",
        "url": "https://www.accredia.it/wp-content/uploads/2026/10/Circolare_informativa_DC_41-2026_ENG-Transition-to-ISO9001-2026-and-ISO14001-2026.pdf",
        "title": "ACCREDIA 发布第 41/2026 号通告 — ISO 9001:2026 与 ISO 14001:2026 认可转换操作安排",
        "summary": "意大利认可机构 ACCREDIA 于 2026-10-20 签发信息通告第 41/2026 号（Ref. DC2026SPM145），首次把 Global ACI 的强制性过渡要求落地为认可机构层面的操作程序，并给出 ISO 9001:2026 五道关键期限：ACCREDIA 自身具备按新版评审的能力 2027-03-31；获认可认证机构（CAB）提交过渡声明及支持文件 2027-06-30；ACCREDIA 完成 CAB 认可转换决定 2027-09-30；停止按 ISO 9001:2015 颁发新证书 2028-03-31；过渡期结束、2015 版证书失效 2029-09-30。通告同时明确：CAB 完成内部适配后即可开展新版审核，但在 ACCREDIA 经 CSA CI 决议批准其认可转换前，不得颁发新版证书；自通告签发日起可受理新版认可申请。这是首个公开的国家/地区级落地时间表，对判断各认可机构节奏具参考价值。",
        "date": "2026-10-20",
        "tags": ["official", "transition"]
    },
    {
        "source": "ISO/TC 176/SC 2",
        "url": "https://committee.iso.org/sites/tc176sc2/home/news/content-left-area/news-and-updates/news-2.html",
        "title": "ISO/TC 176/SC 2 正式发布：ISO 9001:2026 已出版 — 附五条过渡时间节点",
        "summary": "ISO/TC 176/SC 2 于 2026-09-28 由 Mark Finewood 发布公告《ISO 9001:2026 has been released!》，确认 ISO 9001:2026 已于 2026-09-16 出版，并集中列出五条过渡指引：认可机构最迟 2027-03-31 具备按新版评审能力；获认可认证机构 2027-06-30 前提交过渡声明及支持信息；认可机构过渡决定 2027-09-30 前完成；自 2028-03-31 起新的和初次认可认证只能按 ISO 9001:2026 颁发；已获 2015 版认证的组织须在 2029-09-30 前完成过渡，可在例行监督审核、再认证审核中完成，也可另做专项过渡审核。公告强调本次修订是在既有框架上的更新：措辞更清晰，更强调领导力、质量文化与责任担当，风险与机遇表述更明确，新增附录 A 澄清关键术语与条款意图，并与其他管理体系标准保持更好对齐。",
        "date": "2026-09-28",
        "tags": ["official", "transition"]
    },
    {
        "source": "SCC（加拿大标准理事会）",
        "url": "https://scc-ccn.ca/accreditation/bulletins/quality-management-systems-transition-iso-90012026",
        "title": "加拿大 SCC 第 2026-23 号公告 — ISO 9001:2026 认可过渡安排与 CAB 提交要求",
        "summary": "加拿大标准理事会（SCC）于 2026-09-25 发布第 2026-23 号公告，面向管理体系认可项目（MSAP）的获认可客户、申请人、认可咨询小组及评审员，明确 ISO 9001:2026（含 Global ACI-TECH-3-TR 2029-09-30 (M)）均于 2026-09-16 生效，属 Level 5 标准，修订直接影响合格评定机构（CAB）。CAB 须提交的证据包包括：过渡计划、为支撑新版认证项目能力而更新的 CAB 文件、审核人日变更、证书控制安排，且须自行向 SCC 证明其已充分覆盖新版要求与能力需求。关键节点：2027-03-31 起 SCC 开始过渡评审；最迟 2027-06-30 提交附录 A 过渡声明及支持文件；2027-09-30 前完成 SCC 的过渡决定（含认可文件/证书签发）；此后仅受理 2026 版申请；所有现行认证须转换为 2026 版。",
        "date": "2026-09-25",
        "tags": ["official", "transition"]
    },
    {
        "source": "ANSI",
        "url": "https://www.ansi.org/standards-news/all-news/9-16-26-first-full-revision-of-iso-9001-in-a-decade-now-available-from-ansi",
        "title": "ANSI：十年来首次全面修订 — ISO 9001:2026 已可通过 ANSI 网络书店获取",
        "summary": "美国国家标准机构 ANSI 于 2026-09-16 发文称 ISO 9001:2026 是这一全球应用最广质量管理标准十余年来首次全面修订，并概括六项更新：风险与机遇的区分更清晰，鼓励组织像防范挫折一样主动寻找改进机会；更强调质量文化、价值观与道德行为，明确领导层在营造质量环境中的角色；更重视变更管理，帮助组织有意识地而非被动应对转变；气候变化内容并入正文（吸收 2015 版 2024 修正案）；修订附录 A 阐释要求意图以降低歧义误读，对首次使用者与小微企业尤其友好；通过最新协调结构加强与其他管理体系标准对齐，使整合体系运行更高效。ANSI 总裁 Laurie E. Locascio 表示信任不是宣称出来的，而是通过开放、平衡与共识建立的。文中提示：认证机构须先由认可机构完成自身过渡，才能颁发新版证书，组织应尽早与认证机构排定过渡审核。",
        "date": "2026-09-16",
        "tags": ["official", "analysis"]
    },
    {
        "source": "Smithers",
        "url": "https://www.smithers.com/resources/2026/september/iso-9001-2026-is-here-what-your-business-must-know",
        "title": "Smithers：ISO 9001:2026 已生效 — 审核关注点与过渡实操要点",
        "summary": "Smithers 于 2026 年 9 月发布的实务解读，站在审核视角拆解新版变化：一是质量文化与道德要求升级，领导层须证明质量价值观已嵌入全业务而非局限于质量部门，质量从合规职能回归全员共担；二是风险与机遇管理更严格，简单的风险登记表已不够，组织需有分析、排序与行动计划，以改善决策并激发真正的创新机会；三是变更管理要求收紧，凡可能影响质量绩效的重大变更，都须能证明策划、沟通、监测与评审有效；四是气候变化考量直接纳入标准正文，组织须评估气候议题与其业务环境、相关方及质量目标的相关性。文章同时引用 NSF 技术方案经理 Marco Brunato 的观点：新版与 ISO 协调结构一致，同时回应组织韧性、道德行为、知识管理与气候议题等当代挑战。审核仍以有效性为核心，而非文件化程度。",
        "date": "2026-09-16",
        "tags": ["analysis", "transition"]
    },
    {
        "source": "ISO/TC 176",
        "url": "https://committee.iso.org/sites/tc176/home/news/content-left-area/news-and-updates/news.html",
        "title": "ISO/TC 176 官方公告：ISO 9001:2026 已发布 — 附完整过渡时间表",
        "summary": "ISO/TC 176 于 2026-09-23 由 Mark Finewood 发布公告确认 ISO 9001:2026 已于 2026-09-16 出版，并给出经 Global ACI 确认的过渡关键节点：认可机构最迟 2027-03-31 具备对 ISO 9001:2026 实施评审的能力；获认可的认证机构须在 2027-06-30 前提交过渡声明及支持性信息；认可机构的过渡决定须在 2027-09-30 前完成；自 2028-03-31 起，新的和初次认可认证只能依据 ISO 9001:2026 颁发；已获 ISO 9001:2015 认证的组织须在 2029-09-30 前完成过渡。变化要点：措辞更清晰，更强调领导力、质量文化与责任担当，风险与机遇表述更明确，新增附录 A 澄清关键术语与条款意图，并与其他管理体系标准保持更好对齐。",
        "date": "2026-09-23",
        "tags": ["official", "transition"]
    },
    {
        "source": "Global ACI",
        "url": "https://global-aci.org/en/news/global-aci-publishes-transition-requirements-for-iso-90012026",
        "title": "Global ACI 正式发布 ISO 9001:2026 过渡要求 — 强制性文件 TECH-3-TR 2029-09-30 (M)",
        "summary": "原 IAF 职能承接方 Global ACI（国际认可合作组织）已发布强制性文件 Global ACI-TECH-3-TR 2029-09-30 (M)《Transition Requirements for ISO 9001:2026》，签发日 2026-09-04、实施日 2026-09-16，为认可机构与获认可认证机构提供从 ISO 9001:2015（含 Amd 1:2024）向新版过渡的时间表，对 Global ACI MRA 签署方及其认可认证机构具强制性。核心期限：认可机构最迟 2027-03-31 具备评审能力；认证机构 2027-06-30 前提交过渡声明；认可机构过渡决定 2027-09-30 前完成；2028-03-31 起新发/初次认可认证仅限 ISO 9001:2026；现有 2015 版获证组织最迟 2029-09-30 完成过渡，可在例行监督或再认证审核中完成，也可另做专项过渡审核。全球逾百万张获认可 ISO 9001 证书需在此统一时间框架下完成转换。",
        "date": "2026-09-16",
        "tags": ["official", "transition"]
    },
    {
        "source": "ISO",
        "url": "https://www.iso.org/news/2026/09/ISO9001-2026",
        "title": "ISO 9001:2026 正式发布 — 全球最广泛应用质量管理标准迎来第六版",
        "summary": "ISO 于 2026 年 9 月 16 日在日内瓦宣布 ISO 9001:2026《质量管理体系 — 要求》正式发布，取代 ISO 9001:2015。新版更强调领导力、质量文化与道德行为，对风险和机遇的考虑给出更清晰的说明，采用最新协调结构（HS）以便与其他管理体系整合，并新增附录 A 阐释条款意图。ISO 秘书长 Sergio Mujica 称其为质量管理「黄金标准」的里程碑。ISO 9001 还将纳入 ISO 首批数字化增强内容，自 2026 年 10 月 1 日起提供。",
        "date": "2026-09-16",
        "tags": ["official", "revision"]
    },
    {
        "source": "ISO",
        "url": "https://www.iso.org/standard/88464.html",
        "title": "ISO 9001:2026（第 6 版）标准页面 — 修订全生命周期节点可查",
        "summary": "ISO 官网 ISO 9001 页面显示第 6 版（Edition 6，2026-09），将取代 ISO 9001:2015。关键节点：DIS 注册 2025-06-30、DIS 投票启动 2025-08-27、投票结束 2025-11-20、DIS 获批转 FDIS 2026-04-15、FDIS 投票启动 2026-05-14、投票结束 2026-07-10、进入出版阶段（60.00）。提示：截至 2026-09-22 查询时该页面仍显示「出版中 · 最终制作步骤（最长约七周）」，最终出版阶段 60.60 待 ISO 更新。",
        "date": "2026-09-16",
        "tags": ["official"]
    },
    {
        "source": "ISO",
        "url": "https://www.iso.org/quality-management/iso-9001-2026",
        "title": "ISO 官方解读：ISO 9001:2026 要点须知 — 变化、不变与过渡安排",
        "summary": "ISO 官方说明新版已成为现行版本并取代 2015 版，条款结构维持协调结构不变。重点变化：第 6.1 条更清晰区分风险与机遇；第 7.3 条新增对质量文化与道德行为的意识要求；新增附录 A 澄清关键概念、术语与条款意图。获证组织有三年过渡期，无需重新走一遍认证流程，具体时间由认证机构沟通。ISO 建议先做差距分析，再更新过程与成文信息，并让各层级人员理解变化。",
        "date": "2026-09-16",
        "tags": ["official", "analysis", "transition"]
    },
    {
        "source": "ISO/TC 176/SC 2",
        "url": "https://committee.iso.org/sites/tc176sc2/home/news/content-left-area/news-and-updates/news-1.html",
        "title": "ISO/FDIS 9001 以压倒性国际支持获批 — 确认 9 月 16 日出版",
        "summary": "ISO/TC 176/SC 2 于 2026-08-07 公告：ISO/FDIS 9001 获得压倒性国际支持通过，第六版 ISO 9001 计划于 2026-09-16 出版，并向 WG 29 召集人、支持团队及全体成员为这一全球质量管理界里程碑所作的贡献致谢。",
        "date": "2026-08-07",
        "tags": ["official", "revision"]
    },
    {
        "source": "NSF",
        "url": "https://www.nsf.org/knowledge-library/iso-90012026-published-on-september-16-2026-what-quality-leaders-need-to-know",
        "title": "NSF：ISO 9001:2026 将于 9 月 16 日发布 — 质量负责人须知",
        "summary": "NSF 技术方案经理 Marco Brunato 撰文：ISO 已公布 ISO 9001:2026 于 2026-09-16（周三）发布。新版是演进而非革命，体系成熟的组织无需大改；重点强化质量文化、道德行为、风险管理、组织知识与气候相关考虑。2015 版获证组织预计有约三年过渡期，可结合既有认证周期完成转换，提早规划者过渡更顺、受益更快。",
        "date": "2026-08-07",
        "tags": ["analysis", "transition"]
    },
    {
        "source": "ISTO",
        "url": "https://www.isto.ch/pt/insights/iso9001-2026-changes",
        "title": "ISO 9001:2026 变化解析：质量文化、气候变化与扩展的附录 A",
        "summary": "ISTO 于 2026-06-22 发布的解读：发布日为 2026-09-16，三年过渡期预计至 2029 年 9 月，正式时长待认可机构确认。值得注意的组织变更：IAF 职能自 2026-01-01 起由 Global Accreditation Cooperation Incorporated（Global ACI）承接，过渡期的正式安排将由该机构公布。2015 版证书在整个过渡期内持续有效，企业因此有真正的时机选择空间。",
        "date": "2026-06-22",
        "tags": ["analysis", "transition"]
    },
    {
        "source": "标准知多点 / 江苏省钢铁行业协会",
        "url": "http://www.jsgt.org.cn/index.php/Home/Index/art/a_id/38532.html",
        "title": "国家标准《质量管理体系 要求》启动修订 — 拟等同采用 ISO 9001:2026（中文）",
        "summary": "市场监管总局标准技术管理司就 153 项拟立项国家标准征求意见，其中《质量管理体系 要求》拟修订，等同采用 ISO 9001:2026，代替现行 GB/T 19001-2016。该标准由 TC151（全国质量管理和质量保证标准化技术委员会）归口，国家标准委主管，中国标准化研究院牵头起草，项目周期 10 个月，意见征集截止 2026-08-06。中文要点：强化最高管理者牵头落实道德与诚信，新增质量文化建设内容，更关注气候变化因素，风险与机遇拆分为两个独立条款，附录新增新兴技术管控内容，并以「可获得」取代「保持 / 保留」的成文信息表述。",
        "date": "2026-07-10",
        "tags": ["cn", "revision"]
    },
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

    # Push —— 第一次走 git 配置（可能含本地代理 127.0.0.1:3067）
    # 若失败（典型原因：Karing 代理未启动，见 2026-09-19 事故），
    # 自动回退为「直连」再试一次（白天 GitHub 可直连），避免 commit 静默堆积。
    attempts = [
        (["git", "push", "origin", "main"], 30, "配置代理"),
        (["git", "-c", "http.proxy=", "-c", "https.proxy=", "push", "origin", "main"], 90, "直连回退"),
    ]
    last_err = ""
    for cmd, tmo, label in attempts:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=tmo)
        except subprocess.TimeoutExpired:
            last_err = f"{label} 超时({tmo}s)"
            log(f"⚠️ Push {last_err}，重试...")
            continue
        if result.returncode == 0:
            log(f"✅ Push 成功（{label}）")
            return True
        last_err = result.stderr.strip()
        log(f"⚠️ Push 失败（{label}）: {last_err[:200]}")

    log(f"❌ Push 全部失败: {last_err[:200]}")
    log("   本地 commit 未丢失，下次运行会一并推送")
    return False


def _head_sha():
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except Exception:
        return ""


def verify_deployment(max_wait=180):
    """验证 GitHub Pages 是否真的部署了本次 commit（push ≠ 部署）。"""
    head = _head_sha()
    deadline = time.time() + max_wait
    last = "unknown"
    while time.time() < deadline:
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{GH_USER}/{GH_REPO}/pages/builds/latest"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                status = data.get("status", "unknown")
                commit = data.get("commit", "")
                last = status
                if status == "built" and (not head or commit == head):
                    log(f"🌐 Pages 部署确认: built @ {commit[:7]} → {PAGES_URL}")
                    return True
                if status == "errored":
                    log(f"❌ Pages 构建失败(errored) @ {commit[:7]} — 需新 commit 触发重建")
                    return False
                log(f"⏳ Pages 构建中: {status} @ {commit[:7]}（等待...）")
            else:
                log(f"⚠️ 无法查询 Pages 构建状态: {result.stderr.strip()[:150]}")
                return False
        except Exception as e:
            log(f"⚠️ 验证异常: {e}")
            return False
        time.sleep(15)

    log(f"⚠️ Pages 构建超时未确认（最后状态: {last}）")
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
