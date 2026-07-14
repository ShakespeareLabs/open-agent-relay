# OpenAgentRelay

[English](README.md) | [简体中文](README.zh-CN.md)

> **让任何本地 Agent 或自动化，成为整个团队都能直接使用的能力。**

## 这个项目是做什么的？

假设你写了一个脚本，可以查询广告数据、整理用户访谈，或者生成周报。

它在你的电脑上已经能正常工作。但是同事想用时，你通常需要把下面这些东西发给他：

- 代码
- 安装说明
- 依赖
- Prompt 和规则
- API Token 或账号配置

然后每位同事都要在自己的电脑上重新安装和维护一份。

OpenAgentRelay 换了一种方式：

1. 已经能运行的 Agent 或脚本继续留在你的电脑或服务器上。
2. 你在团队 Hub 中给它登记一个名字，例如 `ads-report`。
3. 同事把需求提交给这个名字。
4. 你的 Agent 执行任务，再把结果返回给同事。

同事可以直接使用结果，不需要安装你的项目，也不需要拿到你的凭证副本。

## 一个简单例子

你本地有一个叫 `ads_report.py` 的脚本。

通过下面的命令把它接入团队任务中心：

```bash
relay expose \
  --name ads-report \
  --description "查询广告数据并生成报告" \
  -- python ads_report.py
```

同事可以提交：

```bash
relay ask \
  --agent ads-report \
  --wait \
  "找出本周 CPA 上涨最多的广告系列"
```

OpenAgentRelay 会把需求交给你正在运行的脚本，然后把脚本的结果返回给同事。

脚本仍然在你控制的环境中运行，它的代码和凭证不需要交给调用者。

## 只能接入 AI Agent 吗？

不是。下面这些都可以接入：

- AI Agent
- Python 或 Shell 脚本
- 内部自动化
- 数据查询工具
- 报告生成器
- 未来通过适配器接入的 HTTP 或 A2A Agent

OpenAgentRelay 把这些统一称为**能力**：能够接收任务并返回结果的东西。

## 它和共享 Skill 有什么不同？

Skill 是在教另一个 Agent **如何完成一件事**。使用者需要安装 Skill，并自己准备它需要的工具、环境和凭证。

OpenAgentRelay 是让其他人**直接使用一个已经能够运行的东西**。

| 共享 Skill | 使用 OpenAgentRelay |
|---|---|
| 每个人安装一份 | 作者维护一个可运行版本 |
| 每个人配置依赖 | 作者维护运行环境 |
| 每个人配置凭证 | 凭证可以留在 Runner 所在环境 |
| 更新后需要重新安装 | 作者更新一次即可 |
| 任务分散在每台电脑执行 | 请求和结果统一经过任务 Hub |

两者可以一起使用。一个 Agent 内部仍然可以使用许多 Skill，Relay 负责让这个 Agent 被团队调用。

## 它是怎么工作的？

```text
同事提交需求
      ↓
Hub 保存任务
      ↓
你的 Runner 领取任务
      ↓
本地 Agent 或脚本执行
      ↓
结果返回给同事
```

Runner 会主动向 Hub 建立连接，因此不需要在你的电脑上开放公网端口。

## 五分钟体验

需要 Python 3.11 或更高版本。当前版本运行时不依赖第三方包。

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

启动 Hub：

```bash
relay hub
```

在另一个终端中接入一个最简单的自动化：

```bash
relay expose \
  --name uppercase \
  --description "将文本转换为大写" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
```

提交任务：

```bash
relay ask --agent uppercase --wait "hello team"
```

你应该会收到 `HELLO TEAM`。

也可以打开 [http://127.0.0.1:8787](http://127.0.0.1:8787)，通过简单网页提交任务。

## 0.1 版本能做什么？

- 按名称登记一个 Agent 或自动化
- 通过命令行或网页提交任务
- 让本地 Runner 自动领取任务
- 通过标准输入把文字需求传给任意命令
- 把命令的输出作为任务结果返回
- 展示清晰的任务状态和错误

## 重要说明：0.1 版本只是本地演示

0.1 版本已经证明基本流程可以工作，但它**还不能安全地连接生产凭证或直接暴露在公网**。

目前还没有：

- 用户登录
- 数据和资源级权限
- 持久化任务存储
- 隔离执行环境
- 写操作审批
- 凭证泄漏检测
- 签名任务授权

现阶段请只在本机运行 Hub。连接真实 Agent 或凭证前，请先阅读 [SECURITY.md](SECURITY.md)。

## 接下来做什么？

1. 使用 SQLite 或 PostgreSQL 保存任务
2. 增加登录、权限和审计记录
3. 支持进度、追问、取消和文件
4. 在更安全的容器中运行 Agent，并限制网络出口
5. 接入 A2A 和 MCP Agent
6. 单 Agent 路径稳定后，再增加多 Agent 工作流

## 保持核心体验简单

OpenAgentRelay 的核心只有三件事：

```text
发布一个团队可用的东西
提交一个任务
查看执行结果
```

排队、重试、传输、存储和协议兼容等复杂性，都应该隐藏在这个简单体验之后。

项目采用 Apache-2.0 许可证。
