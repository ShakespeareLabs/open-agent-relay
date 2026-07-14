# OpenAgentRelay

[English](README.md) | [简体中文](README.zh-CN.md)

> **让任何本地 Agent 或自动化，成为团队可以直接调用的能力。**

OpenAgentRelay 让同事或另一个 Agent，直接调用你电脑上已经能工作的能力。调用者只需安装一个很小的 `relay` 命令，不需要 OpenAgentRelay 仓库，也不需要你的 Agent 源码、依赖、Prompt 或业务凭证。

`main` 分支是一个**仅用于可信局域网直连的 Alpha**。它使用普通 HTTP 和共享 Key。不要暴露到公网，也不要接入生产写操作。

```text
调用者或调用 Agent  ── 可信局域网 ──>  发布者的 relay  ──>  本地 Agent
          ↑                                                   |
          └────────────────────── 返回结果 ────────────────────┘
```

## 不知道怎么用？把这个链接直接发给你的 Agent

把下面这个项目链接直接发给能够读取网页的 Codex、Claude Code 或其他 Agent：

```text
https://github.com/ShakespeareLabs/open-agent-relay
```

然后告诉 Agent 你是要“发布能力”还是“调用能力”。Agent 可以自己阅读这份 README，在不克隆仓库的情况下安装 `relay` CLI，并指导或直接完成后续操作。

如果你是发布者，可以直接复制这段话：

```text
请阅读 https://github.com/ShakespeareLabs/open-agent-relay，帮我把一个已经能工作的
本地 Agent 发布成可信局域网能力。只安装 relay CLI，不要克隆仓库。先运行安全测试，
再使用独立工作区和最小权限凭证接入真实 Agent。最后告诉我 Relay 地址、Agent 名称，
以及应该发给调用者的完整连接说明。遇到涉及安全范围的选择时先停下来问我。
```

如果你是调用者，请通过私密方式提供连接信息，再复制这段话：

```text
请阅读 https://github.com/ShakespeareLabs/open-agent-relay，帮我调用别人共享的能力。
只安装 relay CLI，不要克隆仓库。调用时使用 --expect-agent 和 --json，把非零退出码
视为失败，并且永远不要打印 Access Key。

Relay 地址：<发布者提供的地址>
Agent 名称：<发布者提供的名称>
```

Access Key 应通过 `RELAY_ACCESS_KEY` 提供，不要直接写进发给 Agent 的消息。Agent 只需要这个链接和私密连接信息，不需要 OpenAgentRelay 源码。

## 安装 CLI

