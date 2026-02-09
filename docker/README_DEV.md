# Docker 开发环境说明

## 配置说明

这个 Docker 开发环境支持本地开发和容器化测试，代码和依赖管理的关键点：

### 1. **代码管理**
- 项目根目录 `../` 挂载到容器的 `/app`
- 实现代码热重载，本地修改立即生效
- 无需重启容器即可看到代码变更

### 2. **依赖管理**
为了避免本地和容器依赖冲突，采用以下策略：

#### Backend (Python/uv)
- `.venv` 目录通过匿名卷排除，不会被本地挂载覆盖
- 容器启动时自动执行 `uv sync` 安装依赖
- 依赖安装在容器内的独立虚拟环境

#### Frontend (Node.js/pnpm)
- `node_modules` 目录通过匿名卷排除
- 容器启动时自动执行 `pnpm install` 安装依赖
- pnpm store 可选挂载以加速依赖安装

### 3. **启动流程**

```bash
# 初次启动或重新构建
cd docker
docker compose -p deer-flow-dev -f docker-compose-dev.yaml up --build -d

# 日常启动
docker compose -p deer-flow-dev -f docker-compose-dev.yaml up -d

# 查看日志
docker compose -p deer-flow-dev -f docker-compose-dev.yaml logs -f

# 停止服务
docker compose -p deer-flow-dev -f docker-compose-dev.yaml down
```

### 4. **访问地址**
- Frontend: http://localhost:2026
- Gateway API: http://localhost:2026/api/...
- LangGraph API: http://localhost:2026/api/langgraph/...
- API Docs: http://localhost:2026/docs

### 5. **开发工作流**

#### 本地开发
1. 在本地修改代码
2. 容器自动检测变更并热重载
3. 浏览器刷新即可看到效果

#### 添加新依赖

**Backend:**
```bash
# 在本地添加依赖
cd backend
uv add <package>

# 重启容器以安装新依赖
docker compose -p deer-flow-dev -f docker-compose-dev.yaml restart api langgraph
```

**Frontend:**
```bash
# 在本地添加依赖
cd frontend
pnpm add <package>

# 重启容器以安装新依赖
docker compose -p deer-flow-dev -f docker-compose-dev.yaml restart web
```

### 6. **故障排查**

**502 Bad Gateway:**
- 检查服务是否启动完成：`docker compose ps`
- 查看服务日志：`docker logs deer-flow-web/api/langgraph`
- 确认端口没有被占用：`lsof -i :2026`

**依赖安装失败:**
- 清理卷并重建：`docker compose down -v && docker compose up --build -d`
- 检查 lockfile 是否存在：`uv.lock` 或 `pnpm-lock.yaml`

**代码修改不生效:**
- 确认 volumes 挂载正确
- 重启相关服务
- 检查文件权限

### 7. **技术细节**

#### Volume 排除机制
```yaml
volumes:
  - ../:/app                    # 挂载整个项目
  - /app/backend/.venv          # 排除 Python 虚拟环境
  - /app/frontend/node_modules  # 排除 Node.js 依赖
```

这种配置确保：
- 本地代码修改实时同步到容器
- 容器内的依赖不会与本地依赖冲突
- 每个环境的依赖独立管理

#### 环境变量
- `CI=true`: 防止交互式提示，适用于容器环境
- `NODE_ENV=development`: Next.js 开发模式
- `WATCHPACK_POLLING=true`: 文件监控轮询（Docker 文件系统兼容性）

## 与本地开发对比

| 特性 | Docker 开发 | 纯本地开发 |
|------|-----------|----------|
| 依赖隔离 | ✅ 完全隔离 | ❌ 可能冲突 |
| 环境一致性 | ✅ 100%一致 | ⚠️ 取决于本地环境 |
| 启动速度 | ⚠️ 初次较慢 | ✅ 快速 |
| 资源占用 | ⚠️ 较高 | ✅ 较低 |
| 代码热重载 | ✅ 支持 | ✅ 支持 |
| 调试体验 | ⚠️ 需额外配置 | ✅ 原生支持 |

## 推荐工作流

1. **日常开发**: 使用本地开发环境（速度快，调试方便）
2. **集成测试**: 使用 Docker 环境（确保环境一致性）
3. **部署前验证**: 使用 Docker 环境（与生产环境更接近）
