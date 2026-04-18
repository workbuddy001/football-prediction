# ⚽ 足球预测分析器 — 纯排除法框架

基于赔率变化分析的足球比赛预测系统，使用**纯排除法**（不预测"什么会出"，而是排除"什么不会出"）进行方向判断。

> 📊 **当前版本：V4.1** | 赛前情报分析 + 让球盘深度解读 + 赔付压力矩阵 + 阻盘模式检测 + 赔率变化统计

---

## 🚀 快速开始

### 本地运行

本项目包含**两个独立服务**：

```bash
# 1. 克隆仓库
git clone https://github.com/workbuddy001/football-prediction.git
cd football-prediction

# 2. 安装依赖（实际为零依赖，仅 Python 标准库）
pip install -r requirements.txt

# 3. 启动两个服务
# 服务1：竞彩数据查看（必开）
python sporttery_web.py

# 服务2：分析主站（可选）
python football_web.py 8890
```

### 浏览器访问

| 服务 | 地址 | 说明 |
|------|------|------|
| **竞彩数据** | http://localhost:8899 | 查看竞彩网赔率、赔率变化统计、前瞻数据 |
| **分析主站** | http://localhost:8890 | 赛前情报分析、让球盘解读、投注建议 |

> 指定端口：`python xxx_web.py [端口号]`（不传参数则默认 8899）

### 一键同步脚本

项目根目录有 `sync_to_github.bat`，双击即可自动 commit + push。

---

## 📂 项目结构

```
football-prediction/
├── football_web.py              # 分析主站服务（默认8899）
├── sporttery_web.py             # 竞彩数据服务（默认8899）
├── requirements.txt             # Python依赖（实际为零依赖）
├── render.yaml                  # Render云部署配置
├── sync_to_github.bat           # Windows一键同步脚本
├── CHANGELOG.md                 # 更新日志
├── .gitignore                   # Git忽略规则
│
├── static/js/
│   ├── prematch.js             # ⭐ 赛前情报分析模块（V4，四步推理链）
│   └── handicap.js             # ⭐ 让球盘深度解读模块
│
├── sporttery_data/              # 竞彩API缓存数据
│
└── 分析模板/                     # 分析主站数据目录
    ├── 日期目录/                 #   └── 编号_主队vs客队_源数据.md
    ├── _reviews/                #   └── 复盘记录 JSON
    ├── _upsets.json             # 冷门模式库
    ├── _scores.json             # 近况评分缓存
    └── OUTPUT_TEMPLATE.md        # 分析输出模板
```

**核心文件说明：**
- **`sporttery_web.py`** — 竞彩数据查看服务，数据来自竞彩网API
- **`football_web.py`** — 分析主站服务，支持赛前情报分析+赔付矩阵
- **`static/js/prematch.js`** — 赛前情报前端模块（~650行），四步推理链+赔付矩阵+综合判定
- **`static/js/handicap.js`** — 让球盘独立模块（~344行），六档水位+出口结构
- **无数据库** — 使用 JSON 文件存储数据
- **无需前端构建** — HTML/CSS/JS 独立文件，浏览器直接加载

---

## 🧠 核心功能

### 1. ⭐ 竞彩数据服务（sporttery_web.py）

竞彩网赔率数据查看与变化追踪：

- **胜平负** — 标准盘口完整赔率
- **总进球** — 0-7+球各选项赔率 + 变化次数统计
- **半全场** — 9种半全场选项赔率 + 变化次数统计
- **让球胜平负** — 让球盘口赔率
- **比分赔率** — 最低赔率比分推荐
- **赔率变化统计** — 实时追踪每个选项的变化次数和幅度
  - 红色↑ = 赔率上升（庄家造热方向）
  - 绿色↓ = 赔率下降（庄家推离方向）
- **前瞻数据** — 特征分析、历史交锋、伤停、射手、积分榜

### 2. ⭐ 赛前情报分析（prematch.js V4）

点击比赛详情后自动展示完整的赛前情报，采用**四步推理链**：

```
① 赔率水位分析（标准盘1X2）     → 六档水位分类 + 庄家意图解读
② 让球盘水位分析                → 六档水位分类 + 出口结构(单/双/分散/封锁) + 深度解读
③ 赔付压力矩阵                  → 三方向×双盘口赔付对比 + 庄家最优解推演
④ 交叉验证                      → [不怕]/[不跟]标签 + 三重共振陷阱检测
⑤ 综合判定                      → 五维优先级(阻盘>推离最优解>基本面>双重确认>赔付为准)
```

