# 中美 AI 垂直应用深度调研 — 执行计划

## 任务概述
调研未来 3-10 年中美两国 AI 应用渗透的重点垂直方向，打分排序；拆解各方向产业链（上/中/下游）与受益公司；对重点公司做财务、产品线、研发、股价市值分析；产出投资研究报告（.docx）。

## Stage 1 — 深度调研（deep-research-swarm 技能）
并行研究子代理（Route A 宽搜 → 深潜两阶段）：
- Agent 1: 美国 AI 垂直应用方向全景（软件/SaaS、AI 编程 Agent、制药/创新药、基因编辑、机器人、自动驾驶、金融科技、国防、教育、法律、医疗诊断、能源/数据中心等）
- Agent 2: 中国 AI 垂直应用方向全景（对应维度 + 中国特色方向：智能制造、电商、短视频/内容、智驾、AI 硬件生态等）
- Agent 3: 各方向产业链拆解与资金流向（上中下游、资本注入环节）
- Agent 4: 重点公司清单与近况（OpenAI、Anthropic、Salesforce、Datadog、Databricks、Snowflake、ServiceNow、IBM、Recursion RXRX 等 + 中国对标公司）
- 交叉验证，产出研究简报

## Stage 2 — 金融数据采集（插件）
- 美国上市公司：SEC EDGAR（财报/XBRL）+ Yahoo Finance（股价、指标、近1.5年周K数据）
- 中国上市公司（A股/港股）：iFinD
- 非上市公司（OpenAI/Anthropic/Databricks）：用研究数据 + 公开估值信息
- 用 matplotlib 绘制近 1.5 年周K线图

## Stage 3 — 打分与排序
- 0-100 发展可能性打分（市场规模、技术成熟度、政策支持、资本热度、落地速度等维度）
- 先美国后中国，按分数从高到低排序

## Stage 4 — 报告撰写（report-writing 技能）
- 结构化长报告 Markdown：方向打分排序 → 产业链拆解 → 公司逐一分析（含K线图、指标表格、财报表格）→ 投资观点
- 注意：用户无美国绿卡，不做美国税务居民假设；含风险提示，非个性化投资建议

## Stage 5 — 交付（docx 技能）
- Markdown → .docx，图表嵌入
- 交付 /mnt/agents/output/ 下的最终文件
