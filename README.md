# OpenAgentRelay — Hub mode

[English](README.md) | [简体中文](README.zh-CN.md)

> **Submit work to a remote agent without copying its code, environment, or business credentials.**

This branch is the asynchronous Hub experiment. For direct calls on a trusted LAN, use the [`main` branch](https://github.com/ShakespeareLabs/open-agent-relay).

## How it works

~~~text
Caller Agent → Hub stores a task → Runner claims it → Local Agent runs
     ↑                                                   |
     └──────────────── result through Hub ───────────────┘
~~~

The caller can disconnect while work runs. The Runner connects outward to the Hub, so the machine hosting the agent does not need a public inbound port.

## Install

Requires Python 3.11 or newer:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
~~~

## 1. Start the Hub

Create two different keys without putting them in shell history:

~~~bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
read -s RELAY_RUNNER_KEY
export RELAY_RUNNER_KEY
relay hub
~~~

- Share the **Client Key** with callers.
- Share the **Runner Key** only with machines that provide capabilities.
- If either variable is missing, `relay hub` generates and prints a temporary key.

The Client Key can list capabilities, submit tasks, and read results. It cannot publish, claim, heartbeat, complete, or fail tasks.

## 2. Publish an agent

On the machine where the working agent and its business credentials already exist:

~~~bash
export RELAY_RUNNER_KEY="the Hub runner key"
relay expose \
  --hub http://HUB_ADDRESS:8787 \
  --name ads-report \
  --description "Check ad data and create a report" \
  -- python ads_report.py
~~~

The command reads one request from standard input and prints one result to standard output. Its code, Skills, environment, and business credentials remain on this machine.

## 3. Ask from another agent

~~~bash
export RELAY_ACCESS_KEY="the Hub client key"
relay ask \
  --hub http://HUB_ADDRESS:8787 \
  --agent ads-report \
  --wait \
  --json \
  "Show the campaigns with the largest CPA increase"
~~~

`--json` prints one machine-readable task object. A completed command exits with status 0. A failed, cancelled, timed-out, unauthorized, or malformed request exits nonzero.

## Reliability model

When a Runner claims a task, the Hub gives it a temporary lease:

- the Runner sends heartbeats while the agent works;
- an expired lease returns the task to the queue;
- the task retries up to `max_attempts` (default 3, maximum 10);
- repeating the same completion with the same lease and result is idempotent;
- a stale lease or a different repeated result is rejected.

This is **at-least-once execution**. If a Runner performs an external side effect and loses its lease before reporting completion, a retry can execute that side effect again. Prefer read-only agents or make write operations idempotent and approval-gated.

Useful controls:

~~~text
relay hub:    --lease-seconds --max-request-bytes --max-concurrency
relay expose: --request-timeout --execution-timeout
relay ask:    --request-timeout --wait-timeout --max-attempts
~~~

All HTTP errors use a stable JSON envelope:

~~~json
{"error":{"code":"UNAUTHORIZED","message":"valid credentials are required"}}
~~~

## Security boundary

This is still a development preview:

- transport is plain HTTP, not TLS;
- Client and Runner keys identify roles, not individual people;
- tasks and capabilities live only in memory;
- agent execution is not sandboxed;
- there is no per-user policy or approval gate;
- request size and Hub concurrency are bounded, but there is no per-user rate limit.

Use it only on a trusted network. Do not expose this preview directly to the public internet or connect production write operations. Read [SECURITY.md](SECURITY.md).

## What this branch proves

- callers and Runners can be on different networks;
- callers do not need the agent's source code or business credentials;
- role-separated keys prevent callers from impersonating Runners;
- leases, heartbeats, bounded retries, and idempotent completion prevent common stuck-task failures;
- CLI output is suitable for another Agent to parse.

## Still missing

- TLS and per-user identity
- persistent task storage
- durable audit logs
- files, progress streaming, cancellation, and approvals
- container isolation and network egress policy
- multiple Hub replicas

Licensed under Apache-2.0.
