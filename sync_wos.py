# -*- coding: utf-8 -*-
"""
王小治教授课题组 (wxz.group) Web of Science 官方权威数据同步与治理引擎
- 基于 Clarivate Web of Science Starter API 官方数据源
- 双 API Key 智能轮换与接力容错架构 (支持安全环境变量注入，代码零明文泄漏)
- 永久固化 2025 年及以前成果元数据与研究主题（仅实时刷新被引频次）
- 深度提取 authorKeywords 结合标题精准判定 6 大特色环境材料化工研究主题
- 彻底过滤页码/文章号字典脏数据 (杜绝 {'count': 11} 等异常输出)
- 严格识别重点期刊 (Angew, EST, WR, Adv Sci, ACB, CEJ)、代表作与 ESI 高被引
- 独立输出：模块一 (impact_data.js) 与 模块二 (publications_data.js)
"""

import os
import sys
import re
import json
import time
import random
import urllib.request
import urllib.parse
from datetime import datetime

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ==================== 核心配置与目录 ====================
RESEARCHER_ID = "PDX-5463-2025"
SCHOLAR_NAME_CN = "王小治"
SCHOLAR_NAME_EN = "Xiaozhi Wang"
AFFILIATION = "扬州大学环境科学与工程学院"
BASE_URL = "https://api.clarivate.com/apis/wos-starter/v1/documents"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SELECTED_FILE = os.path.join(SCRIPT_DIR, "selected_doi.txt")
ESI_FILE = os.path.join(SCRIPT_DIR, "esi_top_1_percent.txt")
CORR_FILE = os.path.join(SCRIPT_DIR, "corresponding_titles.txt")
CROSSREF_CACHE_FILE = os.path.join(SCRIPT_DIR, "crossref_cache.json")
FIXED_CACHE_FILE = os.path.join(SCRIPT_DIR, "wos_fixed_metadata.json")
LOCAL_SECRETS_FILE = os.path.join(SCRIPT_DIR, "wos_secrets.local.json")

# 导出数据文件
IMPACT_JSON_FILE = os.path.join(SCRIPT_DIR, "impact_metrics.json")
IMPACT_JS_FILE = os.path.join(SCRIPT_DIR, "impact_data.js")
PUBS_JSON_FILE = os.path.join(SCRIPT_DIR, "publications.json")
PUBS_JS_FILE = os.path.join(SCRIPT_DIR, "publications_data.js")

# 重点期刊规则（环境材料化工特色，按梯队严格匹配）
TOP_JOURNALS_STRICT = [
    {"abbr": "Angew", "pattern": r"angewandte\s+chemie", "name": "Angewandte Chemie International Edition", "weight": 100},
    {"abbr": "EST", "pattern": r"environmental\s+science\s+&\s+technology", "exclude": r"\(china\)|china", "name": "Environmental Science & Technology", "weight": 90},
    {"abbr": "WR", "pattern": r"water\s+research", "name": "Water Research", "weight": 80},
    {"abbr": "Adv Sci", "pattern": r"advanced\s+science", "name": "Advanced Science", "weight": 70},
    {"abbr": "ACB", "pattern": r"applied\s+catalysis\s+b", "name": "Applied Catalysis B: Environment and Energy", "weight": 60},
    {"abbr": "CEJ", "pattern": r"chemical\s+engineering\s+journal", "name": "Chemical Engineering Journal", "weight": 50},
    {"abbr": "JHM", "pattern": r"journal\s+of\s+hazardous\s+materials", "name": "Journal of Hazardous Materials", "weight": 40},
    {"abbr": "ACS Catal", "pattern": r"acs\s+catalysis", "name": "ACS Catalysis", "weight": 35},
    {"abbr": "Nano Energy", "pattern": r"nano\s+energy", "name": "Nano Energy", "weight": 30},
    {"abbr": "Biochar", "pattern": r"\bbiochar\b", "name": "Biochar", "weight": 25}
]

