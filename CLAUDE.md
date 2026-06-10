# WorldCup 2026 Predictor - AI Agent Configuration

## Role
您是 WorldCup 2026 预测项目的 AI 助手，负责帮助开发者进行项目开发、数据分析和功能实现。

## Goals
1. 协助开发世界杯预测模型和算法
2. 支持后端 API 开发和调试
3. 帮助实现前端界面和交互
4. 提供数据抓取和处理支持
5. 辅助进行比赛模拟和预测分析

## Project Structure
```
WorldCup/
├── backend/                    # Python FastAPI 后端
│   ├── app/
│   │   ├── api/               # REST API 端点
│   │   ├── core/              # 核心算法（Elo、Poisson、预测）
│   │   ├── models/            # 数据库模型
│   │   ├── schemas/           # Pydantic 数据结构
│   │   ├── services/          # 业务服务（爬虫、数据抓取）
│   │   └── tasks/             # 定时任务
│   ├── seed_data/             # 初始数据
│   └── tests/                 # 测试用例
├── flutter_app/               # Flutter 移动端应用
│   └── lib/
│       ├── pages/             # 页面组件
│       ├── providers/         # 状态管理
│       ├── services/          # API 服务
│       └── widgets/           # 通用组件
├── data/                      # 数据文件
└── docs/                      # 文档
```

## Key Features
- ⚽ **比赛预测**: 使用 Elo 评分和 Poisson 模型进行比赛结果预测
- 📊 **数据分析**: 球员数据统计、球队排名分析
- 🔄 **实时数据**: 自动抓取懂球帝等数据源
- 🎯 **模拟功能**: 完整世界杯赛程模拟
- 💡 **推荐系统**: 基于数据的投注建议

## Available Skills

### Development Skills
- `code-review`: 代码审查和质量检查
- `systematic-debugging`: 系统性调试
- `test-driven-development`: 测试驱动开发
- `finishing-a-development-branch`: 完成开发分支

### Browser Skills
- `browser_navigate`: 导航网页
- `browser_click`: 点击元素
- `browser_fill`: 填写表单
- `browser_evaluate`: 执行 JavaScript

### Database Skills
- `create_entities`: 创建实体
- `read_graph`: 读取图数据
- `search_nodes`: 搜索节点

## Workflow

### 开发流程
1. **需求分析**: 理解需求并制定实现计划
2. **设计阶段**: 编写技术文档和架构设计
3. **实现阶段**: 编写代码并进行单元测试
4. **审查阶段**: 代码审查和质量保证
5. **验证阶段**: 运行测试并验证功能

### 数据流程
1. **数据抓取**: 从懂球帝等源获取数据
2. **数据处理**: 清洗和转换数据
3. **模型训练**: 更新 Elo 评分和预测模型
4. **预测生成**: 生成比赛预测结果
5. **结果展示**: 通过 API 和前端展示

## Tool Usage Guidelines

### 代码操作
- 使用 `Edit` 工具修改现有文件
- 使用 `Write` 工具创建新文件
- 使用 `Read` 工具读取文件内容
- 使用 `Grep` 工具搜索代码

### 命令执行
- 使用 `RunCommand` 运行 Python 脚本和测试
- 使用 `cd` 切换目录
- 使用 `pip` 安装依赖
- 使用 `python -m pytest` 运行测试

### 浏览器操作
- 使用浏览器工具进行网页抓取
- 优先使用 Obscura 作为浏览器后端
- 抓取完成后及时关闭页面

## Best Practices

1. **代码规范**: 遵循 PEP8 规范，使用类型注解
2. **测试覆盖**: 关键功能应有单元测试
3. **文档更新**: 代码变更时同步更新文档
4. **错误处理**: 完善的异常处理和日志记录
5. **代码复用**: 抽取公共逻辑到工具函数

## Safety Guidelines
- 不要泄露敏感信息（API keys、密码等）
- 不要执行危险命令（rm -rf、格式化等）
- 定期备份重要数据
- 测试环境和生产环境分离

## Contact
如有问题或建议，请联系项目开发者。