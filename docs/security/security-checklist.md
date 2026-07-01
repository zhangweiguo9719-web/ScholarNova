# MVP 上线前安全检查清单

## 1. 环境变量与密钥管理

- [ ] `.env` 文件已添加到 `.gitignore`
- [ ] `SECRET_KEY` 已替换为随机生成的强密钥
- [ ] 数据库密码使用强密码（至少 16 字符）
- [ ] LLM API Key 未硬编码在代码中
- [ ] 生产环境 `DEBUG=false`
- [ ] 生产环境 `APP_ENV=production`

## 2. 网络安全

- [ ] 数据库端口（5432）仅绑定 127.0.0.1
- [ ] Redis 端口（6379）仅绑定 127.0.0.1
- [ ] 生产环境使用 HTTPS
- [ ] CORS 配置仅允许信任的域名
- [ ] SSRF 防护已启用（`ALLOW_PRIVATE_IPS=false`）
- [ ] HTTP 协议已禁用（`ALLOW_HTTP=false`，生产环境）

## 3. API 安全

- [ ] 速率限制已配置（搜索 30/min，分析 10/min）
- [ ] 所有输入使用 Pydantic 严格校验
- [ ] 查询字符串最大长度限制（2000 字符）
- [ ] 列表字段最大元素数限制（100）
- [ ] 请求体大小限制（10MB）
- [ ] 安全响应头已添加
  - X-Content-Type-Options: nosniff
  - X-Frame-Options: DENY
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security (HTTPS)

## 4. LLM 网关安全

- [ ] API Key 仅保存在进程内存中
- [ ] 日志中无明文 API Key
- [ ] 错误信息中无明文 API Key
- [ ] Base URL 验证已启用
- [ ] 请求超时已设置（30 秒）
- [ ] 响应体大小限制已设置（10MB）

## 5. 数据库安全

- [ ] 所有查询使用 SQLAlchemy ORM（参数化查询）
- [ ] 无动态 SQL 拼接
- [ ] 连接池大小已限制
- [ ] 生产环境使用 SSL 连接
- [ ] 数据库密码未在日志中输出

## 6. 日志安全

- [ ] 日志中敏感信息已脱敏
- [ ] API Key 脱敏（仅显示前 4 位）
- [ ] URL 中的敏感参数已脱敏
- [ ] IP 地址保留（用于安全审计）
- [ ] 日志级别生产环境设为 WARNING 或以上

## 7. Docker 安全

- [ ] 后端容器以非 root 用户运行
- [ ] 容器设置了 `no-new-privileges` 安全选项
- [ ] 只暴露必要端口
- [ ] 环境变量中无硬编码敏感值
- [ ] 数据卷权限正确

## 8. 依赖安全

- [ ] 依赖版本已锁定（requirements-lock.txt）
- [ ] 无已知高危漏洞的依赖
- [ ] 定期更新依赖
- [ ] 开发依赖未包含在生产镜像中

## 9. 错误处理

- [ ] 生产环境不暴露内部错误详情
- [ ] 异常信息中不包含敏感数据
- [ ] 统一的错误响应格式
- [ ] 适当的 HTTP 状态码

## 10. 访问控制

- [ ] API 文档（/docs, /redoc）仅在 DEBUG 模式可用
- [ ] 用户身份验证机制就位（如需要）
- [ ] 敏感操作需要授权
