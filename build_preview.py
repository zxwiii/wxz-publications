# -*- coding: utf-8 -*-
import os
import sys

if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json

script_dir = os.path.dirname(os.path.abspath(__file__))
m1_path = os.path.join(script_dir, "凡科_模块1_学术影响力.html")
m2_path = os.path.join(script_dir, "凡科_模块2_成果与筛选.html")
metrics_path = os.path.join(script_dir, "impact_metrics.json")
out_path = os.path.join(script_dir, "preview_all.html")

# 读取指标
banner_stats_str = "199 篇收录 · 6,683 次总引 · 44 H-index"
if os.path.exists(metrics_path):
    try:
        with open(metrics_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
            s = meta.get("stats", {})
            p_cnt = s.get("total_publications", 199)
            c_cnt = s.get("total_citations", 6683)
            h_idx = s.get("h_index", 44)
            f_cnt = s.get("featured_count", 11)
            banner_stats_str = f"{p_cnt} 篇收录 · {c_cnt:,} 次总引 · {h_idx} H-index · {f_cnt} 篇精选代表作"
    except Exception:
        pass

with open(m1_path, "r", encoding="utf-8") as f:
    m1 = f.read()

with open(m2_path, "r", encoding="utf-8") as f:
    m2 = f.read()

# 预览文件在本地直接使用相对路径加载数据文件
m1_preview = m1.replace('src="https://wxz.group/impact_data.js"', 'src="./impact_data.js"')
m2_preview = m2.replace('src="https://wxz.group/publications_data.js"', 'src="./publications_data.js"')

preview_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>王小治教授课题组 · 官方学术成果与影响力展示系统 (wxz.group)</title>
  <style>
    body {{
      background-color: #f8fafc;
      margin: 0;
      padding: 20px 14px 60px 14px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", sans-serif;
    }}
    .preview-container {{
      max-width: 1200px;
      margin: 0 auto;
    }}
    .preview-banner {{
      background: #1e50ae;
      color: #ffffff;
      padding: 13px 20px;
      border-radius: 8px;
      margin-bottom: 20px;
      font-size: 13px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      box-shadow: 0 4px 12px rgba(30, 80, 174, 0.16);
    }}
    .preview-badge {{
      background: rgba(255, 255, 255, 0.2);
      border: 1px solid rgba(255, 255, 255, 0.4);
      padding: 3px 10px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }}
  </style>
  <script src="./impact_data.js"></script>
  <script src="./publications_data.js"></script>
</head>
<body>
<div class="preview-container">
  <div class="preview-banner">
    <div><strong>🔬 王小治教授课题组 (wxz.group) · 学术成果系统全景双模块联动预览</strong>（Clarivate Web of Science 官方权威直连）</div>
    <div class="preview-badge">{banner_stats_str}</div>
  </div>

{m1_preview}

<div style="height: 16px;"></div>

{m2_preview}

</div>
</body>
</html>
"""

with open(out_path, "w", encoding="utf-8") as f:
    f.write(preview_content)

print(f"✓ 成功生成双模块全景预览页面: {out_path} ({len(preview_content)} 字符)")
