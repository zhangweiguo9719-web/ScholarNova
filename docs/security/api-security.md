# API 安全设计文档

## 1. 概述

ScholarAgent API 采用多层安全防护策略，包括请求验证、速率限制、SSRF 防护、日志脱敏等措施，确保系统在 MVP 阶段具备基本的安全保障。

## 2. 安全架构

```
客户端请求
    │
    ▼
┌─────────────────────────────────────┐
│  RequestValidationMiddleware        │  请求大小验证
│  (限制请求体 <= 10MB)               │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  SecurityHeadersMiddleware          │  安全响应头
│  (X-Content-Type-Options, etc.)     │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  CORSMiddleware                     │  跨域控制
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Rate Limiter                       │  速率限制
│  (搜索 30/min, 分析 10/min)         │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Pydantic Schema Validation         │  输入校验
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  SSRF Protection (URL Validation)   │  SSRF 防护
└─────────────────────────────────────┘
    │
    ▼
    业务逻辑
```

## 3. 速率限制

### 3.1 算法

采用滑动窗口算法，基于内存存储（MVP 阶段）。每个 IP 地址独立计数。

### 3.2 限制规则

| 端点类型 | 限制 | 窗口 |
|---------|------|------|
| 搜索请求 | 30 次/分钟 | 滑动 60 秒 |
| 分析请求 | 10 次/分钟 | 滑动 60 秒 |

### 3.3 响应格式

当超过速率限制时，返回 HTTP 429：

```json
{
    "detail": "请求过于频繁，请稍后再试",
    "code": "RATE_LIMIT_ERROR",
    "retry_after": 30
}
```

响应头：
```
Retry-After: 30
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1719500000
```

### 3.4 IP 获取策略

1. 优先从 `X-Forwarded-For` 头获取（反向代理场景）
2. 其次从 `X-Real-IP` 头获取
3. 最后使用 `request.client.host`

## 4. SSRF 防护

### 4.1 概述

防止攻击者利用服务器作为代理访问内网资源。

### 4.2 防护规则

1. **协议检查**：仅允许 HTTPS（开发环境可配置允许 HTTP）
2. **内网 IP 检查**：
   - 127.0.0.0/8 (Loopback)
   - 10.0.0.0/8 (Class A private)
   - 172.16.0.0/12 (Class B private)
   - 192.168.0.0/16 (Class C private)
   - 169.254.0.0/16 (Link-local)
   - ::1, fe80::/10 (IPv6)
3. **DNS Rebinding 防护**：解析域名后检查解析结果是否为内网 IP
4. **localhost 限制**：仅在 DEBUG 模式允许

### 4.3 应用范围

- LLM API Base URL 验证
- 模型测试端点的自定义 URL 验证

## 5. 输入验证

### 5.1 Pydantic Schema 约束

| 字段 | 约束 |
|------|------|
| 查询字符串 | 最大 2000 字符 |
| 列表字段 | 最大 100 个元素 |
| 论文对比 | 最少 2 篇，最多 10 篇 |
| 推荐数量 | 1-50 |
| 反馈评论 | 最大 500 字符 |

### 5.2 UUID 验证

所有资源 ID 使用 UUID v4 格式，由 Pydantic 自动验证。

## 6. 安全响应头

### 6.1 已实现的安全头

| 头部 | 值 | 说明 |
|------|-----|------|
| X-Content-Type-Options | nosniff | 防止 MIME 类型嗅探 |
| X-Frame-Options | DENY | 防止点击劫持 |
| X-XSS-Protection | 1; mode=block | XSS 过滤 |
| Referrer-Policy | strict-origin-when-cross-origin | 控制 Referer 信息 |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | HSTS（仅生产环境） |

### 6.2 信息泄露防护

- 移除 `Server` 响应头
- 移除 `X-Powered-By` 响应头
- API 文档（/docs, /redoc）仅在 DEBUG 模式可用

## 7. 日志安全

### 7.1 脱敏规则

| 数据类型 | 脱敏规则 | 示例 |
|---------|---------|------|
| API Key | 前 4 位 + **** | sk-a1b2**** |
| URL | 保留域名，隐藏查询参数 | https://api.openai.com/v1?... |
| 用户查询 | 保留原样 | - |
| IP 地址 | 保留原样（安全审计） | - |

### 7.2 自动脱敏

日志系统自动检测并脱敏以下模式：
- `sk-` 开头的 API Key
- `sk-ant-` 开头的 Anthropic Key
- `Bearer` Token

## 8. 数据库安全

### 8.1 SQL 注入防护

- 使用 SQLAlchemy ORM，所有查询自动参数化
- 禁止动态拼接 SQL 字符串
- 使用 `select()` 而非原始 SQL

### 8.2 连接安全

- 连接池大小限制（20 + 10 overflow）
- 连接超时 30 秒
- 连接回收 1 小时
- 生产环境使用 SSL 连接

## 9. Docker 安全

### 9.1 容器安全

- 后端容器以 `appuser` 用户运行（非 root）
- 设置 `no-new-privileges` 安全选项
- 临时文件系统挂载 `/tmp`

### 9.2 网络隔离

- 所有服务在同一 Docker 网络中
- 数据库和 Redis 端口仅绑定 127.0.0.1

## 10. 环境变量安全

### 10.1 敏感配置

所有敏感配置通过环境变量注入，不硬编码在代码中：

- `SECRET_KEY`
- `POSTGRES_PASSWORD`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`

### 10.2 安全开关

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DEBUG | false | 生产环境必须为 false |
| ALLOW_PRIVATE_IPS | false | 是否允许访问内网 |
| ALLOW_HTTP | false | 是否允许 HTTP |
