# ⚽ 足球预测分析器 — 纯排除法框架

基于赔率变化分析的足球比赛预测系统，使用**纯排除法**（不预测"什么会出"，而是排除"什么不会出"）进行方向判断。

> 📊 **当前版本：V3.4.x** | 内置 R1~R8 排除规则 + 冷门模式库 + 三方向排除引擎

---

## 🚀 快速开始

### 本地运行

```bash
# 1. 克隆仓库
git clone https://github.com/workbuddy001/football-prediction.git
cd football-prediction

# 2. 安装依赖
pip install -r requirements.txt  # 实际上本项目零依赖，仅 Python 标准库

# 3. 启动服务
python football_web.py

# 4. 打开浏览器
# http://localhost:8899
```

> 指定端口：`python football_web.py 9000`（默认 8899）

### 一键同步脚本

项目根目录有 `sync_to_github.bat`，双击即可自动 commit + push。

---

## 📂 项目结构

```
football-prediction/
├── football_web.py          # 主程序（Web服务器 + 前端 + 后端API）
├── requirements.txt         # Python依赖（实际为零依赖）
├── render.yaml              # Render云部署配置
├── sync_to_github.bat       # Windows一键同步脚本
├── .gitignore               # Git忽略规则
│
└── 分析模板/                 # 数据目录
    ├── 日期目录/              #   └── 编号_主队vs客队_源数据.md
    ├── _reviews/             #   └── 复盘记录 JSON
    ├── _upsets.json          # 冷门模式库
    ├── _scores.json          # 近况评分缓存
    └── OUTPUT_TEMPLATE.md    # 分析输出模板
```

**核心文件说明**：
- **`football_web.py`** — 全栈单文件应用（~3700行），包含所有功能
- **无数据库** — 使用 JSON 文件存储复盘记录和冷门库
- **无需前端构建** — HTML/CSS/JS 全部内嵌在 Python 中

---

## ☁️ 云端部署

### 方式一：Render（推荐免费）

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://dashboard.render.com/new?type=web&repo=https://github.com/workbuddy001/football-prediction)

**步骤：**
1. 点击上方按钮 → 选择 `workbuddy001/football-prediction` 仓库
2. 设置环境变量：
   - `HOST` = `0.0.0.0`（绑定公网IP，必须！）
3. 点击 **Create Web Service**
4. 等待 ~2 分钟自动部署完成

> ⚠️ 必须设置 `HOST=0.0.0.0` 环境变量，否则无法从外部访问！

### 方式二：手动 VPS 部署

```bash
# 安装 Git + Python3
apt update && apt install -y git python3

# 克隆代码
git clone https://github.com/workbuddy001/football-prediction.git
cd football-prediction

# 后台运行
nohup python3 football_web.py &

# 或用 systemd 管理（推荐）
cat > /etc/systemd/system/football.service << 'EOF'
[Unit]
Description=Football Prediction Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/football-prediction
ExecStart=python3 football_web.py 8899
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl enable football
systemctl start football
```

### 方式三：Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8899
CMD ["python", "football_web.py"]
```

```bash
docker build -t football-prediction .
docker run -d -p 8899:8899 football-prediction
```

---

## 🧠 核心功能

### 1. 三方向排除引擎（R1~R8）

| 规则 | 名称 | 说明 |
|------|------|------|
| **R1** | 高赔率排除 | 赔率 > 5.0 排除；> 3.5 大概率排除 |
| **R4** | 历史倾向 | 历史交锋6条以上一致时加分 |
| **R7** | 近况对比 | 主队 vs 客队近况评分差 |
| **R8** | 🔥冷门检测器 | 检测"造热陷阱"：高赔+竞彩巨降+多公司同向 |

### 2. 冷门模式库 🧊

- 复盘时**自动检测爆冷**并分类入库
- 支持4种冷门类型识别：
  - 🔇 **静默型**：竞彩+澳门完全不动
  - 🔄 **反向掩护**：被排除的方向实际打出
  - 🔥 **造热陷阱**：有预警但不够强
  - ❓ **未知**
- 分析时**自动匹配历史相似冷门**（满分78分制），按危险等级提示

### 3. 投注建议系统

| 星级 | 含义 | 建议 |
|------|------|------|
| ★★★★★ | 排除2个只剩1个 | ✅ 建议投注 |
| ★★★★☆ | 排除1个+赔率差大 | ✅ 建议投注 |
| ★★★☆☆ | 排除1个+赔率差小 | 🟡 可小试 |
| ★★☆☆☆ | 有极端冷门信号 | 🚨 谨慎/观望 |
| ☆☆☆☆☆ | 无法判断或矛盾 | ⚪ 观望 |

### 4. 历史复盘

- 每场比赛可录入比分进行复盘验证
- 自动统计命中率
- 复盘失败自动检测是否为冷门 → 加入冷门库

---

## 📊 API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/analyze` | 执行单场赔率分析 |
| POST | `/api/review` | 保存复盘记录 |
| GET | `/api/reviews` | 查询所有复盘 |
| GET | `/api/upsets` | 查询冷门模式库 |
| GET | `/api/matches` | 获取比赛列表 |
| GET | `/api/data/:date/:id` | 获取源数据 |

---

## ⚙️ 配置项

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | 8899 | 服务端口（通过命令行参数指定） |
| `HOST` | 127.0.0.1 | 绑定地址（设为 `0.0.0.0` 用于云端部署） |
| `DATA_ROOT` | ./分析模板 | 数据文件根目录 |

> `HOST` 通过环境变量设置：`export HOST=0.0.0.0`

---

## 🛠️ 开发与调试

### 本地开发

```bash
python football_web.py       # 启动（默认8899端口）
python football_web.py 9000  # 指定端口
```

修改 `football_web.py` 后重启生效（无需编译）。

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| 页面空白/报错 | 浏览器 Ctrl+F5 强制清除缓存 |
| 端口占用 | `netstat -ano \| findstr :8899` → 杀进程 |
| 中文乱码 | 确保 UTF-8 编码（默认已处理） |
| 数据加载失败 | 检查 `分析模板/` 目录下是否有对应日期的源数据文件 |

---

## 📝 更新日志

### V3.4 (2026-04-12)
- ✨ 新增 **冷门模式库**（Upset Pattern Library）：复盘自动检测爆冷入库
- ✨ 新增 **相似匹配算法**：78分制5维匹配（赔率+基本面+联赛）
- ✨ 新增 **冷门模式浏览页面** + **历史复盘页面**
- 🔥 **R8 冷门检测器增强**：⚡极端信号降星级+红色预警横幅+观望建议

### V3.3 (2026-04-12)
- 🔥 R8 极端冷门信号影响结论：降星+橙色标记
- 🔥 投注建议强化：极端冷门→🚨观望建议
- 🔥 冷门预警横幅覆盖所有三方向

### V3.2 (2026-04-12)
- 🔧 修复 JSON.parse 双重解析陷阱
- 🔧 修复 30家赔率遍历索引（ri=0 开始）
- ✅ 排除引擎完整实现（R1/R4/R7/R8）

---

## 📄 License

MIT License — 自由使用，仅供参考学习。

> ⚠️ **免责声明**：本工具提供的分析结果仅供参考，不构成任何投资建议。足球比赛结果具有不确定性，请理性对待预测结果。
