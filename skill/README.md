# sumosearch Skill for Claude / GitHub Copilot

This directory contains a Claude skill that lets Claude (and any AI assistant
that supports Claude skills) fetch logs from Sumo Logic using the `sumosearch`
CLI.

## What the skill does

- Checks that `sumosearch` is installed; offers to install it if not
- Collects the required arguments (`--query`, `--from`, `--to`) from the user
  if they are not already provided
- Constructs and runs `sumosearch fetch` with the right flags
- Handles common errors (missing credentials, auth failures, rate limits, job
  timeouts) and guides the user to fix them
- Returns results to Claude so it can analyze, summarize, or investigate further

The skill is designed to be used standalone ("show me errors from the payments
service in the last hour") or called by another skill that provides all the
flags directly (e.g. an incident-investigation skill).

## Directory layout

```
skill/
  sumosearch/
    SKILL.md          # The skill definition loaded by Claude
    evals/
      evals.json      # Test cases for validating the skill
  README.md           # This file
```

## Installation

### Claude Code

Copy the `sumosearch` skill folder into your Claude skills directory:

```bash
cp -r skill/sumosearch ~/.claude/skills/sumosearch
```

Claude Code will pick it up automatically on the next session. You can verify
with:

```bash
claude skills list
```

### GitHub Copilot (VS Code)

Copy the skill folder to the Copilot skills location used by your
organisation's Copilot configuration. The exact path depends on your
enterprise setup — refer to your internal Copilot docs. Typically:

```bash
cp -r skill/sumosearch <your-copilot-skills-dir>/sumosearch
```

## Prerequisites

The skill assumes `sumosearch` is installed and credentials are configured. If
not, the skill will guide the user through both steps.

**Install sumosearch:**

```bash
uv tool install sumosearch --from git+https://github.com/sdsahib/sumo-search.git
```

**Configure credentials:**

```bash
sumosearch init
```


## Usage examples

Once installed, just talk to Claude naturally:

> "Show me errors from the checkout service `_sourceCategory=prod/checkout` between 9am and 10am UTC today"

> "Fetch the last hour of logs from `_sourceCategory=prod/api` as JSON"

> "Search Sumo Logic for pod=payments-service timeouts in the last 30 minutes"

Claude will fill in any missing details, run the search, and return the results.

## Building on top of this skill

If you are writing your own skill that needs to fetch logs as a step, you can
delegate to this skill by providing all required flags:

```
query: _sourceCategory=prod/payments timeout
from: 2026-03-20T08:30:00
to: 2026-03-20T09:00:00
format: json
pages: 5
```

The sumosearch skill will run the command and return structured JSON output
for your skill to process.
