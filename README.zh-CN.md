# OpenAgentRelay — Hub 模式

[English](README.md) | [简体中文](README.zh-CN.md)

> **无需复制代码、环境和业务凭证，也能把任务交给远程 Agent。**

这个分支是异步 Hub 实验。如果只需要在可信局域网内直接调用，请使用 [`main` 分支](https://github.com/ShakespeareLabs/open-agent-relay)。

## 它如何工作？

~~~text
调用 Agent → Hub 保存任务 → Runner 领取 → 本地 Agent 执行
    ↑                                      |
    └──────────── 结果通过 Hub 返回 ────────┘
~~~

任务执行期间，调用者可以断开连接。Runner 主动连接 Hub，因此提供能力的电脑不需要开放公网入站端口。

## 安装

需要 Python 3.11 或更高版本：

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
~~~

## 1. 启动 Hub

创建两个不同的 Key，并避免写入 Shell 历史：

~~~bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
read -s RELAY_RUNNER_KEY
export RELAY_RUNNER_KEY
relay hub
~~~

- 把 **Client Key** 发给调用者；
- **Runner Key** 只发给提供能力的机器；
- 如果没有设置环境变量，`relay hub` 会自动生成并显示临时 Key。

Client Key 只能查看能力、提交任务和读取结果，不能发布、领取、心跳、完成或标记失败任务。

## 2. 发布一个 Agent

在已经拥有 Agent、Skills 和业务凭证的电脑上：

~~~bash
export RELAY_RUNNER_KEY="Hub 的 Runner Key"
relay expose \
  --hub http://HUB_ADDRESS:8787 \
  --name ads-report \
  --description "查询广告数据并生成报告" \
  -- python ads_report.py
~~~

命令从标准输入读取一个请求，再把一个结果输出到标准输出。代码、Skills、运行环境和业务凭证继续留在这台电脑上。

## 3. 让另一个 Agent 调用

~~~bash
export RELAY_ACCESS_KEY="Hub 的 Client Key"
relay ask \
  --hub http://HUB_ADDRESS:8787 \
  --agent ads-report \
  --wait \
  --json \
  "找出 CPA 上涨最多的广告系列"
~~~

`--json` 只输出一个便于 Agent 解析的任务对象。成功完成时退出码为 0；失败、取消、等待超时、认证失败或请求错误都会返回非零退出码。

## 可靠性逻辑

Runner 领取任务后，Hub 会发放一个临时租约：

- Agent 执行期间，Runner 定期发送心跳；
- 租约过期后，任务自动回到队列；
- 任务最多重试 `max_attempts` 次，默认 3 次，最大 10 次；
- 使用同一租约重复提交相同结果是幂等的；
- 过期租约或不同的重复结果会被拒绝。

这是**至少执行一次**语义。如果 Runner 完成外部写操作后、上报结果前失去租约，重试可能再次执行该写操作。应优先发布只读 Agent；写操作必须自身幂等，并增加审批。

可以配置：

~~~text
relay hub:    --lease-seconds --max-request-bytes --max-concurrency
relay expose: --request-timeout --execution-timeout
relay ask:    --request-timeout --wait-timeout --max-attempts
~~~

所有 HTTP 错误使用稳定的 JSON 结构：

~~~json
{"error":{"code":"UNAUTHORIZED","message":"valid credentials are required"}}
~~~

## 安全边界

它仍然是开发预览版本：

- 使用普通 HTTP，没有 TLS；
- Client Key 和 Runner Key 只能识别角色，不能识别具体个人；
- 任务和能力只保存在内存中；
- Agent 执行没有沙箱隔离；
- 没有个人权限和写操作审批；
- 已限制请求大小和 Hub 并发，但没有每位用户独立限流。

只能用于可信网络。不要直接暴露到公网，也不要接入生产写操作。请阅读 [SECURITY.md](SECURITY.md)。

## 这个分支已经证明什么？

- 调用者和 Runner 可以处在不同网络；
- 调用者不需要 Agent 源码和业务凭证；
- 角色分离 Key 可以阻止普通调用者冒充 Runner；
- 租约、心跳、有限重试和幂等完成可以避免常见的任务卡死；
- CLI 输出可以被另一个 Agent 稳定解析。

## 还缺少什么？

- TLS 和个人身份认证
- 持久化任务存储
- 持久化审计日志
- 文件、进度流、取消和审批
- 容器隔离与网络出口限制
- 多 Hub 副本

项目采用 Apache-2.0 许可证。