# 课题组 6 大核心学术主题深度匹配规则（Title + authorKeywords + Source）
THEME_RULES = [
    {
        "name": "光催化与环境材料",
        "regex": r"photocataly|photo-cataly|co2 photoreduction|co2 reduction|photoreduction|nitrogen fixation|n2 fixation|biocl|biobr|bioi|bismuth oxyhalide|carbon nitride|g-c3n4|heterojunction|photothermal|photoelectro|visible light|solar|band gap|photo-induced|photodegradation|photooxidation|photogenerated|photocatalyst|light irradiation|photosynthetic|photoelectrochemical|photofenton|single-atom catalyst|tio2|phase engineering"
    },
    {
        "name": "生物炭与多孔材料",
        "regex": r"biochar|porous carbon|carbon flake|supercapacitor|nanosphere|straw|pyrolysis|carbon material|biomass|hydrochar|mesoporous|activated carbon|carbon dot|carbon defect|carbon nano|aerogel|mof|zeolite|sewage sludge"
    },
    {
        "name": "高级氧化与铁循环",
        "regex": r"fenton|persulfate|peroxymonosulfate|peroxydisulfate|\bpds\b|\bpms\b|hydroxyl radical|reactive oxygen|sulfate radical|\bso4\.-|\b\.-oh\b|electron transfer|iron|nzvi|ferri|zerovalent iron|magnetite|fe3o4|fe\(ii\)|fe\(iii\)|oxygen vacancy|catalytic oxidation|advanced oxidation"
    },
    {
        "name": "重金属吸附与修复",
        "regex": r"heavy metal|cadmium|\bcd\b|arsenic|\bas\b|lead|\bpb\b|copper|\bcu\b|chromium|\bcr\b|mercury|\bhg\b|adsorption|desorption|soil remediation|remediation|earthworm|eisenia|immobiliz|speciation|pak choi|bioaccumul|contamination|atmospheric deposition|aerosol"
    },
    {
        "name": "土壤生态与碳氮循环",
        "regex": r"soil organic carbon|paddy|nitrogen cycle|nitrate|ammoni|urea|carbon cycle|n2o|methane|ch4|greenhouse gas|microbial community|bacteria|wheat|rice|crop|nutrient|fertiliz|sediment|lake|organic matter|humic|root|rhizosphere|orchard|intercropping|cover crop|elevated co2"
    },
    {
        "name": "新兴污染物与健康",
        "regex": r"microplastic|tetracycline|sulfamethoxazole|ciprofloxacin|antibiotic|pharmaceutical|endocrine|formaldehyde|hcho|voc|volatile organic|indoor air|oxidative stress|metabolom|toxic|antimicrobial"
    }
]

def load_api_keys():
    """安全读取 API Keys：优先从环境变量加载，本地从安全文件加载，绝对杜绝代码明文"""
    keys = []
    # 1. 优先读取系统环境变量 (GitHub Actions Secrets)
    for env_var in ["WOS_API_KEYS", "WOS_API_KEY"]:
        val = os.environ.get(env_var, "").strip()
        if val:
            for k in re.split(r"[,;\s]+", val):
                if k.strip() and k.strip() not in keys:
                    keys.append(k.strip())
    for env_var in ["WOS_API_KEY_1", "WOS_API_KEY_2", "WOS_KEY_1", "WOS_KEY_2"]:
        val = os.environ.get(env_var, "").strip()
        if val and val not in keys:
            keys.append(val)

    # 2. 从本地私密文件加载 (已加入 .gitignore，不随代码提交)
    if not keys and os.path.exists(LOCAL_SECRETS_FILE):
        try:
            with open(LOCAL_SECRETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                loaded = data.get("WOS_API_KEYS", [])
                if isinstance(loaded, list):
                    for k in loaded:
                        if isinstance(k, str) and k.strip() and k.strip() not in keys:
                            keys.append(k.strip())
        except Exception:
            pass

    return keys

def clean_html_tags(s):
    """去除 HTML 标签"""
    if not s:
        return ""
    return re.sub(r'<[^>]+>', '', s).strip()

def normalize_title(t):
    """标题字符串清洗归一化：小写并剔除所有非字母数字字符"""
    if not t:
        return ""
    t_clean = clean_html_tags(t)
    return re.sub(r"[^a-z0-9]", "", t_clean.lower())

def to_title_case(s):
    """转换为标准学术英文标题大小写"""
    if not s:
        return ""
    s = s.strip()
    words = s.split()
    lowers = {'and', 'or', 'of', 'for', 'in', 'on', 'with', 'by', 'at', 'to', 'from', 'as', 'the', 'a', 'an'}
    titled = []
    for i, w in enumerate(words):
        w_low = w.lower()
        if i > 0 and w_low in lowers:
            titled.append(w_low)
        else:
            titled.append(w.capitalize())
    return " ".join(titled)

def load_text_lines(filepath):
    """读取文本行并自动剔除注释与空行"""
    if not os.path.exists(filepath):
        return []
    lines = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines

def parse_clean_pages(pages_obj, article_number=""):
    """
    清洗提取规范的页码或文章号
    彻底杜绝诸如 {'range': '370-382', ...} 或 {'count': 11} 的字典脏字符
    """
    art_str = ""
    if article_number is not None:
        raw_art = str(article_number).strip()
        # 正常文章号长度适中 (如 106620, 115669, 138149, 125179)
        if raw_art and len(raw_art) <= 12 and not raw_art.startswith("{"):
            art_str = raw_art

    if not pages_obj:
        return art_str

    if isinstance(pages_obj, dict):
        if pages_obj.get("range"):
            return str(pages_obj["range"]).strip()
        if pages_obj.get("begin"):
            b = str(pages_obj["begin"]).strip()
            e = str(pages_obj.get("end", "")).strip()
            return f"{b}-{e}" if e and e != b else b
        # 仅有 count 而无真实页码时，取文章编号
        return art_str

    if isinstance(pages_obj, str):
        p = pages_obj.strip()
        if "range" in p:
            m = re.search(r"['\"]range['\"]\s*:\s*['\"]([^'\"]+)['\"]", p)
            if m:
                return m.group(1).strip()
        if "begin" in p and "end" in p:
            m = re.search(r"['\"]begin['\"]\s*:\s*['\"]([^'\"]+)['\"].*?['\"]end['\"]\s*:\s*['\"]([^'\"]+)['\"]", p)
            if m:
                return f"{m.group(1).strip()}-{m.group(2).strip()}"
        if p.startswith("{") or "count" in p:
            return art_str
        return p

    return art_str

def fetch_crossref_metadata(doi, cache):
    """通过 Crossref API 获取标准卷号、期号与页码"""
    if not doi:
        return {}
    doi_key = doi.lower().strip()
    if doi_key in cache:
        return cache[doi_key]

    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}"
    req = urllib.request.Request(url, headers={
        "User-Agent": "AcademicWebsiteBuilder/1.0 (mailto:scholar@wxz.group)"
    })
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            msg = data.get("message", {})
            vol = str(msg.get("volume", "")).strip()
            iss = str(msg.get("issue", "")).strip()
            page = str(msg.get("page", "") or msg.get("article-number", "")).strip()
            res = {"volume": vol, "issue": iss, "pages": page}
            cache[doi_key] = res
            return res
    except Exception:
        cache[doi_key] = {"volume": "", "issue": "", "pages": ""}
        return cache[doi_key]

