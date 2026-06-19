# 公网部署说明

这个项目不能只用 GitHub Pages 部署，因为它包含 FastAPI 后端、MySQL、Redis 和 WebSocket。最简单的公网方式是在一台云服务器上用 Docker Compose 运行。

## 一台服务器部署

服务器要求：

- Linux 云服务器，建议 2 核 2G 或以上。
- 已安装 Docker 和 Docker Compose。
- 防火墙开放 `80` 端口。

部署命令：

```bash
git clone https://github.com/jht78781-collab/stock-fund-trend-risk-system.git
cd stock-fund-trend-risk-system
docker compose -f docker-compose.prod.yml up -d --build
```

访问：

```text
http://服务器公网IP
```

## 可选环境变量

可以在项目根目录创建 `.env`：

```env
MYSQL_ROOT_PASSWORD=请改成强密码
MYSQL_DATABASE=stock_analysis
MYSQL_USER=stock_user
MYSQL_PASSWORD=请改成强密码
WEB_PORT=80
CORS_ORIGINS=http://你的域名
```

然后重新启动：

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

## 域名和 HTTPS

如果绑定域名，建议再配置 Nginx Proxy Manager、Caddy 或云厂商负载均衡来启用 HTTPS。

## 实时性说明

后端 WebSocket 每 5 秒重新请求行情并推送给前端，但行情是否变化取决于交易时段和上游数据源刷新频率。页面会显示 `source` 和 `source_timestamp`，用于判断行情源和真实行情时间。

## 风险提示

本系统所有预测、概率和风险等级仅供学习研究，不构成投资建议。

