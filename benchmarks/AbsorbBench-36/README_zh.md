# AbsorbBench-36

AbsorbBench-36 用于测试智能体的微波吸波结构逆向设计能力，包含18项涂覆蜂窝夹层任务和18项TPMS任务。任务划分为开发集8项、验证集4项、测试集24项。

本公开包提供任务定义、初始设计参数、材料与建模说明，以及输入校验和评分工具。**不包含本研究的方法测试结果、优化设计、优化轨迹或Initial历史得分。** 全部任务统一采用AB36编号，任务条件与冻结版本一致。

## 如何使用

1. 使用开发集搭建和调试自己的智能体，在验证集选择配置。
2. 冻结智能体后运行24项测试任务。每项任务最多提出5个新设计，所有方法从同一Initial开始。
3. 用自己的全波求解器计算Initial和各次提案，保留原始复反射系数和求解日志。
4. 使用评分工具计算覆盖率、是否达标，以及各任务首次成功轮次。未解决的求解故障单独报告。

```bash
cd benchmarks/AbsorbBench-36
python tools/absorbbench.py validate
python tools/absorbbench.py show AB36-TPMS-D01
python tools/absorbbench.py template AB36-TPMS-D01 --out evaluation.json
python tools/geometry.py AB36-TPMS-D01 --out geometry.json
```

工具需要Python 3.10及以上，不调用模型或求解器。`evaluation.json`为待填写模板，其验证标记默认为false；必须完成真实计算和检查后才能评分。

任务与初始参数见[任务目录](tasks/)和[任务总表](tasks.csv)。详细规则见[评价协议](docs/protocol.md)、[建模说明](docs/modeling.md)及[接入说明](docs/integration.md)。英文文档给出了完整字段和命令。

该公开包不含商业求解器和AbsorbEvo私有智能体实现。使用者需要自行提供求解器及适配程序。基准目录按[MIT协议](LICENSE)开放使用；建议引用基准名称、版本和仓库提交号，以便复现。
