# arXiv Graphify

利用大模型和 arXiv API 自动构建领域论文知识图谱的工具，基于 graphify 实现。

## 核心功能

### 1. 初始化命令 (`init`)

**完整交互流程：**

```bash
export QWEN_API_KEY=sk-...
python -m arxiv_graphify init --keyword "graph neural network"
```

执行后会经历以下交互式步骤：

#### Step 1: 大模型建议 arXiv 关键词
- 调用 Qwen API 将你的领域关键词扩展为 **5-8 个 arXiv 分类关键词**
- 每个关键词附带中文说明，解释其覆盖范围
- 示例输出：
  ```
  Suggested arXiv keywords:
    1. cs.LG - 计算机科学 - 机器学习：涵盖图神经网络（GNN）的基础算法、理论分析与通用机器学习框架
    2. cs.SI - 计算机科学 - 社交与信息网络：聚焦 GNN 在社交网络、引用网络、知识图谱等真实图结构数据上的建模与应用
    3. stat.ML - 统计学 - 机器学习：强调 GNN 的统计建模视角，如泛化界、偏差 - 方差权衡、随机图上的学习理论等
    4. cs.NE - 计算机科学 - 神经与进化计算：关注 GNN 作为新型神经架构的设计、训练动力学、可扩展优化方法及与进化算法的结合
    5. cs.CV - 计算机科学 - 计算机视觉：涵盖将 GNN 用于图像超像素图、点云处理、场景图推理、视觉关系检测等结构化视觉任务
    6. cs.CL - 计算机科学 - 计算语言学：指 GNN 在依存句法树、AMR 图、文档级语义图、知识增强语言模型等 NLP 结构化表示中的应用
  ```

#### Step 2: 用户确认关键词
- 等待用户输入 `y/N` 确认是否接受这些关键词
- 如不满意可重新调整领域关键词后重新运行

#### Step 3: 选择时间范围
- 提供预设选项：
  - 1. 最近 1 年
  - 2. 最近 3 年（默认）
  - 3. 最近 5 年
  - 4. 自定义范围
- 自定义模式可手动输入起止日期

#### Step 4: 批量抓取论文
- 使用 arXiv API v2 按确认的关键词和时间范围搜索
- 自动去重（同一篇文章可能匹配多个关键词）
- 保存论文元数据到 `raw/arxiv/papers/` 目录

#### Step 5: 保存项目元数据
- 生成 `.arxiv_meta.json` 记录：
  - 领域关键词
  - arXiv 关键词列表
  - 时间范围
  - 论文数量
  - 初始化时间

### 2. 增量更新命令 (`update`)

```bash
python -m arxiv_graphify update
```

- 读取 `.arxiv_meta.json` 获取上次更新时间
- 使用项目内已确认的关键词，搜索「上次更新至今」的新文章
- 自动追加新论文到 `raw/arxiv/papers/`
- 更新元数据中的时间戳和论文计数

### 3. 构建知识图谱命令 (`build`)

```bash
python -m arxiv_graphify build
```

- 调用 `graphify update` 处理 `raw/arxiv/` 目录下的所有论文
- 生成知识图谱到 `graphify-out/` 目录
- 输出 `GRAPH_REPORT.md` 包含：
  - 神节点（god nodes）分析
  - 社区结构（communities）
  - 意外连接（surprising connections）

### 4. 状态查询命令 (`status`)

```bash
python -m arxiv_graphify status
```

显示项目当前状态：
- 领域关键词
- arXiv 关键词列表
- 论文总数
- 时间范围
- 初始化时间
- 上次更新时间

---

## 安装

```bash
pip install -e .
```

---

## 快速开始

### 1. 配置 API Key

**方式一：环境变量（推荐）**
```bash
export QWEN_API_KEY=sk-...
```

**方式二：配置文件**
```json
// ~/.arxiv_graphify_config.json
{
  "qwen_api_key": "sk-..."
}
```
```bash
python -m arxiv_graphify init --keyword "..." --config ~/.arxiv_graphify_config.json
```

### 2. 初始化领域图谱

```bash
python -m arxiv_graphify init --keyword "graph neural network"
```

按提示完成：
1. 确认大模型建议的 arXiv 关键词
2. 选择时间范围
3. 等待论文抓取完成

### 3. 构建知识图谱

```bash
python -m arxiv_graphify build
```

### 4. 查看报告

```bash
cat graphify-out/GRAPH_REPORT.md
```

### 5. 定期更新

```bash
python -m arxiv_graphify update
python -m arxiv_graphify build
```

---

## 命令参考

| 命令 | 说明 | 必选参数 |
|------|------|----------|
| `init` | 初始化新项目 | `--keyword` |
| `update` | 增量更新论文 | 无 |
| `build` | 构建知识图谱 | 无 |
| `status` | 显示项目状态 | 无 |

### 全局选项

| 选项 | 说明 |
|------|------|
| `-c, --config PATH` | 指定配置文件路径 |
| `-o, --output-dir PATH` | 指定输出目录（默认当前目录） |
| `-m, --max-papers INTEGER` | 每个关键词最大抓取数（init 默认 500，update 默认 200） |

---

## 项目结构

```
project/
├── raw/arxiv/papers/       # 论文元数据 JSON 文件
│   ├── 2012.12104.json
│   ├── 2101.00001.json
│   └── ...
├── graphify-out/           # graphify 生成的知识图谱
│   ├── graph.json          # 图谱数据
│   ├── GRAPH_REPORT.md     # 分析报告
│   └── wiki/               # 可选的 Wiki 导航
├── .arxiv_meta.json        # 项目元数据
├── .arxiv_graphify_config.json  # 可选的配置文件
└── docs/plans/             # 设计和实施文档
```

---

## 测试

```bash
# 运行所有测试
PYTHONPATH=src pytest tests/ -v

# 运行特定测试文件
PYTHONPATH=src pytest tests/test_config.py -v
PYTHONPATH=src pytest tests/test_qwen_client.py -v
```

---

## API 说明

### Qwen API
- **用途**：关键词扩展、论文摘要生成
- **Endpoint**：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- **模型**：`qwen-plus`
- **获取 Key**：[阿里云百炼控制台](https://dashscope.console.aliyun.com/)

### arXiv API v2
- **用途**：论文搜索和元数据获取
- **Endpoint**：`https://export.arxiv.org/api/query`
- **认证**：无需 Key（公开 API，有限流）
- **文档**：[arXiv API Documentation](https://arxiv.org/help/api)

---

## 亮点功能

1. **大模型智能关键词扩展** - 无需手动研究 arXiv 分类体系，输入自然语言领域描述即可获取精准的关键词组合

2. **交互式确认流程** - 每一步都可确认/修改，确保抓取方向符合用户预期

3. **增量更新机制** - 自动记录上次更新时间，只抓取新论文，节省 API 调用和时间

4. **纯新增模式集成 graphify** - 新论文直接追加，graphify 自动处理关联和聚类

5. **结构化元数据管理** - `.arxiv_meta.json` 完整记录项目配置，支持长期维护

6. **完整的测试覆盖** - 所有核心模块都有单元测试，支持 CI/CD

---

## 后续计划

- [ ] 子领域扩展功能 - 在确认主关键词后询问是否添加相关子领域
- [ ] 文章样例确认 - 对每个关键词搜索 3-5 篇文章生成中文概要供用户确认
- [ ] 定时自动更新 - 支持 cron 配置定期自动执行 update
- [ ] 多图合并 - 支持多个子领域图谱的合并分析
