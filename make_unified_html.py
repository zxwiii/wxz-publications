# -*- coding: utf-8 -*-
"""
构建凡科网单模块双屏合一版 HTML (凡科_学术成果系统_双模块合一版.html)
- 完整保留模块一（4大核心指标卡片+近10年柱状图+6大主题条形图+重点顶刊）与模块二（搜索+四维筛选+双语切换+论文列表）
- 智能压缩空白与注释，确保总字符数 (~44,600) 与 UTF-8 字节数 (~46,400) 均严格低于凡科 50,000 上限
- 智能双模加载：本地双击打开 (file://) 毫秒级直读本地 JS；线上访问优先走国内极速公共 CDN (直通 GitHub 仓库)
"""
import os
import re

script_dir = os.path.dirname(os.path.abspath(__file__))
m1_path = os.path.join(script_dir, "凡科_模块1_学术影响力.html")
m2_path = os.path.join(script_dir, "凡科_模块2_成果与筛选.html")
out_path = os.path.join(script_dir, "凡科_学术成果系统_双模块合一版.html")

with open(m1_path, "r", encoding="utf-8") as f:
    m1 = f.read().replace("\r\n", "\n")

if ".wxz-jpill.acsnano" not in m1:
    m1 = m1.replace(
        "#wxz-impact-app .wxz-jpill.wr { border-color: #5eead4 !important; color: #0f766e !important; }",
        "#wxz-impact-app .wxz-jpill.wr { border-color: #5eead4 !important; color: #0f766e !important; }\n  #wxz-impact-app .wxz-jpill.acsnano { border-color: #fcd34d !important; color: #b45309 !important; }"
    )
    with open(m1_path, "w", encoding="utf-8") as f:
        f.write(m1)

with open(m2_path, "r", encoding="utf-8") as f:
    m2 = f.read().replace("\r\n", "\n")

# 1. 完整切片提取模块一与模块二 HTML
m1_html = m1[m1.index('<div id="wxz-impact-app">'):m1.index('<style>')].strip()
m2_html = m2[m2.index('<div id="wxz-pub-root"'):m2.index('<style>')].strip()

# 2. 提取并压缩 CSS
def compact_css(css_str):
    css_str = re.sub(r'/\*[\s\S]*?\*/', '', css_str)
    css_str = css_str.replace(' !important', '')
    css_str = re.sub(r'\s+', ' ', css_str)
    css_str = re.sub(r'\s*([\{\}:;,])\s*', r'\1', css_str)
    css_str = css_str.replace(';}', '}\n')
    return css_str.strip()

m1_css = compact_css(m1[m1.index('<style>') + 7:m1.index('</style>')])
m2_css = compact_css(m2[m2.index('<style>') + 7:m2.index('</style>')])

# 3. 完整切片提取模块一与模块二核心渲染 JS
m1_js_start = m1.index("function renderImpactUI()")
m1_js_end = m1.index("  // ", m1_js_start)
m1_render_fn = m1[m1_js_start:m1_js_end].strip()

m2_js_start = m2.index("var RAW_DATA = [];")
m2_js_end = m2.index("  // 智能多级容灾数据加载链路", m2_js_start)
m2_core_js = m2[m2_js_start:m2_js_end].strip()

raw_unified = f"""<div id="wxz-unified-app">
{m1_html}
{m2_html}
</div>
<style>
#wxz-unified-app {{
  width: 100% !important;
  max-width: 1200px !important;
  margin: 0 auto 30px auto !important;
  padding: 0 !important;
  box-sizing: border-box !important;
}}
#wxz-unified-app *, #wxz-unified-app *::before, #wxz-unified-app *::after {{
  box-sizing: border-box !important;
}}
{m1_css}
{m2_css}
</style>
<script>
window.WxzImpactHelper = {{
  filter: function(type, val) {{
    if (window.WxzPubApp && window.WxzPubApp.toggleFilter) {{
      window.WxzPubApp.toggleFilter(type, val);
      var target = document.getElementById("wxz-pub-root");
      if (target) {{
        target.scrollIntoView({{ behavior: "smooth", block: "start" }});
      }}
    }}
  }}
}};

(function() {{
  {m1_render_fn}
  {m2_core_js}

  var cacheVer = "?v=" + Math.floor(Date.now() / 60000);
  var isLocalFile = (window.location.protocol === "file:");
  var BASES = isLocalFile ? [
    "./",
    "https://testingcf.jsdelivr.net/gh/zxwiii/wxz-publications@main/",
    "https://fastly.jsdelivr.net/gh/zxwiii/wxz-publications@main/"
  ] : [
    "https://testingcf.jsdelivr.net/gh/zxwiii/wxz-publications@main/",
    "https://fastly.jsdelivr.net/gh/zxwiii/wxz-publications@main/",
    "https://cdn.jsdelivr.net/gh/zxwiii/wxz-publications@main/",
    "https://wxz.group/",
    "./"
  ];

  var impactRendered = false;
  var pubsRendered = false;

  function checkAndRender() {{
    if (window.WXZ_IMPACT && !impactRendered) {{
      impactRendered = true;
      renderImpactUI();
    }}
    if (window.WXZ_PUBLICATIONS && !pubsRendered) {{
      pubsRendered = true;
      WxzPubApp.init();
    }}
  }}

  function loadScript(url, cb) {{
    var s = document.createElement("script");
    s.src = url;
    var done = false;
    function finish() {{
      if (done) return;
      done = true;
      cb();
    }}
    s.onload = finish;
    s.onerror = finish;
    document.head.appendChild(s);
    setTimeout(finish, 2500);
  }}

  function tryBaseIndex(idx) {{
    checkAndRender();
    if ((impactRendered && pubsRendered) || idx >= BASES.length) return;

    var base = BASES[idx];
    var suffix = (base === "./" && isLocalFile) ? "" : cacheVer;
    var pending = 0;

    function onPartDone() {{
      pending--;
      checkAndRender();
      if (pending <= 0 && (!impactRendered || !pubsRendered)) {{
        tryBaseIndex(idx + 1);
      }}
    }}

    if (!window.WXZ_IMPACT) {{
      pending++;
      loadScript(base + "impact_data.js" + suffix, onPartDone);
    }}
    if (!window.WXZ_PUBLICATIONS) {{
      pending++;
      loadScript(base + "publications_data.js" + suffix, onPartDone);
    }}
    if (pending === 0) {{
      checkAndRender();
    }}
  }}

  tryBaseIndex(0);
}})();
</script>
"""

# 清理注释与多余缩进空白，精简根选择器别名
compacted = re.sub(r'<!--[\s\S]*?-->', '', raw_unified)
compacted = re.sub(r'(?m)^\s*//.*$', '', compacted)
compacted = re.sub(r'(?m)^[ \t]+', '', compacted)
compacted = re.sub(r'\n{2,}', '\n', compacted)
compacted = compacted.replace('wxz-impact-app', 'wxz-i').replace('wxz-pub-root', 'wxz-p')

header_comment = "<!-- 王小治教授课题组 (wxz.group) · 学术成果与影响力系统【双模块合一版 | 凡科单模块即插即用】 -->\n"
final_content = header_comment + compacted.strip() + "\n"

with open(out_path, "w", encoding="utf-8") as f:
    f.write(final_content)

print(f"SUCCESS: {out_path} ({len(final_content)} chars, {len(final_content.encode('utf-8'))} bytes)")
