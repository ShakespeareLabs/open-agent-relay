# OpenAgentRelay

[English](README.md) | [简体中文](README.zh-CN.md)

> **让任何本地 Agent 或自动化，成为团队可以直接调用的能力。**

`main` 分支先从最简单的模式开始：在可信局域网内直接调用。

## 它解决什么问题？

你的电脑上已经有一个能正常工作的 Agent 或脚本，同事也想使用。

通常你需要把代码、依赖、安装说明、Prompt 和凭证发给他，让他在自己的电脑上再运行一份。

OpenAgentRelay 让同事直接调用你电脑上已经能运行的这一份。

~~~text
同事的电脑  ──局域网──>  你的电脑  ──>  你的 Agent
                              |
同事收到结果  <───────────────┘
~~~

main 分支不需要 Hub。代码、运行环境、Prompt 和业务凭证继续留在你的电脑上。

## 两台电脑如何使用？

两台电脑需要连接同一个可信局域网。

### 1. 在拥有 Agent 的电脑上

安装项目：

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
~~~

把一个本地命令开放给局域网：

~~~bash
relay serve \
  --host 0.0.0.0 \
  --port 8787 \
  --name uppercase \
  --description "将文本转换为大写" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
~~~

OpenAgentRelay 会显示一个临时 Access Key。把这个 Key 和本机的局域网 IP 发给同事，例如 192.168.1.42。

### 2. 在同事的电脑上

安装 OpenAgentRelay，然后直接调用你的电脑：

~~~bash
relay ask \
  --target http://192.168.1.42:8787 \
  --access-key "RELAY_SERVE 显示的 KEY" \
  "hello team"
~~~

同事会收到：

~~~text
HELLO TEAM
~~~

同事也可以在浏览器中打开 http://192.168.1.42:8787，然后输入同一个 Access Key。

## 如何接入自己的 Agent？

假设现有 Agent 会从标准输入读取需求，再把答案输出到标准输出：

~~~bash
relay serve \
  --host 0.0.0.0 \
  --name ads-report \
  --description "查询广告数据并生成报告" \
  -- python ads_report.py
~~~

同事调用：

~~~bash
relay ask \
  --target http://192.168.1.42:8787 \
  --access-key "RELAY_SERVE 显示的 KEY" \
  "找出本周 CPA 上涨最多的广告系列"
~~~

OpenAgentRelay 会把需求交给 ads_report.py，再把脚本打印的结果返回给同事。

## 可以共享哪些东西？

- AI Agent
- Python 或 Shell 脚本
- 数据查询
- 报告生成器
- 内部自动化

只要它能接收需求并返回结果，同事就可以调用。

## 它和共享 Skill 有什么不同？

Skill 是在教另一个 Agent 如何完成一件事。每位使用者仍然需要安装 Skill，并准备工具、环境和凭证。

OpenAgentRelay 是让同事直接调用你电脑上已经能够运行的东西。

| 共享 Skill | OpenAgentRelay 直连模式 |
|---|---|
| 每个人安装一份 | 一个可运行版本留在作者电脑 |
| 每个人配置依赖 | 作者维护现有运行环境 |
| 每个人都需要业务凭证 | 业务凭证留在提供能力的进程中 |
| 更新后需要重新安装 | 作者只更新一份 |
| 每台电脑分别执行 | 同事直接调用作者电脑 |

Agent 内部仍然可以使用 Skill。Relay 只负责直接传递需求和返回结果。

## Access Key 和安全说明

每个服务都有一个共享 Access Key：

- 可以通过 --access-key 或 RELAY_ACCESS_KEY 指定；
- 如果没有指定，relay serve 会在启动时自动生成临时 Key。

这个 Key 只用于控制谁能调用 Agent。它不是 Agent 内部使用的 Google、数据库或其他业务凭证。

0.1 版本仍然使用普通 HTTP。Key 在网络传输中没有加密，也不能区分具体是哪位同事。它只能用于可信局域网。不要把端口暴露到公网，也不要接入生产写操作。

连接真实 Agent 前，请阅读 [SECURITY.md](SECURITY.md)。

## 0.1 版本包含什么？

- 两台电脑之间直接调用
- 共享 Access Key
- 简单的命令行客户端
- 简单的浏览器页面
- 通过 /.well-known/agent-card.json 查看 Agent 说明
- 通过 stdin/stdout 接入现有命令
- 不向调用者返回本地 stderr 的结构化错误

## 0.1 版本暂时没有什么？

- 自动发现局域网内的电脑
- 每位用户独立登录和权限
- TLS 加密
- 离线任务和队列
- 进度更新和文件传输
- 一个地址挂载多个 Agent
- 公网连接能力

## 如果需要 Hub 呢？

之前完成的异步 Hub + Runner 方案保留在 [hub-mode 分支](https://github.com/ShakespeareLabs/open-agent-relay/tree/hub-mode)。它是另一种网络模式，和直连模式分开维护。

main 分支只专注解决一个问题：**让同一局域网内的同事直接调用你电脑上正在运行的 Agent。**

项目采用 Apache-2.0 许可证。