def update_fanke_module1_static(impact_data):
    """自动将最新的宏观指标同步到 凡科_模块1_学术影响力.html 的静态预渲染字段中"""
    m1_file = os.path.join(SCRIPT_DIR, "凡科_模块1_学术影响力.html")
    if not os.path.exists(m1_file):
        return
    try:
        with open(m1_file, "r", encoding="utf-8") as f:
            content = f.read()
        s = impact_data.get("stats", {})
        feat_cnt = s.get("featured_count", 0)
        esi_cnt = s.get("esi_count", 0)
        role_cnt = s.get("role_count", 0)
        cites = s.get("total_citations", 0)
        h_idx = s.get("h_index", 0)
        pubs = s.get("total_publications", 0)

        # 替换代表作篇数
        content = re.sub(r'<strong id="wxz-cnt-feat">\d+</strong>', f'<strong id="wxz-cnt-feat">{feat_cnt}</strong>', content)
        content = re.sub(r'title="点击筛选 \d+ 篇顶刊代表作"', f'title="点击筛选 {feat_cnt} 篇顶刊代表作"', content)
        # 替换 ESI
        content = re.sub(r'<strong id="wxz-cnt-esi">\d+</strong>', f'<strong id="wxz-cnt-esi">{esi_cnt}</strong>', content)
        # 替换通讯一作
        content = re.sub(r'<strong id="wxz-cnt-role">\d+</strong>', f'<strong id="wxz-cnt-role">{role_cnt}</strong>', content)
        # 替换主要指标
        content = re.sub(r'<div class="wxz-stat-num" id="wxz-stat-cites">[^<]+<span class="wxz-plus">\+</span></div>', f'<div class="wxz-stat-num" id="wxz-stat-cites">{cites:,}<span class="wxz-plus">+</span></div>', content)
        content = re.sub(r'<div class="wxz-stat-num" id="wxz-stat-hindex">\d+</div>', f'<div class="wxz-stat-num" id="wxz-stat-hindex">{h_idx}</div>', content)
        content = re.sub(r'<div class="wxz-stat-num" id="wxz-stat-pubs">\d+</div>', f'<div class="wxz-stat-num" id="wxz-stat-pubs">{pubs}</div>', content)

        with open(m1_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✓ 已自动同步更新凡科模块一静态指标: 代表作={feat_cnt}篇, ESI={esi_cnt}篇, 收录={pubs}篇")
    except Exception as e:
        print(f"[提示] 同步凡科静态指标时跳过: {e}")

def classify_topics(title, keywords_list, journal):
    """结合标题、作者关键词与期刊的多维深度学术主题分类"""
    text = (title + " " + " ".join(keywords_list) + " " + journal).lower()
    matched = []
    for r in THEME_RULES:
        if re.search(r["regex"], text):
            matched.append(r["name"])
    return matched if matched else ["光催化与环境材料"]

def fetch_wos_documents_multi_key(api_keys):
    """使用双 API Key 智能轮换与容错接力拉取全部 WoS 官方文献记录"""
    if not api_keys:
        print("[警告] 未提供任何 WoS API Key，请配置环境变量 WOS_API_KEYS 或本地密钥文件！")
        return []

    keys_pool = api_keys.copy()
    random.shuffle(keys_pool)
    print(f"✓ 启用双 API Key 智能安全轮换架构，共载入 {len(keys_pool)} 组密钥")

    for key_idx, current_key in enumerate(keys_pool):
        key_mask = current_key[:6] + "..." + current_key[-4:] if len(current_key) > 10 else "***"
        print(f"  -> 尝试使用 Key [{key_idx+1}/{len(keys_pool)}] ({key_mask})...")
        all_hits = []
        page = 1
        limit = 50
        total_docs = 0
        success = True

        while True:
            url = f"{BASE_URL}?q=AI%3D({urllib.parse.quote(RESEARCHER_ID)})&limit={limit}&page={page}&sortField=PY+D"
            req = urllib.request.Request(url, headers={
                "X-ApiKey": current_key,
                "Accept": "application/json"
            })
            try:
                with urllib.request.urlopen(req, timeout=25) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    hits = data.get("hits", [])
                    total_docs = data.get("metadata", {}).get("total", 0)
                    if not hits:
                        break
                    all_hits.extend(hits)
                    print(f"     已成功获取第 {page} 页 ({len(all_hits)} / {total_docs} 篇)...")
                    if len(all_hits) >= total_docs:
                        break
                    page += 1
                    time.sleep(0.2)
            except Exception as e:
                print(f"     [警告] Key [{key_idx+1}] 请求异常: {e}")
                success = False
                break

        if success and all_hits:
            print(f"✓ 成功通过 Key [{key_idx+1}] 获取全部 {len(all_hits)} 篇官方文献！")
            return all_hits

        print(f"  [提示] Key [{key_idx+1}] 请求受限或未完成，自动接力切换下一个 Key...")

    return []

def rebuild_from_local(selected_dois, esi_dois, esi_title_norms, corr_titles, fixed_meta, now_str):
    """当离线或网络异常时，从本地已有的 publications.json 快速重新打标并生成数据"""
    if not os.path.exists(PUBS_JSON_FILE):
        print("[错误] 本地不存在 publications.json，无法进行离线构建！")
        return False
    print("\n✓ 正在启用【本地高可用模式】：直接根据本地文献数据重新应用最新清单...")
    with open(PUBS_JSON_FILE, "r", encoding="utf-8") as f:
        pubs = json.load(f)

    for p in pubs:
        doi_lower = (p.get("doi") or "").lower().strip()
        title_norm = normalize_title(p.get("title") or "")
        p["is_featured"] = True if doi_lower in selected_dois else False

        is_esi = False
        if doi_lower in esi_dois or (p.get("doi") and p.get("doi") in esi_dois):
            is_esi = True
        elif title_norm in esi_title_norms:
            is_esi = True
        else:
            for et in esi_title_norms:
                if len(et) > 20 and (et in title_norm or title_norm in et):
                    is_esi = True
                    break
        p["is_esi"] = is_esi

        is_corresponding = False
        if title_norm in corr_titles:
            is_corresponding = True
        else:
            for ct in corr_titles:
                if len(ct) > 20 and (ct in title_norm or title_norm in ct):
                    is_corresponding = True
                    break
        p["is_corresponding"] = is_corresponding

        # 清洗页码字段中的字典脏数据
        p["pages"] = parse_clean_pages(p.get("pages"))

    total_pubs = len(pubs)
    citation_counts = [p.get("citations", 0) for p in pubs]
    total_citations = sum(citation_counts)
    citation_counts.sort(reverse=True)
    h_index = sum(1 for i, cite in enumerate(citation_counts) if cite >= i + 1)
    avg_citations = round(total_citations / total_pubs, 1) if total_pubs > 0 else 0

    year_map = {}
    for p in pubs:
        y = p.get("year")
        if y:
            try:
                y = int(y)
                if y not in year_map:
                    year_map[y] = {"pubs": 0, "cites": 0}
                year_map[y]["pubs"] += 1
                year_map[y]["cites"] += p.get("citations", 0)
            except Exception:
                pass
    all_years = sorted(list(year_map.keys()), reverse=True)
    trend_years = [y for y in all_years if y >= 2016]
    trend_data = []
    for y in sorted(trend_years):
        trend_data.append({
            "year": y,
            "publications": year_map.get(y, {}).get("pubs", 0),
            "citations": year_map.get(y, {}).get("cites", 0)
        })

    topic_distribution = {}
    for tr in THEME_RULES:
        topic_distribution[tr["name"]] = sum(1 for p in pubs if tr["name"] in p.get("topics", []))

    top_journals_stat = []
    for tj in TOP_JOURNALS_STRICT:
        cnt = sum(1 for p in pubs if p.get("top_journal") == tj["abbr"])
        if cnt > 0:
            top_journals_stat.append({
                "abbr": tj["abbr"],
                "name": tj["name"],
                "count": cnt
            })

    impact_data = {
        "scholar": {
            "name_cn": SCHOLAR_NAME_CN,
            "name_en": SCHOLAR_NAME_EN,
            "researcher_id": RESEARCHER_ID,
            "affiliation": AFFILIATION,
            "wos_profile": f"https://www.webofscience.com/wos/author/record/{RESEARCHER_ID}"
        },
        "stats": {
            "total_publications": total_pubs,
            "total_citations": total_citations,
            "h_index": h_index,
            "avg_citations_per_paper": avg_citations,
            "featured_count": sum(1 for p in pubs if p.get("is_featured")),
            "esi_count": sum(1 for p in pubs if p.get("is_esi")),
            "role_count": sum(1 for p in pubs if (p.get("is_first") or p.get("is_corresponding")))
        },
        "year_trend": trend_data,
        "topics_distribution": topic_distribution,
        "top_journals": top_journals_stat,
        "updated_at": "定期自动更新 (每月2日/16日)",
        "source": "Clarivate Web of Science (核心合集)"
    }

    with open(IMPACT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(impact_data, f, ensure_ascii=False, indent=2)

    with open(IMPACT_JS_FILE, "w", encoding="utf-8") as f:
        f.write("/**\n")
        f.write(f" * 王小治教授课题组 · 学术影响力大屏核心数据 (模块一)\n")
        f.write(f" * 数据源自: Clarivate Web of Science 核心合集 | 更新时间: {now_str}\n")
        f.write(" */\n")
        f.write("window.WXZ_IMPACT = ")
        f.write(json.dumps(impact_data, ensure_ascii=False, indent=2))
        f.write(";\n")

    with open(PUBS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(pubs, f, ensure_ascii=False, indent=2)

    with open(PUBS_JS_FILE, "w", encoding="utf-8") as f:
        f.write("/**\n")
        f.write(f" * 王小治教授课题组 · 论文成果展示与多维检索核心数据 (模块二)\n")
        f.write(f" * 成果总量: {len(pubs)} 篇 | 更新时间: {now_str}\n")
        f.write(" */\n")
        f.write("window.WXZ_PUBLICATIONS = ")
        f.write(json.dumps(pubs, ensure_ascii=False, indent=2))
        f.write(";\n")

    update_fanke_module1_static(impact_data)
    print(f"✓ 本地高可用模式已成功更新数据文件！")
    return True

def main():
    print("=" * 68)
    print("🎓 王小治教授课题组学术成果自动化同步系统 (Clarivate WoS 官方版)")
    print(f"学者 ID: {RESEARCHER_ID} | 工作目录: {SCRIPT_DIR}")
    print("=" * 68)

    # 1. 安全载入双 API Keys
    api_keys = load_api_keys()
    if not api_keys:
        print("[错误] 未能检测到任何有效 API Key！")
        print("请在环境变量中设置 WOS_API_KEYS，或在本地配置 wos_secrets.local.json。")
        sys.exit(1)

    # 2. 载入外部治理控制文件
    selected_dois = set(d.lower().strip() for d in load_text_lines(SELECTED_FILE))
    print(f"✓ 载入代表作清单: {len(selected_dois)} 篇")

    esi_lines = load_text_lines(ESI_FILE)
    esi_dois = set()
    esi_title_norms = set()
    for l in esi_lines:
        if l.startswith("10."):
            esi_dois.add(l.lower().strip())
        else:
            esi_title_norms.add(normalize_title(l))
    print(f"✓ 载入 ESI 高被引清单: {len(esi_lines)} 篇 (DOIs: {len(esi_dois)}, 标题: {len(esi_title_norms)})")

    corr_titles = set(normalize_title(t) for t in load_text_lines(CORR_FILE))
    print(f"✓ 载入官方通讯作者标题库: {len(corr_titles)} 篇")

    # 3. 载入本地缓存与固化元数据库 (自动清洗脏数据)
    crossref_cache = {}
    if os.path.exists(CROSSREF_CACHE_FILE):
        try:
            with open(CROSSREF_CACHE_FILE, "r", encoding="utf-8") as f:
                crossref_cache = json.load(f)
            print(f"✓ 载入 Crossref 缓存: {len(crossref_cache)} 条记录")
        except Exception:
            crossref_cache = {}

    fixed_meta = {}
    if os.path.exists(FIXED_CACHE_FILE):
        try:
            with open(FIXED_CACHE_FILE, "r", encoding="utf-8") as f:
                fixed_meta = json.load(f)
            # 清洗历史固化数据中的脏页码
            for k, v in fixed_meta.items():
                if isinstance(v, dict) and "pages" in v:
                    v["pages"] = parse_clean_pages(v.get("pages"))
            print(f"✓ 载入历史固化元数据库: {len(fixed_meta)} 条记录 (脏数据已清洗)")
        except Exception:
            fixed_meta = {}

    # 4. 双 Key 抓取 WoS 官方数据
    now_str = datetime.now().strftime("%Y年%m月%d日")
    all_hits = fetch_wos_documents_multi_key(api_keys)

    if not all_hits:
        print("[提示] 未能从 Clarivate WoS 在线拉取到数据 (可能因离线、网络代理或接口波动)")
        if rebuild_from_local(selected_dois, esi_dois, esi_title_norms, corr_titles, fixed_meta, now_str):
            print("✓ 已顺利基于本地数据库重新应用最新代表作与成果标签完成更新！")
            return
        else:
            print("[错误] 未能从 WoS 获取数据且本地缓存不可用，请检查网络！")
            sys.exit(1)

    print(f"✓ WoS 文献全部拉取完成，共获得 {len(all_hits)} 篇官方核心记录！")

    # 5. 计算宏观学术指标
    citation_counts = []
    year_map = {}
    journal_count_map = {}

    for doc in all_hits:
        c = 0
        for item in doc.get("citations", []):
            if item.get("db") == "WOS":
                c = item.get("count", 0)
                break
        citation_counts.append(c)

        y = doc.get("source", {}).get("publishYear")
        if y:
            try:
                y = int(y)
                if y not in year_map:
                    year_map[y] = {"pubs": 0, "cites": 0}
                year_map[y]["pubs"] += 1
                year_map[y]["cites"] += c
            except Exception:
                pass

        jt = doc.get("source", {}).get("sourceTitle", "")
        if jt:
            jt_clean = to_title_case(clean_html_tags(jt))
            journal_count_map[jt_clean] = journal_count_map.get(jt_clean, 0) + 1

    total_citations = sum(citation_counts)
    total_pubs = len(all_hits)
    citation_counts.sort(reverse=True)
    h_index = sum(1 for i, cite in enumerate(citation_counts) if cite >= i + 1)
    avg_citations = round(total_citations / total_pubs, 1) if total_pubs > 0 else 0

    print("\n" + "-" * 50)
    print("📊 Clarivate Web of Science 核心合集权威指标计算完成:")
    print(f"  • 核心合集收录论文: {total_pubs} 篇")
    print(f"  • Web of Science 总被引频次: {total_citations:,} 次")
    print(f"  • Web of Science H 指数: {h_index}")
    print(f"  • 篇均被引频次: {avg_citations} 次/篇")
    print("-" * 50)

    # 6. 组装与深度清洗论文详细列表 (严格执行 2025 年及以前元数据固化，仅实时刷新引用)
    processed_pubs = []
    all_years = sorted(list(year_map.keys()), reverse=True)
    unassigned_docs = []
    max_fixed_id = 0

    for k, v in fixed_meta.items():
        if isinstance(v, dict) and "id" in v:
            if v["id"] > max_fixed_id:
                max_fixed_id = v["id"]

    for doc in all_hits:
        title_raw = doc.get("title", "")
        title_clean = clean_html_tags(title_raw)
        title_norm = normalize_title(title_clean)

        raw_doi = doc.get("identifiers", {}).get("doi", "")
        doi = ""
        if isinstance(raw_doi, list):
            for d in raw_doi:
                if d and isinstance(d, str):
                    doi = d.strip()
                    break
        elif isinstance(raw_doi, str):
            doi = raw_doi.strip()
        doi_lower = doi.lower()

        # 实时被引次数（始终动态从 WoS 获取最新频次）
        wos_cites = 0
        for item in doc.get("citations", []):
            if item.get("db") == "WOS":
                wos_cites = item.get("count", 0)
                break

        # 期刊与卷期页码清洗
        source_info = doc.get("source", {})
        journal_raw = source_info.get("sourceTitle", "")
        journal_clean = to_title_case(clean_html_tags(journal_raw))

        pub_year = source_info.get("publishYear", 2026)
        try:
            pub_year = int(pub_year)
        except Exception:
            pub_year = 2026

        vol = str(source_info.get("volume", "")).strip()
        iss = str(source_info.get("issue", "")).strip()
        # 使用专业函数提取规范页码或文章号
        pages_str = parse_clean_pages(source_info.get("pages"), source_info.get("articleNumber"))

        # 作者解析与身份识别
        authors_raw = doc.get("names", {}).get("authors", [])
        author_names = []
        is_first_author = False
        is_corresponding = False

        for idx, a in enumerate(authors_raw):
            disp = a.get("displayName") or a.get("wosStandard") or ""
            r_id = a.get("researcherId") or ""
            disp_clean = to_title_case(disp)
            author_names.append(disp_clean)

            # 匹配王小治
            is_wxz = False
            if r_id == RESEARCHER_ID:
                is_wxz = True
            elif re.search(r"wang\s*,?\s*x(iaozhi|\.?\s*z\.?)", disp.lower()):
                if not re.search(r"xiaowei|xian|xiao(?!zhi)", disp.lower()):
                    is_wxz = True

            if is_wxz and idx == 0:
                is_first_author = True

        authors_str = ", ".join(author_names) if author_names else "Wang, Xiaozhi et al."

        # 通讯作者高容错匹配
        if title_norm in corr_titles:
            is_corresponding = True
        else:
            for ct in corr_titles:
                if len(ct) > 20 and (ct in title_norm or title_norm in ct):
                    is_corresponding = True
                    break

        # 重点期刊匹配
        top_j_info = None
        for tj in TOP_JOURNALS_STRICT:
            if re.search(tj["pattern"], journal_clean.lower()):
                if "exclude" in tj and re.search(tj["exclude"], journal_clean.lower()):
                    continue
                top_j_info = tj
                break

        # 代表作判定（严格由当前 selected_doi.txt 指定）
        is_featured = (doi_lower in selected_dois) if doi_lower else False

        # ESI 高被引判定（支持 DOI 和 标题归一化匹配）
        is_esi = False
        if doi_lower in esi_dois or (doi and doi in esi_dois):
            is_esi = True
        elif title_norm in esi_title_norms:
            is_esi = True
        else:
            for et in esi_title_norms:
                if len(et) > 20 and (et in title_norm or title_norm in et):
                    is_esi = True
                    break

        # 提取 WoS authorKeywords 深度分析主题
        wos_kws = doc.get("keywords", {}).get("authorKeywords", [])

        # 固化元数据回填与判定（2025 年及以前的数据执行永久固化）
        fixed_item = fixed_meta.get(doi_lower) or fixed_meta.get(title_norm)
        pub_id = None
        topics = []
        is_already_fixed = False

        if pub_year <= 2025 and fixed_item and isinstance(fixed_item, dict) and fixed_item.get("fixed_v2"):
            # 严格遵循用户指令：2025年及以前的数据，标题、期刊、卷期、作者、主题永久固化（仅引用频次实时刷新）
            pub_id = fixed_item.get("id")
            title_clean = fixed_item.get("title", title_clean)
            authors_str = fixed_item.get("authors", authors_str)
            journal_clean = fixed_item.get("journal", journal_clean)
            vol = fixed_item.get("volume", vol)
            iss = fixed_item.get("issue", iss)
            pages_str = parse_clean_pages(fixed_item.get("pages"), source_info.get("articleNumber"))
            topics = fixed_item.get("topics", [])
            is_already_fixed = True
        else:
            # 2026 年新文献，或尚未完成深度关键词分析的文章：全面提取并标引
            topics = classify_topics(title_clean, wos_kws, journal_clean)
            if fixed_item and isinstance(fixed_item, dict):
                pub_id = fixed_item.get("id")

        # Crossref 补充缺失的卷期页码
        if (not vol or not pages_str) and doi:
            cr_meta = fetch_crossref_metadata(doi, crossref_cache)
            if not vol and cr_meta.get("volume"):
                vol = cr_meta["volume"]
            if not iss and cr_meta.get("issue"):
                iss = cr_meta["issue"]
            if not pages_str and cr_meta.get("pages"):
                pages_str = parse_clean_pages(cr_meta.get("pages"))

        record = {
            "id": pub_id,
            "title": title_clean,
            "authors": authors_str,
            "journal": journal_clean,
            "year": pub_year,
            "volume": vol,
            "issue": iss,
            "pages": pages_str,
            "doi": doi,
            "citations": wos_cites,  # 实时最新被引
            "is_featured": is_featured,
            "is_esi": is_esi,
            "is_first": is_first_author,
            "is_corresponding": is_corresponding,
            "top_journal": top_j_info.get("abbr") if top_j_info else None,
            "top_weight": top_j_info.get("weight", 0) if top_j_info else 0,
            "topics": topics,
            "_raw_date": pub_year
        }

        if pub_id:
            processed_pubs.append(record)
        else:
            unassigned_docs.append(record)

    # 为新增文章按发表年份从早到晚分配连续递增 ID
    unassigned_docs.sort(key=lambda x: (x.get("year", 0), x.get("title", "")))
    curr_new_id = max_fixed_id + 1
    for doc in unassigned_docs:
        doc["id"] = curr_new_id
        curr_new_id += 1
        processed_pubs.append(doc)

    # 成果列表展示排序规则：默认按年份降序 + 终生编号降序
    processed_pubs.sort(key=lambda x: (x.get("year", 0), x.get("id", 0)), reverse=True)

    # 固化元数据：对 2025 年及以前的文献进行永久固化标引（保存 fixed_v2 标志）
    for p in processed_pubs:
        key = (p.get("doi") or "").lower().strip()
        if not key:
            key = normalize_title(p.get("title"))
        if p.get("year", 0) <= 2025:
            fixed_meta[key] = {
                "id": p.get("id"),
                "fixed_v2": True,
                "topics": p.get("topics"),
                "title": p.get("title"),
                "authors": p.get("authors"),
                "journal": p.get("journal"),
                "year": p.get("year"),
                "volume": p.get("volume"),
                "issue": p.get("issue"),
                "pages": p.get("pages"),
                "doi": p.get("doi")
            }

    # 保存缓存
    with open(CROSSREF_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(crossref_cache, f, ensure_ascii=False, indent=2)

    with open(FIXED_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(fixed_meta, f, ensure_ascii=False, indent=2)

    # 7. 生成模块一数据：宏观学术影响力 (impact_data.js & impact_metrics.json)
    trend_years = [y for y in all_years if y >= 2016]
    trend_data = []
    for y in sorted(trend_years):
        trend_data.append({
            "year": y,
            "publications": year_map.get(y, {}).get("pubs", 0),
            "citations": year_map.get(y, {}).get("cites", 0)
        })

    top_journals_stat = []
    for tj in TOP_JOURNALS_STRICT:
        cnt = sum(1 for p in processed_pubs if p.get("top_journal") == tj["abbr"])
        if cnt > 0:
            top_journals_stat.append({
                "abbr": tj["abbr"],
                "name": tj["name"],
                "count": cnt
            })

    topic_distribution = {}
    for tr in THEME_RULES:
        topic_distribution[tr["name"]] = sum(1 for p in processed_pubs if tr["name"] in p.get("topics", []))

    impact_data = {
        "scholar": {
            "name_cn": SCHOLAR_NAME_CN,
            "name_en": SCHOLAR_NAME_EN,
            "researcher_id": RESEARCHER_ID,
            "affiliation": AFFILIATION,
            "wos_profile": f"https://www.webofscience.com/wos/author/record/{RESEARCHER_ID}"
        },
        "stats": {
            "total_publications": total_pubs,
            "total_citations": total_citations,
            "h_index": h_index,
            "avg_citations_per_paper": avg_citations,
            "featured_count": sum(1 for p in processed_pubs if p.get("is_featured")),
            "esi_count": sum(1 for p in processed_pubs if p.get("is_esi")),
            "role_count": sum(1 for p in processed_pubs if (p.get("is_first") or p.get("is_corresponding")))
        },
        "year_trend": trend_data,
        "topics_distribution": topic_distribution,
        "top_journals": top_journals_stat,
        "updated_at": "定期自动更新 (每月2日/16日)",
        "source": "Clarivate Web of Science (核心合集)"
    }

    with open(IMPACT_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(impact_data, f, ensure_ascii=False, indent=2)

    with open(IMPACT_JS_FILE, "w", encoding="utf-8") as f:
        f.write("/**\n")
        f.write(f" * 王小治教授课题组 · 学术影响力大屏核心数据 (模块一)\n")
        f.write(f" * 数据源自: Clarivate Web of Science 核心合集 | 更新时间: {now_str}\n")
        f.write(" */\n")
        f.write("window.WXZ_IMPACT = ")
        f.write(json.dumps(impact_data, ensure_ascii=False, indent=2))
        f.write(";\n")

    print(f"\n✓ 成功导出模块一数据: {IMPACT_JS_FILE}")

    # 8. 生成模块二数据：成果检索与多维筛选 (publications_data.js & publications.json)
    with open(PUBS_JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(processed_pubs, f, ensure_ascii=False, indent=2)

    with open(PUBS_JS_FILE, "w", encoding="utf-8") as f:
        f.write("/**\n")
        f.write(f" * 王小治教授课题组 · 论文成果展示与多维检索核心数据 (模块二)\n")
        f.write(f" * 成果总量: {len(processed_pubs)} 篇 | 更新时间: {now_str}\n")
        f.write(" */\n")
        f.write("window.WXZ_PUBLICATIONS = ")
        f.write(json.dumps(processed_pubs, ensure_ascii=False, indent=2))
        f.write(";\n")

    print(f"✓ 成功导出模块二数据: {PUBS_JS_FILE}")
    update_fanke_module1_static(impact_data)
    print("\n" + "=" * 68)
    print("🎉 Web of Science 官方权威数据治理与同步全部成功！")
    print(f"   • 收录文献总量: {len(processed_pubs)} 篇")
    print(f"   • 代表作已标记: {sum(1 for p in processed_pubs if p.get('is_featured'))} 篇")
    print(f"   • ESI 高被引标记: {sum(1 for p in processed_pubs if p.get('is_esi'))} 篇")
    print(f"   • 第一作者识别: {sum(1 for p in processed_pubs if p.get('is_first'))} 篇")
    print(f"   • 通讯作者识别: {sum(1 for p in processed_pubs if p.get('is_corresponding'))} 篇")
    print(f"   • 6大主题分布: {topic_distribution}")
    print("=" * 68)

if __name__ == "__main__":
    main()