### 3. ⭐ 赔付压力矩阵

每个赛果在**标准盘和让球盘两个维度**的赔付压力对比：

| 赛果 | 标准盘 | 让球盘 | 综合得分 | 应付压力 |
|------|--------|--------|---------|---------|
| 主胜 | 1.65✅ | 3.00 | 2.37分 | 压力最小 |
| 平局 | 3.75⚠️ | 1.95 | 2.68分 | 中等 |
| 客胜 | 3.90⚠️ | 1.95 | 2.71分 | 较大 |

自动推演：
- **庄家最优解** → 综合最低赔付方向 = 庄家最想看到的结果
- **最怕结果** → 综合最高赔付方向 = 庄家不愿出
- **🔥 推离最优解警报** → 赔率拉高 + 最低赔付 = 庄家真方向
- **🧱 阻盘模式检测** → 标准低赔 + 让球超高水(>3.0) + 基本面同向 = 阻拦真方向

### 4. ⭐ 让球盘六档水位分类（handicap.js）

| 区间 | 档位 | 庄家意图 | 含义 |
|------|------|---------|------|
| >4.2 | 超高水 | 强阻 | 拉高让你不敢买 |
| >3.5 | 高水 | 微阻 | 轻度劝退 |
| >2.8 | 中高水 | 博取高倍 | 高赔诱惑区 |
| >2.0 | 中低水 | 引导 | 合理区间引导 |
| >1.5 | 低水 | 守 | 低赔实盘防守 |
| <1.5 | 超低水 | 确 | 大概率方向 |

**出口结构分析**：单出口 / 双出口 / 分散 / 封锁 — 判断筹码流向集中度。

### 5. 综合判定五维优先级

```
优先级从高到低：

① 🔥🔥 阻盘模式      标准低赔 + 让球超高(>3.0) + 基本面同向 = 真
② 🔥 推离最优解     赔率拉高 + 最低赔付 = 庄家真方向
③ ⚠️ 基本面压制(≥6分) 差距大且与赔付矛盾 → 基本面优先
④ ✅ 双重确认       赔付最优 = 排除法结论一致
⑤ 📊 赔付为准(<4分差) 小差距时以赔付矩阵为第一参考
⑥ 观望             多信号冲突或无法判断
```

### 6. 三方向排除引擎（R1~R8）

| 规则 | 名称 | 说明 |
|------|------|------|
| **R1** | 高赔率排除 | 赔率 > 5.0 排除；> 3.5 大概率排除 |
| **R4** | 历史倾向 | 历史交锋6条以上一致时加分 |
| **R7** | 近况对比 | 主队 vs 客队近况评分差 |
| **R8** | 🔥冷门检测器 | 检测"造热陷阱"：高赔+竞彩巨降+多公司同向 |

### 7. 冷门模式库 🧊

- 复盘时**自动检测爆冷**并分类入库
- 支持4种冷门类型识别：
  - 🔇 **静默型**：竞彩+澳门完全不动
  - 🔄 **反向掩护**：被排除的方向实际打出
  - 🔥 **造热陷阱**：有预警但不够强
  - ❓ **未知**
- 分析时**自动匹配历史相似冷门**（满分78分制），按危险等级提示

### 8. 投注建议系统

| 星级 | 含义 | 建议 |
|------|------|------|
| ★★★★★ | 排除2个只剩1个 | ✅ 建议投注 |
| ★★★★☆ | 排除1个+赔率差大 | ✅ 建议投注 |
| ★★★☆☆ | 排除1个+赔率差小 | 🟡 可小试 |
| ★★☆☆☆ | 有极端冷门信号 | 🚨 谨慎/观望 |
| ☆☆☆☆☆ | 无法判断或矛盾 | ⚪ 观望 |

### 9. 历史复盘

- 每场比赛可录入比分进行复盘验证
- 自动统计命中率
- 复盘失败自动检测是否为冷门 → 加入冷门库

---

## ☁️ 云端部署

### 竞彩数据服务（sporttery_web.py）

由于竞彩数据来自竞彩网API，建议**本地部署**以便数据抓取。

```bash
# 本地部署
python sporttery_web.py 8899
# 访问 http://localhost:8899
```

### 分析主站服务（football_web.py）

推荐部署到云端：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/new?type=web&repo=https://github.com/workbuddy001/football-prediction)

