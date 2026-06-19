# 基于多源金融数据的股票基金趋势分析与风险评估系统

第一阶段为股票分析 MVP，暂不做完整基金预测。

## 项目目录

```text
stock-fund-trend-risk-system/
  backend/
    app/
      api/v1/endpoints/      # FastAPI 路由与 WebSocket
      core/                  # 配置、数据库、Redis 缓存
      models/                # SQLAlchemy 模型
      repositories/          # MySQL 读写
      schemas/               # Pydantic 响应模型
      services/              # AKShare、技术指标、预测规则
      utils/                 # 日期等工具函数
    requirements.txt
    .env.example
  frontend/
    src/
      api/
      components/
      styles/
      types/
      views/
  docs/
    API.md
  docker-compose.yml
```

## 功能范围

- FastAPI 后端。
- AKShare 股票实时行情、股票搜索、历史日 K 数据。
- 技术指标：`MA5`、`MA10`、`MA20`、`MACD`、`RSI`。
- 简单规则预测：上涨概率、下跌概率、风险等级、预测理由。
- Redis 缓存行情和历史数据。
- MySQL 保存股票基础信息、历史行情、预测记录。
- WebSocket 每 5 秒推送行情变化。
- 实时行情返回 `source` 和 `source_timestamp`，用于区分后端查询时间和上游真实行情时间。
- 所有预测结果包含风险提示：仅供学习研究，不构成投资建议。
- Vue3 + TypeScript + Element Plus + ECharts 前端 MVP。

## 启动依赖

在项目根目录启动 MySQL 和 Redis：

```powershell
docker compose up -d
```

如果本机已经有 MySQL 占用 `3306`，请修改 `docker-compose.yml` 端口映射，或在 `backend/.env` 中改成已有 MySQL 的账号、密码、库名。Redis 未启动时后端会临时使用内存缓存，但生产或正式联调应启动 Redis。

Windows 本地也可以使用 winget 安装 Redis：

```powershell
winget install --id taizod1024.redis-windows-fork --exact
redis-server --port 6379
```

## 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端文档：

- OpenAPI：`http://127.0.0.1:8000/docs`
- 接口说明：[docs/API.md](docs/API.md)

## 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认访问：`http://127.0.0.1:5173`

## 常用接口

```text
GET /api/v1/stocks/search?keyword=000001
GET /api/v1/stocks/000001/quote
GET /api/v1/stocks/000001/history
GET /api/v1/stocks/000001/analysis
GET /api/v1/stocks/000001/predictions
WS  /api/v1/ws/stocks/000001
```

## 数据来源说明

本 MVP 优先使用 AKShare 获取沪深京 A 股实时行情与历史 K 线数据。当前本机访问 AKShare 依赖的部分东方财富批量接口不稳定，因此后端加入了真实行情兜底链路：东方财富单股票接口、腾讯实时行情、腾讯历史 K 线。行情数据可能受上游接口、交易时间、网络环境影响产生延迟或缺失。
如果请求返回 `502` 且详情指向 `eastmoney.com` 或代理连接失败，通常是当前网络无法访问 AKShare 依赖的东方财富接口。

开发环境可在 `backend/.env` 中设置 `ENABLE_FIXTURE_FALLBACK=true`，当 AKShare 和东方财富接口都不可用时使用示例数据完成前后端联调。示例数据只用于本地演示，真实分析应关闭该开关。

实时性说明：后端和 WebSocket 会按配置周期重新请求行情，但上游是否返回新价格取决于交易时段和数据源刷新频率。请以接口返回的 `source_timestamp` 判断行情源的实际时间。

## 风险提示

本系统所有预测、概率和风险等级仅供学习研究，不构成投资建议。
