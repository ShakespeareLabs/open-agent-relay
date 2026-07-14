# OpenAgentRelay

[English](README.md) | [简体中文](README.zh-CN.md)

> **Turn any local agent or automation into a team-callable capability.**

The `main` branch starts with the simplest mode: direct calls over a trusted LAN.

## What does it solve?

You already have an agent or script that works on your computer. A teammate wants to use it.

Normally, you send them the code, dependencies, setup guide, prompts, and credentials so they can run another copy.

OpenAgentRelay lets them call the working copy on your computer instead.

~~~text
Teammate's computer  ──local network──>  Your computer  ──>  Your agent
                                                |
Teammate receives result  <─────────────────────┘
~~~

The main branch does not need a Hub. Your code, environment, prompts, and business credentials stay on your machine.

## Two-computer example

Both computers must be on the same trusted local network.

### 1. On the computer that owns the agent

Install the project:

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
~~~

Serve a local command on the LAN:

~~~bash
relay serve \
  --host 0.0.0.0 \
  --port 8787 \
  --name uppercase \
  --description "Turn text into uppercase" \
  -- python -c 'import sys; print(sys.stdin.read().upper())'
~~~

OpenAgentRelay prints a temporary access key. Share that key and this computer's local IP address with your teammate. For example, the IP may be 192.168.1.42.

### 2. On a teammate's computer

Install OpenAgentRelay, then call the machine directly:

~~~bash
read -s RELAY_ACCESS_KEY
export RELAY_ACCESS_KEY
relay ask \
  --target http://192.168.1.42:8787 \
  --expect-agent uppercase \
  "hello team"
~~~

Using `RELAY_ACCESS_KEY` keeps the key out of the command line and shell history.
`--expect-agent` checks the public agent card before execution and prevents accidental calls to the wrong name. Plain HTTP still cannot prove the server's cryptographic identity.

The teammate receives:

~~~text
HELLO TEAM
~~~

They can also open http://192.168.1.42:8787 in a browser and enter the same access key.

## Use your own agent

If your existing agent reads a request from standard input and prints its answer to standard output:

~~~bash
relay serve \
  --host 0.0.0.0 \
  --name ads-report \
  --description "Check ad data and create a report" \
  -- python ads_report.py
~~~

A teammate calls it with:

~~~bash
relay ask \
  --target http://192.168.1.42:8787 \
  "Show the campaigns with the biggest CPA increase this week"
~~~

OpenAgentRelay passes the request to ads_report.py and returns whatever the script prints.

## Continue a conversation

Direct calls are stateless by default. Start an isolated Relay-managed conversation when follow-up questions need prior context:

~~~bash
relay ask --target http://192.168.1.42:8787 --new-conversation --json "Analyze this account"
~~~

The response contains a random `conversation_id`. Continue it with:

~~~bash
relay ask --target http://192.168.1.42:8787 --conversation conv_... "Which campaign is worst?"
~~~

Relay keeps a bounded transcript in memory and passes it to a fresh agent execution. Conversations expire after one hour by default and disappear when the server restarts. A random caller ID stored locally binds the conversation to the caller; it is not a replacement for per-user authentication.

## What can be shared?

- an AI agent
- a Python or shell script
- a data query
- a report generator
- an internal automation

If it accepts a request and returns a result, a teammate can call it.

## How is this different from sharing a Skill?

A Skill teaches another agent how to do something. Every user still has to install it and prepare its tools, environment, and credentials.

OpenAgentRelay lets teammates call something that is already working on your computer.

| Sharing a Skill | OpenAgentRelay direct mode |
|---|---|
| Everyone installs a copy | One working copy stays on the author's machine |
| Everyone configures dependencies | The author keeps the working environment |
| Everyone needs business credentials | Business credentials stay with the serving process |
| Updates require reinstalling | The author updates one copy |
| Work runs separately on every machine | Teammates call the author's machine directly |

An agent can still use Skills internally. Relay only handles the direct request and response.

## Access key and security

Each server has one shared access key:

- provide one with `RELAY_ACCESS_KEY` (recommended) or `--access-key`, or
- let relay serve generate a temporary key at startup.

This key controls who can invoke the agent. It is not the Google, database, or other business credential used by the agent.

Version 0.1 still uses plain HTTP. The key is not encrypted while traveling over the network and it does not identify individual teammates. Use it only on a trusted LAN. Do not expose the port to the public internet or connect production write operations.

Read [SECURITY.md](SECURITY.md) before connecting a real agent.

## What version 0.1 includes

- direct calls between two computers
- a shared access key
- a small command-line client
- a small browser page
- an agent description at /.well-known/agent-card.json
- a stdin/stdout adapter for existing commands
- structured errors that hide local stderr from callers
- configurable execution and client timeouts
- request-size and execution-concurrency limits
- optional bounded, expiring conversations

## What version 0.1 does not include

- automatic discovery of computers
- per-user login or permissions
- TLS encryption
- offline tasks or queues
- progress updates or file transfer
- multiple agents behind one address
- public-internet connectivity

Run `relay serve --help` to configure execution timeout, request size, concurrency, and conversation expiry.

## Want the Hub experiment?

The earlier asynchronous Hub + Runner design is preserved on the [hub-mode branch](https://github.com/ShakespeareLabs/open-agent-relay/tree/hub-mode). It is a different mode with a different network model.

The main branch stays focused on one problem: **a teammate on the same LAN directly calls the agent running on your computer.**

Licensed under Apache-2.0.
