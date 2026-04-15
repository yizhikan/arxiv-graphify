# arXiv 论文知识图谱系统设计文档

**日期**: 2026-04-15  
**状态**: 已批准

---

## 一、系统概述

构建一个利用 graphify 构建 arXiv 领域论文知识图谱的系统，包含初始化和增量更新两部分功能。

---

## 二、核心功能

### 2.1 初始化命令 (`init`)

用户给出领域关键词，系统执行以下流程：

1. **关键词扩展** - 调用 Qwen API 返回该关键词在 arXiv 上对应的关键词组合列表
2. **用户确认** - 用户确认/修改关键词列表
3. **子领域扩展** - 询问是否添加相关子领域，逐步扩展
4. **文章样例确认** - 对每个关键词搜索 3-5 篇文章，生成中文概要，用户基于样例判断关键词准确性
5. **时间范围选择** - 混合模式：先提供预设选项（1 年/3 年/5 年），不满意可自定义
6. **批量抓取** - 使用 arXiv API v2 按时间范围抓取论文
7. **构建图谱** - 调用 graphify 处理收集的论文

### 2.2 增量更新命令 (`update`)

1. 读取项目元数据文件获取上次更新时间
2. 使用已确认的关键词，搜索「上次更新至今」的新文章
3. 下载新论文元数据到 `raw/arxiv/`
4. 运行 `graphify update`（纯新增模式）
5. 更新元数据文件中的时间戳

### 2.3 可选定时更新

提供 cron 配置示例，用户可选配置自动更新。

---

## 三、技术选型

| 组件 | 选型 | 备注 |
|------|------|------|
| arXiv 搜索 | arXiv API v2 | `https://export.arxiv.org/api/query` |
| 大模型 API | Qwen API | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| 知识图谱 | graphify | 现有 graphify 系统 |
| 编程语言 | Python 3.10+ | 与 graphify 保持一致 |

---

## 四、数据存储结构

```
project/
├── raw/
│   └── arxiv/
│       ├── papers/           # 论文元数据 (JSON/Markdown)
│       └── .gitkeep
├── graphify-out/             # graphify 输出
├── .arxiv_meta.json          # 项目元数据
├── arxiv_graphify.py         # 主命令行工具
└── docs/
    └── plans/
```

### .arxiv_meta.json 格式

```json
{
  "domain_keyword": "graph neural network",
  "arxiv_keywords": ["cs.LG", "cs.SI", "stat.ML"],
  "initialized_at": "2026-04-15T00:00:00Z",
  "last_updated": "2026-04-15T00:00:00Z",
  "time_range": {
    "start": "2021-01-01",
    "end": "2026-04-15"
  },
  "paper_count": 1234
}
```

---

## 五、API 使用

### Qwen API

- Endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- 模型：`qwen-plus`
- 用途：
  - 关键词扩展
  - 中文概要生成

### arXiv API v2

- Endpoint: `https://export.arxiv.org/api/query`
- 查询示例：
  ```
  https://export.arxiv.org/api/query?search_query=cat:cs.AI+AND+all:graph&start=0&max_results=100
  ```

---

## 六、命令接口设计

```bash
# 初始化
python arxiv_graphify.py init --keyword "<领域关键词>"

# 增量更新
python arxiv_graphify.py update

# 查看状态
python arxiv_graphify.py status

# 定时更新 (可选)
python arxiv_graphify.py schedule --interval weekly
```

---

## 七、错误处理

- arXiv API 限流：指数退避重试
- Qwen API 失败：降级为英文摘要，提示用户
- graphify 失败：保留中间数据，便于排查

---

## 八、测试要求

- 单元测试：关键词扩展、摘要生成、arXiv 搜索
- 集成测试：完整 init 流程、update 流程
- 用户验收测试：实际领域初始化、图谱质量验证
