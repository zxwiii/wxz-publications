# 王小治教授课题组 · Web of Science 官方权威学术成果系统

> **Clarivate Web of Science (科睿唯安核心合集官方数据库) 权威直连自动化展示系统**  
> 课题组官方网址：[https://wxz.group](https://wxz.group) | 学者 ResearcherID：[PDX-5463-2025](https://www.webofscience.com/wos/author/record/PDX-5463-2025)

---

## 一、 系统架构与学术特性

本系统专为**扬州大学王小治教授课题组**深度定制，视觉设计契合 [wxz.group](https://wxz.group) 科技宝蓝（`#1e50ae`）与天青色（`#0284c7`）风格，完美展示课题组在**环境材料、土壤修复与化学工程**等领域的学术成果与学术影响力。

### 🌟 核心特色与学术规范：
1. **权威直连与实时动态指标**：
   - 官方直通 **Clarivate Web of Science Starter API**，实时计算收录文献、总被引频次与 H 指数；
   - 近十年发文量与被引频次柱状图完全由数据动态驱动，全自动无感更新。
2. **严格北京时间与呼吸绿灯指示器（实时状态一览无余）**：
   - 同步脚本绑定严格**北京时间（`Asia/Shanghai`, UTC+8）**，杜绝云端 Linux 零时区导致日期倒退；
   - 页面左下角内置纯 CSS 原生绿色呼吸脉冲灯（`#10b981`），实时显示数据更新日期（如 `数据自动更新至：2026年10月26日`），用户和访客可直观确认是否读到最新文件。
3. **Commit SHA 瞬时版本号机制（彻底消灭公共 CDN 7 天强缓存）**：
   - 前端加载时优先探测 GitHub 最新 Commit SHA，直接拼接绝对唯一哈希版本号请求 jsDelivr 高速 CDN；
   - 无论公共 CDN 缓存策略如何强硬，每次推送后版本号全球唯一，**旧缓存命中率归零，最新成果全网秒级呈现**；
   - 具备 1.0 秒超时自动降级至主干及 Gitee 官方跨域 API v5（Base64 纯前端解码执行，免去服务器存文件）。
4. **高精度 6 大特色环境材料化工研究方向**：
   - 融合论文标题、期刊名称与 Web of Science 官方作者关键词（`authorKeywords`）精准判定：
     - `光催化与环境材料`
     - `高级氧化与铁循环`
     - `重金属吸附与修复`
     - `生物炭与多孔材料`
     - `土壤生态与碳氮循环`
     - `新兴污染物与健康` (微塑料、抗生素、室内甲醛净化)
5. **历史数据固化机制（2025年及以前）**：
   - 2025 年及以前的历史文献元数据已固化在 `wos_fixed_metadata.json` 中；
   - 每次同步仅动态刷新其实时被引频次，保证历史数据永不偏移、极速加载。
6. **精选成果多维联动筛选与学术级规范**：
   - 支持按：`【全部】`、`【★ 代表作 Selected】`、`【🔥 ESI高被引】`、`【👥 通讯/第一作者】` 精准过滤；
   - 纯正学术纯数字编号（如 `202. Triple-Network...`，无 `#` 符号），每张卡片展示直达官方 DOI 链接与一键复制学术引用按钮。
7. **双 API Key 智能轮换与零密钥泄露**：
   - 系统支持双 API Key 智能随机轮换与配额耗尽接力；
   - **代码零明文泄露**：API Keys 绝对不以明文形式上传到 GitHub/Gitee，本地从私密忽略文件读取，云端由 GitHub Secrets 环境变量安全注入。
8. **凡科网（CMS）单模块双屏合一（< 50,000 字符限制）**：
   - 提供合一版代码 [`凡科_学术成果系统_双模块合一版.html`](file:///E:/OneDrive%20-%20Jiangsu%20University/工作/5.实验室管理/网站/wxz/wxz-pub/凡科_学术成果系统_双模块合一版.html)，体积为 **49,211 字符**，严格低于凡科网 50,000 字符限制；
   - 凡科网后台只需放入一个代码插件即可同时展现完整影响力大屏与成果检索系统，消除两个独立模块的高度错位。

---

## 二、 核心文件清单

```text
wxz-pub/
├── .github/workflows/update_publications.yml  # GitHub Actions 定时自动化同步工作流
├── 凡科_学术成果系统_双模块合一版.html         # 凡科网首选！单模块双屏合一版 (<50,000字符)
├── 凡科_模块1_学术影响力.html                 # 独立模块一：学术影响力宏观大屏
├── 凡科_模块2_成果与筛选.html                 # 独立模块二：成果展示与多维检索
├── preview_all.html                           # 本地免跨域双击全景预览页面
├── sync_wos.py                                # WoS 官方数据抓取与治理引擎（双 Key 轮换）
├── make_unified_html.py                       # 自动合成合一版 HTML 并做严格语法与字符校验
├── build_preview.py                           # 自动构建本地全景预览单页
├── corresponding_titles.txt                   # 官方通讯作者论文标题库（113篇）
├── selected_doi.txt                           # 自定义重点代表作 DOI 库（包含 ACS Nano 等）
├── esi_top_1_percent.txt                      # ESI 高被引论文标题库
├── wos_fixed_metadata.json                    # 固化历史文献数据库 (脏数据已清洗)
├── crossref_cache.json                        # 卷期页码缓存数据库
├── publications_data.js                       # 前端成果全量数据文件
├── impact_data.js                             # 前端学术影响力指标数据文件
└── README.md                                  # 系统运维与部署手册
```

---

## 三、 GitHub 仓库端：配置与修改指南

### 1. 配置安全 Secrets（注入 WoS API Key 与 Gitee 密钥）
为了防止 API Key 泄露到公开网络，系统严格通过 GitHub Secrets 机制注入：
1. 访问 GitHub 仓库页面：`https://github.com/zxwiii/wxz-publications`；
2. 点击顶部导航栏 **Settings** $\rightarrow$ 左侧菜单 **Secrets and variables** $\rightarrow$ **Actions**；
3. 点击绿色按钮 **New repository secret**，依次添加以下变量：

| Secret 名称 | 填入内容 | 说明 |
| :--- | :--- | :--- |
| **`WOS_API_KEY_1`** | `<您的第1组 WoS API 密钥>` | 必填。科睿唯安官方 Starter API 主密钥 |
| **`WOS_API_KEY_2`** | `<您的第2组 WoS API 密钥>` | 必填。科睿唯安官方 Starter API 备用密钥（智能轮换接力） |
| **`GITEE_USER`** | `zxwiii` | 选填。Gitee 用户名（用于镜像推送国内极速节点） |
| **`GITEE_REPO`** | `wxz-publications` | 选填。Gitee 仓库名 |
| **`GITEE_TOKEN`** | `<您的 Gitee 私人令牌>` | 选填。Gitee 个人设置 $\rightarrow$ 私人令牌 生成（勾选 `projects` 权限） |

> [!IMPORTANT]
> **安全声明**：GitHub Secrets 中的内容采用银行级加密，任何人都无法查看明文。本地敏感文件 `wos_secrets.local.json` 已被 `.gitignore` 保护，绝不会被上传。

### 2. 修改定时同步时间或手动一键触发
在 `.github/workflows/update_publications.yml` 中：
- **修改定时周期**：找到 `cron: '0 2 2,16 * *'`：
  - 当前设定为：每月 2 号与 16 号北京时间上午 10:00（UTC 02:00）自动执行；
  - 若希望改为每月 1 号和 15 号，只需修改为 `cron: '0 2 1,15 * *'` 并推送到仓库。
- **手动立即运行同步**：
  - 打开 GitHub 仓库页面，点击顶部 **Actions** 标签；
  - 在左侧选择 **自动同步王小治课题组学术成果 (Sync WoS & Mirror to Gitee)**；
  - 点击右侧 **Run workflow** 下拉按钮，点击绿色 **Run workflow** 即可立即触发一次完整同步。

### 3. 如何推送本地代码更新到 GitHub
在本地修改了 `selected_doi.txt`、`corresponding_titles.txt` 或运行了生成脚本后：
```bash
git add .
git commit -m "Update publication metadata and unified template"
git push origin main
```
云端会自动触发工作流或保留更新，前端通过 Commit SHA 机制会瞬间读取到本次提交的最新内容。

---

## 四、 前端（凡科网 / 官网）部署与修改指南

### 推荐方案：使用【双模块合一版】（凡科网单个插件搞定）
为了避免在凡科网中创建两个插件带来的加载顺序不一致或高度不对齐问题，强烈推荐使用合一版：

1. **获取代码**：
   - 打开本地 [`凡科_学术成果系统_双模块合一版.html`](file:///E:/OneDrive%20-%20Jiangsu%20University/工作/5.实验室管理/网站/wxz/wxz-pub/凡科_学术成果系统_双模块合一版.html)；
   - 使用文本编辑器（如 VS Code、记事本）打开，按 `Ctrl + A` 全选，按 `Ctrl + C` 复制全部代码（共 49,211 字符）。
2. **粘贴到凡科网后台**：
   - 登录凡科建站后台，进入学术成果/科研论文页面；
   - 在页面中添加一个“**插件代码 / HTML代码**”模块；
   - 清空原有内容，将复制的代码粘贴进去；
   - 将插件宽度设置为 100%（或适应 1200px 版心），保存并发布网页。
3. **前端修改需求指引**：
   - **如果修改了样式/配色**：在 `凡科_模块1_学术影响力.html` 或 `凡科_模块2_成果与筛选.html` 的 `<style>` 标签中修改对应的 HEX 颜色代码，然后双击运行 `make_unified_html.py`，重新将生成的合一版 HTML 粘贴到凡科网即可。
   - **如果更新了代表作或通讯作者名单**：
     - 在 `selected_doi.txt` 中添加新代表作的 DOI；
     - 在 `corresponding_titles.txt` 中添加新通讯作者论文的英文标题；
     - 运行 `python sync_wos.py`，再运行 `python make_unified_html.py` 即可。

---

## 五、 如何确认前台已成功读取最新数据？

打开前台网页后，观察两个核心细节即可确认数据是否最新：
1. **绿色脉冲呼吸灯**：
   - 位于学术影响力面板左下角，持续散发淡绿色柔和呼吸光芒（`#10b981`），代表云端服务处于实时激活状态；
2. **实时更新日期**：
   - 呼吸灯后方明确显示：`数据自动更新至：2026年10月26日`；
   - 此日期并非固定文字，而是前端 JS 在拉取到最新数据后动态提取填入；只要日期与最新推送日期一致，即代表浏览器已 100% 读取到最新文件，无任何缓存延迟！