**Render 部署步骤：**
1. 点击上方按钮 → 选择 `workbuddy001/football-prediction` 仓库
2. 设置环境变量：
   - `HOST` = `0.0.0.0`（绑定公网IP，必须！）
   - `PORT` = `8890`（或其他端口）
3. 点击 **Create Web Service**
4. 等待 ~2 分钟自动部署完成

> ⚠️ 必须设置 `HOST=0.0.0.0` 环境变量，否则无法从外部访问！

### VPS 部署（同时运行两个服务）

```bash
# 安装 Git + Python3
apt update && apt install -y git python3

# 克隆代码
git clone https://github.com/workbuddy001/football-prediction.git
cd football-prediction

# 启动竞彩数据服务
nohup python3 sporttery_web.py > sporttery.log 2>&1 &
# 端口：8899

# 启动分析主站
nohup python3 football_web.py 8890 > football.log 2>&1 &
# 端口：8890

# 验证服务运行
netstat -tlnp | grep -E '8899|8890'
```

### systemd 服务管理（推荐）

```bash
# 创建竞彩数据服务
cat > /etc/systemd/system/football-sporttery.service << 'EOF'
[Unit]
Description=Football Sporttery Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/football-prediction
ExecStart=python3 sporttery_web.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 创建分析主站服务
cat > /etc/systemd/system/football-analysis.service << 'EOF'
[Unit]
Description=Football Analysis Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/football-prediction
ExecStart=python3 football_web.py 8890
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动
systemctl enable football-sporttery
systemctl enable football-analysis
systemctl start football-sporttery
systemctl start football-analysis
```

### Docker 部署

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8899 8890
CMD ["sh", "-c", "python sporttery_web.py & python football_web.py 8890"]
```

```bash
docker build -t football-prediction .
docker run -d -p 8899:8899 -p 8890:8890 football-prediction
```

---

## 📊 API 接口

### 竞彩数据服务（端口 8899）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 竞彩数据查看页面 |
| GET | `/api/matches` | 获取已缓存的比赛列表 |
| GET | `/api/match/:id` | 获取指定比赛数据 |
| POST | `/api/fetch/:id` | 抓取指定比赛数据 |

### 分析主站服务（端口 8890）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 执行单场赔率分析 |
| POST | `/api/review` | 保存复盘记录 |
| GET | `/api/reviews` | 查询所有复盘 |
| GET | `/api/upsets` | 查询冷门模式库 |
| GET | `/api/matches` | 获取比赛列表 |
| GET | `/api/data/:date/:id` | 获取源数据 |
| POST | `/api/prematch` | 获取赛前情报分析数据 |

---

## ⚙️ 配置项

### 竞彩数据服务

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | 8899 | 服务端口（通过命令行参数指定）|
| `HOST` | 127.0.0.1 | 绑定地址 |

### 分析主站

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | 8899 | 服务端口（通过命令行参数指定）|
| `HOST` | 127.0.0.1 | 绑定地址（设为 `0.0.0.0` 用于云端部署）|
| `DATA_ROOT` | ./分析模板 | 数据文件根目录 |

> `HOST` 通过环境变量设置：`export HOST=0.0.0.0`

---

## 🛠️ 开发与调试

### 本地开发

```bash
# 竞彩数据服务
python sporttery_web.py       # 默认 8899 端口
python sporttery_web.py 9000 # 指定端口

# 分析主站
python football_web.py       # 默认 8899 端口
python football_web.py 8890 # 指定端口（避免与竞彩服务冲突）
```

修改 JS 文件后重启 Python 服务生效。前端 JS 语法检查：

```bash
node --check static/js/prematch.js
node --check static/js/handicap.js
```

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| 页面空白/报错 | 浏览器 Ctrl+F5 强制清除缓存 |
| "i is not defined" | 循环变量名错误，检查 for 循环体 |
| "XXX is not defined" | var 声明作用域问题，移到函数开头 |
| 端口占用 | `netstat -ano \| findstr :8899` → 杀进程 |
| 中文乱码 | 确保 UTF-8 编码（默认已处理）|
| 竞彩数据为空 | 检查网络连接，确保能访问竞彩网API |
| 分析数据缺失 | 检查 `分析模板/` 目录下是否有对应日期的源数据文件 |

---

## 📝 更新日志

详见 [CHANGELOG.md](./CHANGELOG.md)

---

## 📄 License

MIT License — 自由使用，仅供参考学习。

> ⚠️ **免责声明**：本工具提供的分析结果仅供参考，不构成任何投资建议。足球比赛结果具有不确定性，请理性对待预测结果。
