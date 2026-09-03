# Research Planning Architect 中文说明

`research-planning-architect` 是一个 Codex skill，用于把 ML/AI 或科学研究中的初步想法，转化为有证据支撑、可执行、可被审稿人检验的研究计划。它重点覆盖 novelty 诊断、跨领域创新启发、baseline/SOTA 基准整理、贡献定位、方法设计、分层实验矩阵、算力规划和 reviewer red-team。

## 适用场景

当任务需要真正的研究设计决策时，适合使用这个 skill，例如：

- 把粗糙 idea 转化为可投稿的研究论点。
- 审计已有研究计划的 novelty、可行性、baseline、实验设计或 reviewer 风险。
- 整理当前 baseline/SOTA 表，包含重要指标、报告分数和可比设置。
- 规划数据集、baseline、指标、消融实验和算力预算。
- 将研究想法与近三年顶会顶刊论文、SOTA 或目标 venue 规范进行对比。
- 根据反馈升级研究计划，例如“不够新”“太泛”“实验不够”“baseline/SOTA 弱”。

不适合用于单篇论文解读、普通文献列表生成、常规论文润色，或与实验计划无关的纯 coding 任务。

## 核心输出

完整研究计划应包含以下 10 个部分：

1. 研究论点
2. 近年论文证据表
3. Baseline/SOTA 基准表
4. Novelty 判断
5. 顶会贡献定位
6. 方法蓝图
7. 数据集、模型与算力规划
8. 分层实验矩阵
9. Reviewer red-team
10. 迭代计划
11. 风险登记表

文献检索会区分两类证据：近三年同领域顶会顶刊用于覆盖研究论点、直接对比和 novelty 威胁；Nature、Science、重要子刊、权威论坛和技术报告等跨领域来源用于构建可迁移机制、测量协议或更强评测设计，不能替代同领域直接证据。

## 分层实验矩阵

实验部分被明确拆成三层，目的是让计划更贴合真实数据、代码成熟度、算力、deadline、license 和 privacy 限制。

- 最小可行性验证实验：用最小成本验证或证伪核心机制，决定 idea 是否值得继续投入。
- 快速优化完善框架实验：通过低成本变体、诊断实验、stress slice 和有限 sweep，快速改进方法框架。
- 完整对比实验：面向论文级结论，与可信 baseline 做完整比较，并包含消融、鲁棒性、效率、定性分析和统计报告。

每一层实验都应说明：被验证的 claim、具体实验、数据/模型范围、baseline 或控制组、指标、预算和决策门槛。

## 目录结构

```text
research-planning-architect/
├── SKILL.md
├── AGENTS.md
├── README.md
├── README_ZH.md
├── agents/
│   └── openai.yaml
├── assets/
│   └── templates/
│       └── research-plan-template.md
├── examples/
│   └── smoke-research-plan.md
├── references/
│   ├── experiment-design.md
│   ├── novelty-and-positioning.md
│   ├── reviewer-red-team.md
│   ├── search-and-evidence.md
│   └── validation-and-iteration.md
└── scripts/
    ├── audit_research_plan.py
    ├── research_plan_scaffold.py
    └── validate_skill.py
```

## 参考文件

- `references/search-and-evidence.md`：文献检索协议、证据表结构、baseline/SOTA 表结构、跨领域创新启发来源、来源优先级和 claim 标签。
- `references/novelty-and-positioning.md`：novelty 评分维度和贡献定位方式。
- `references/experiment-design.md`：数据集、baseline、指标、消融、分层实验矩阵、算力和可复现性规则。
- `references/reviewer-red-team.md`：常见 reviewer 攻击点和缓解策略。
- `references/validation-and-iteration.md`：计划审计清单、反馈归因和修订规则。

## 脚本用法

生成研究计划 scaffold：

```bash
python3 scripts/research_plan_scaffold.py "你的研究想法" \
  --target-venue ICLR \
  --compute "2xA100, 2 weeks" \
  --language zh
```

审计已有或草稿研究计划：

```bash
python3 scripts/audit_research_plan.py examples/smoke-research-plan.md
```

校验 skill 目录结构：

```bash
python3 scripts/validate_skill.py .
```

## 维护检查

修改该 skill 后，建议运行：

```bash
python3 scripts/validate_skill.py .
python3 scripts/audit_research_plan.py examples/smoke-research-plan.md
python3 -m py_compile scripts/audit_research_plan.py scripts/research_plan_scaffold.py scripts/validate_skill.py
```

维护时保持 `SKILL.md` 简洁、流程化。详细可复用规则放在 `references/`，输出模板放在 `assets/templates/`，稳定的生成或检查逻辑放在 `scripts/`。
