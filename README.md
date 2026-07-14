# OpenAgentRelay

[English](README.md) | [简体中文](README.zh-CN.md)

> **Turn any local agent or automation into something your whole team can use.**

## What does this project do?

Imagine you built a script that can check ad data, summarize interviews, or generate a weekly report.

It works on your computer, but when a teammate wants to use it, you normally have to send them:

- the code
- setup instructions
- dependencies
- prompts and rules
- API tokens or account configuration

Then every teammate has to install and maintain their own copy.

OpenAgentRelay takes a different approach:

1. Your working agent or script stays on your computer or server.
2. You give it a name in the team Hub, such as `ads-report`.
3. A teammate sends a request to that name.
4. Your agent runs the task and sends the result back.

Your teammates use the result without installing your project or receiving a copy of its credentials.

## A simple example

You have a local script called `ads_report.py`.

You make it available to your team:

```bash
relay expose \
  --name ads-report \
  --description "Check ad data and create a report" \
  -- python ads_report.py
```

A teammate can now submit:

```bash
relay ask \
  --agent ads-report \
  --wait \
  "Show me the campaigns with the biggest CPA increase this week"
```

OpenAgentRelay sends the request to your running script and returns its answer to the teammate.

The script still runs where you control it. Its code and credentials do not need to be sent to the caller.

## Is this only for AI agents?

No. You can connect:

- an AI agent
- a Python or shell script
- an internal automation
- a data query tool
- a report generator
- an existing HTTP or A2A agent in a future adapter

OpenAgentRelay calls all of these **capabilities**: things that can accept a task and return a result.

## How is this different from sharing a Skill?

A Skill teaches another agent **how to do something**. The user has to install it and provide the tools, environment, and credentials it needs.

OpenAgentRelay lets people **use something that is already running**.

| Sharing a Skill | Using OpenAgentRelay |
|---|---|
| Everyone installs a copy | The author runs one working copy |
| Everyone sets up dependencies | The author maintains the working environment |
| Everyone configures credentials | Credentials can stay with the runner |
| Updates require reinstalling | The author updates once |
| Work happens separately on each computer | Requests and results go through one task Hub |

Skills and OpenAgentRelay can work together. An agent may use many Skills internally, while Relay makes that agent available to the team.

## How it works

```text
Teammate submits a request
          ↓
The Hub stores the task
          ↓
Your Runner picks it up
          ↓
Your local agent or script runs
          ↓
The result goes back to the teammate
```

The Runner connects outward to the Hub. You do not need to open a public port on your computer.

## Try it in five minutes

You need Python 3.11 or newer. The current version has no third-party runtime dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Start the Hub:

```bash
relay hub
```

In another terminal, publish a tiny example automation:

```bash
relay expose \
  --name uppercase \
  --description "Turn text into uppercase" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
```

Submit a task:

```bash
relay ask --agent uppercase --wait "hello team"
```

You should receive `HELLO TEAM`.

You can also open [http://127.0.0.1:8787](http://127.0.0.1:8787) and submit a task from the small Web interface.

## What version 0.1 can do

- register an agent or automation by name
- accept tasks from the CLI or Web page
- let a local Runner pick up tasks
- pass text into any command through standard input
- return command output as the task result
- show clear task states and errors

## Important: version 0.1 is a local demo

Version 0.1 proves the basic idea, but it is **not ready for production credentials or the public internet**.

It does not yet include:

- user login
- resource-level permissions
- persistent task storage
- isolated execution
- approval steps for write operations
- secret scanning
- signed task permissions

Keep the Hub on localhost for now. Read [SECURITY.md](SECURITY.md) before connecting a real agent or credential.

## What comes next

1. Save tasks in SQLite or PostgreSQL
2. Add login, permissions, and audit records
3. Support progress updates, questions, cancellation, and files
4. Run agents in safer containers with network controls
5. Connect A2A and MCP agents
6. Add multi-agent workflows after the single-agent path is reliable

## The small core

OpenAgentRelay is built around three simple actions:

```text
publish something the team can use
submit a task
watch the result
```

Queueing, retries, transport, storage, and protocol support should stay behind this simple experience.

Licensed under Apache-2.0.
