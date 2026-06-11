# 世界杯预测 App — 数据目录

## 数据源

| 文件 | 来源 | 内容 |
|------|------|------|
| `teams_2026.json` | Zafronix WC API | 48 支球队详情（含 26 人大名单、教练、分组） |
| `tournament_2026.json` | Zafronix WC API | 2026 赛事信息（场馆、日期、赛制） |
| `tournaments_all.json` | Zafronix WC API | 1930-2026 共 23 届赛事列表 |

## 数据用途

- **teams_2026.json** → P0 种子数据，导入数据库
- **tournament_2026.json** → 赛程、场馆信息
- **tournaments_all.json** → Elo 模型历史校准

## API Key

- Zafronix: `zwc_free_3776717359a0cecfe09e0b8e`
- 复制 `.env.example` 为 `.env` 并填入 Key