普通用户不需要克隆仓库。推荐通过 [`pipx`](https://pipx.pypa.io/) 安装 CLI：

```bash
pipx install "git+https://github.com/ShakespeareLabs/open-agent-relay.git@main"
relay version
```

如果还没有 `pipx`，请先按它的安装说明完成一次性安装；macOS 通常可以使用 `brew install pipx`。

如果已经进入 Python 3.11 或更高版本的虚拟环境，也可以使用：

```bash
python -m pip install "git+https://github.com/ShakespeareLabs/open-agent-relay.git@main"
```

只有参与开发时才需要克隆仓库。首个正式安装包发布后，主要安装命令会简化为 `pipx install open-agent-relay`。

## 发布者：发布一个能力

发布者拥有已经能正常工作的 Agent 或自动化。

### 1. 先用安全示例测试

设置一个至少 16 个字符的 Access Key，并避免写入 Shell 历史：

```bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
```

启动一个无副作用的测试能力：

```bash
relay serve \
  --host 0.0.0.0 \
  --port 8787 \
  --name uppercase \
  --description "将文本转换为大写" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
```

启动成功后会确认配置的 Key 已加载，并显示 `Serving uppercase on http://0.0.0.0:8787`。如果没有配置 Key，Relay 才会生成并显示一个临时 Key。在发布者电脑上验证服务：

```bash
curl http://127.0.0.1:8787/healthz
```

预期返回 `{"status":"ok"}`。

### 2. 把连接信息发给调用者

找到发布者的局域网地址。macOS 常用 `ipconfig getifaddr en0`，Linux 常用 `hostname -I`。通过可信渠道把下面这些信息完整发给调用者：

```text
Relay 地址： http://192.168.1.42:8787
Agent 名称： uppercase
Access Key：<RELAY_ACCESS_KEY 的值>
用途：       将文本转换为大写
信任范围：   可信局域网 Alpha；禁止敏感数据和生产写操作
```

`0.0.0.0` 只是监听地址，不能让调用者直接使用。发布者的防火墙还可能需要允许 8787 端口的 TCP 入站连接。

### 3. 发布现有命令

Relay 每次收到请求都会启动一次命令。该命令必须：

- 从标准输入读取一个请求；
- 把最终答案写入标准输出；
- 把日志和诊断信息写入标准错误；
- 完成当前请求后退出。

```bash
relay serve \
  --host 0.0.0.0 \
  --name ads-report \
  --description "只读广告数据报告" \
  -- python /path/to/ads_report.py
```

### 4. 发布一个受限 Codex 能力

请使用独立工作区和完成这一项能力所需的最小权限凭证。不要发布拥有全部个人文件、MCP、Skills 和 Token 的日常 Codex 环境。

```bash
relay serve \
  --host 0.0.0.0 \
  --name code-reviewer \
  --description "只读审查独立工作区" \
  -- codex exec \
       --ephemeral \
       --sandbox read-only \
       --ignore-user-config \
       --skip-git-repo-check \
       -C /path/to/restricted-workspace \
       -
```

每个请求通常都会启动一次新的 `codex exec`。Codex 可以使用受限工作区中可访问的内容，但 Relay 不会自动恢复发布者过去的 Codex Session。

## 调用者：调用一个能力

调用者只需要 `relay` CLI 和连接信息，不需要发布者的仓库或 Agent 实现。

加载共享 Key，并避免写入命令历史：

```bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
```

### 直接执行

供人使用：

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent uppercase \
  "hello team"
```

供另一个 Agent 或自动化使用时，始终请求 JSON：

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent uppercase \
  --json \
  "hello team"
```

成功输出：

```json
{
  "capability": "uppercase",
  "result": "HELLO TEAM"
}
```

### 深度交互

默认调用不保留上下文。需要连续追问时，先创建一段由 Relay 管理的对话：

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent ads-report \
  --new-conversation \
  --json \
  "分析这个广告账户"
```

保存返回的 `conversation_id`，然后继续：

```bash
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent ads-report \
  --conversation conv_... \
  --json \
  "哪个广告系列最差？"
```

Relay 在内存中保存有长度上限的文本记录，再把它注入一次新的 Agent 执行。对话默认一小时过期，服务器重启后消失。本地 Caller ID 可以防止不同调用者意外续接，但它不是真正的个人身份认证。

## 把这个能力交给另一个 Agent

先在调用 Agent 的环境中配置 `RELAY_ACCESS_KEY`，再把下面的连接说明交给它：

```text
你可以通过 relay CLI 调用一个远程能力。

目标：http://192.168.1.42:8787
预期 Agent：ads-report

单次请求使用：
relay ask --target http://192.168.1.42:8787 --expect-agent ads-report --json "<请求>"

连续追问时，第一次加 --new-conversation，保存 JSON 中的 conversation_id，
后续使用 --conversation <conversation_id>。非零退出码代表失败。
不要打印或返回 RELAY_ACCESS_KEY。
```

Agent 只需要 CLI 和连接说明，不需要 OpenAgentRelay 仓库。

## 错误与重试

CLI 运行错误会返回非零退出码，并把 JSON 错误写入标准错误：

```json
{"error":{"status":401,"code":"UNAUTHORIZED","message":"a valid access key is required"}}
```

常见错误：

| 错误码 | 含义 | 调用者如何处理 |
|---|---|---|
| `CONNECTION_ERROR` | 地址错误、服务停止或防火墙拦截 | 检查地址、局域网、服务和端口 |
| `UNAUTHORIZED` | Access Key 缺失或错误 | 重新加载共享 Key |
| `AGENT_MISMATCH` | 公开 Agent 名称不一致 | 停止调用并向发布者确认 |
| `BUSY` | Agent 执行并发已满 | 延迟后重试 |
| `EXECUTION_TIMEOUT` | 本地 Agent 超过执行时间 | 联系发布者或缩小请求 |
| `OUTPUT_TOO_LARGE` | Agent 输出超过上限 | 要求返回更小的结果 |

公开 Agent Card 位于 `/.well-known/agent-card.json`。人类调用者也可以直接在浏览器中打开 Relay 地址并输入 Access Key。

## 安全边界

- Bearer 认证只有一个共享 Key，不能识别具体是哪位同事；
- 网络传输使用普通 HTTP，能观察局域网流量的人可能看到 Key、输入和输出；
- `--expect-agent` 只能防止配置错误，不能从密码学上证明服务器身份；
- 调用者输入不可信。Agent 可能读取其进程有权访问的文件、调用工具或返回敏感数据；
- 应使用独立工作区、只读工具、最小权限凭证和范围明确的能力；
- 不要把端口暴露到公网，也不要接入生产写操作。

发布真实 Agent 前，请阅读 [SECURITY.md](SECURITY.md)。

## 限制与当前范围

`relay serve --help` 可以配置执行超时、请求大小、输出大小、执行并发和对话有效期。0.1 版本不包含 TLS、个人权限、自动发现、文件传输、进度流、持久对话、一个地址挂载多个 Agent，也不提供 Relay 自身的执行沙箱。

异步 Hub + Runner 实验仍保留在 [`hub-mode` 分支](https://github.com/ShakespeareLabs/open-agent-relay/tree/hub-mode)，不属于这条直连 Alpha 使用路径。

参与源码开发请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。项目采用 Apache-2.0 许可证。
