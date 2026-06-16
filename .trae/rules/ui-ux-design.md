# UI/UX 设计规范

> **强制规则**：所有涉及 UI 结构、视觉设计、交互模式或用户体验的任务，**必须优先调用 `ui-ux-pro-max` 技能**，使用其设计系统搜索和 UX 准则数据库进行决策。

## 触发场景（必须调用）

- 新建/重构页面（Landing Page、Dashboard、列表页、详情页等）
- 创建或修改 UI 组件（按钮、卡片、表单、图表、导航等）
- 选择配色方案、字体搭配、间距标准、布局系统
- 审查 UI 代码的可访问性、视觉一致性或用户体验
- 实现导航结构、动画效果、响应式布局
- 产品级设计决策（风格选择、信息层级、品牌表达）
- 改善界面的感知质量、清晰度或易用性

## 使用方式

```bash
# 生成完整设计系统（首选）
python .trae/skills/ui-ux-pro-max/scripts/search.py "<产品类型> <关键词>" --design-system -p "WorldCup"

# 按领域搜索细节
python .trae/skills/ui-ux-pro-max/scripts/search.py "<关键词>" --domain <domain>

# 搜索 Flutter 栈最佳实践
python .trae/skills/ui-ux-pro-max/scripts/search.py "<关键词>" --stack flutter
```

## 可用领域

| 域 | 用途 |
|---|------|
| `style` | UI 风格（glassmorphism、minimalism 等 67+ 种） |
| `color` | 配色方案（161 套，按产品类型分类） |
| `typography` | 字体搭配（57 组 Google Fonts） |
| `ux` | UX 准则（99 条：无障碍、动画、导航等） |
| `chart` | 图表类型（25 种） |
| `product` | 产品类型推荐（161 种） |
