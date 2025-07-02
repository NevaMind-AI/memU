# PersonaLab PostgreSQL 配置指南

## 问题解决 ✅

之前PersonaLab会创建SQLite数据库文件（如`memory.db`、`conversations.db`等），现在已配置为使用PostgreSQL数据库。

## 原因分析

PersonaLab的数据库选择逻辑位于 `personalab/config/database.py` 中：

```python
@classmethod
def from_env(cls) -> "DatabaseConfig":
    # 检查PostgreSQL环境变量
    postgres_host = os.getenv('POSTGRES_HOST')
    postgres_db = os.getenv('POSTGRES_DB')
    
    # 如果设置了PostgreSQL环境变量，使用PostgreSQL
    if postgres_host and postgres_db:
        return cls(backend="postgresql", ...)
    
    # 否则默认使用SQLite
    return cls(backend="sqlite", ...)
```

**关键**: 只有当同时设置了 `POSTGRES_HOST` 和 `POSTGRES_DB` 环境变量时，系统才会使用PostgreSQL。

## 当前配置 ✅

### 环境变量设置
```bash
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=personalab
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""
```

### 验证状态
- ✅ 数据库后端: PostgreSQL
- ✅ 数据库连接: 成功
- ✅ SQLite文件: 已清理完毕

## 快速使用

### 方法1: 每次手动设置环境变量
```bash
# 设置环境变量
source setup_postgres_env.sh

# 使用PersonaLab
python your_script.py
```

### 方法2: 永久配置（推荐）
将环境变量添加到 `~/.zshrc` 文件中：

```bash
# 在 ~/.zshrc 文件末尾添加
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=personalab
export POSTGRES_USER=chenhong
export POSTGRES_PASSWORD=""

# 重新加载配置
source ~/.zshrc
```

## 配置工具

### 自动配置脚本
```bash
# 运行完整配置和测试
python configure_postgresql.py
```

### 验证配置
```bash
# 验证当前配置状态
python test_postgres_config.py
```

### 环境设置脚本
```bash
# 快速设置环境变量（需要每次运行）
source setup_postgres_env.sh
```

## PostgreSQL服务管理

### 启动PostgreSQL服务
```bash
brew services start postgresql@14
```

### 停止PostgreSQL服务
```bash
brew services stop postgresql@14
```

### 检查服务状态
```bash
brew services list | grep postgres
```

## 数据库管理

### 连接数据库
```bash
psql -d personalab
```

### 查看表结构
```sql
-- 记忆相关表
\dt memory*

-- 对话相关表  
\dt conversation*
```

### 备份数据库
```bash
pg_dump personalab > personalab_backup.sql
```

## 故障排除

### 1. PostgreSQL服务未运行
```bash
# 启动服务
brew services start postgresql@14

# 验证状态
brew services list | grep postgres
```

### 2. 连接权限问题
```bash
# 确保用户有权限访问数据库
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE personalab TO chenhong;"
```

### 3. 环境变量未设置
```bash
# 检查环境变量
env | grep POSTGRES

# 重新设置
source setup_postgres_env.sh
```

### 4. 仍在创建SQLite文件
- 确认环境变量已正确设置：`echo $POSTGRES_HOST`
- 重新启动Python进程
- 运行验证脚本：`python test_postgres_config.py`

## 优势

使用PostgreSQL相比SQLite的优势：

1. **性能**: 更好的并发性能和查询优化
2. **扩展性**: 支持更大的数据量和用户数
3. **功能**: 支持向量搜索（pgvector扩展）
4. **生产环境**: 更适合部署到生产环境
5. **备份恢复**: 更完善的备份和恢复机制

## 总结

现在PersonaLab已正确配置为使用PostgreSQL数据库，不再创建SQLite文件。确保在使用前设置正确的环境变量即可。 