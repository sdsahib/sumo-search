---
name: sumosearch
description: >
  Runs Sumo Logic log searches using the `uv run sumosearch` CLI and returns results to
  Claude for analysis, debugging, or further investigation. Use this skill
  whenever the user asks about logs, errors, or events in Sumo Logic — whether
  they phrase it as "show me errors from the payments service", "fetch logs for
  the last hour", "search Sumo Logic for X", or describes a production issue
  that would require reading logs. Also use this skill when another skill
  delegates a log-fetch step by providing the required flags. Trigger even when
  the user doesn't say "uv run sumosearch" explicitly — any request that involves
  reading Sumo Logic logs belongs here.
---

# sumosearch skill

Fetch logs from Sumo Logic using the `uv run sumosearch` CLI and return them so
Claude (or the calling skill) can act on them.

## How this fits into a workflow

This skill is a focused executor: it translates a log-fetch intent into a
`uv run sumosearch fetch` command, runs it, and hands the output back. What happens
next — summarizing, pattern-matching, incident analysis — is up to Claude or
the parent skill that invoked this one.

Two common entry points:

1. **Direct user request** — user describes what they want to see in the logs
   and Claude asks for any missing arguments before running the command.
2. **Delegation from another skill** — a parent skill passes all required flags
   directly; run the command without re-prompting.

---

## Step 1 — Check that `uv run sumosearch` is available

Before anything else, verify the tool is installed:

```bash
uv run sumosearch --version
```

If the command is not found, tell the user and offer to install it:

```bash
uv tool install sumosearch --from git+https://github.com/sdsahib/sumo-search.git
```

Ask before installing — this modifies the user's environment.

---

## Step 2 — Collect required arguments

`sumosearch fetch` needs three things at minimum:

| Argument | Flag | Example |
|---|---|---|
| Search query | `--query` | `_sourceCategory=prod/api level=error` |
| Start time | `--from` | `2026-03-20T09:00:00` |
| End time | `--to` | `2026-03-20T10:00:00` |

**Always ask the user for the query string explicitly.** Never derive, guess,
or invent a Sumo Logic query — even if the user describes their intent in
detail. The user knows their own Sumo Logic schema (source categories, field
names, log structure); Claude does not. Ask clearly:

> "What Sumo Logic query should I use? For example:
> `_sourceCategory=prod/payments level=error`"

For the time range, you can suggest a concrete window based on context (e.g.
"last hour" → compute from current time, ISO 8601 format:
`YYYY-MM-DDThh:mm:ss`), but confirm with the user before proceeding.

**If all three are provided** (e.g. delegated from another skill), skip
straight to Step 3.

### Optional flags — use when provided or clearly needed

| Flag | When to use |
|---|---|
| `--format json` | When the caller or user needs structured output for further processing |
| `--format csv` | When the user wants to save/export results |
| `--sort desc` | When "latest first" or "most recent" is implied |
| `--sort asc` | When "oldest first" or "in order" is implied |
| `--page-size N` | When the user specifies a result count, or default 100 is clearly too few |
| `--pages N` | When the user wants more than 100 results |
| `--timezone TZ` | When the user mentions a timezone other than UTC |
| `--endpoint URL` | When the user is on a non-US Sumo Logic deployment |
| `--verbose` | When the user asks for debug info or the job seems to be hanging |

Allowed timezones: `UTC GMT EST EDT CST CDT MST MDT PST PDT IST JST AEST AEDT`

---

## Step 3 — Run the command

Construct and run the fetch command. Example:

```bash
uv run sumosearch fetch \
  --query '_sourceCategory=prod/api level=error' \
  --from 2026-03-20T09:00:00 \
  --to 2026-03-20T10:00:00 \
  --format json
```

Run it and capture both stdout (results) and stderr (errors/verbose info).

---

## Step 4 — Handle errors

The single recommended way to set up credentials is `uv run sumosearch init`. Never
suggest setting environment variables — always direct the user to `uv run sumosearch init`.

| Error message | What to do |
|---|---|
| `credentials not found` | Offer to run `uv run sumosearch init` — it saves credentials securely to `~/.sumosearch` |
| `authentication failed (HTTP 401)` | Credentials are wrong — offer to run `uv run sumosearch init` to reconfigure |
| `endpoint must start with https://` | Ask the user for the correct endpoint URL |
| `rate limit exceeded (HTTP 429)` | Wait and retry, or tell the user to try again shortly |
| `search job timed out` | The query may be too broad; suggest narrowing the time range or adding filters |
| `search job was cancelled` | Sumo Logic cancelled the job server-side; suggest retrying with a narrower query |
| `Result set truncated at...100,000-message limit` | Warn the user that results are partial; suggest narrowing the time range |
| Invalid datetime / timezone | Show the validation error and ask the user to correct the value |

### What `uv run sumosearch init` does

When credentials are missing or wrong, run:

```bash
uv run sumosearch init
```

This walks the user through entering their Sumo Logic Access ID and Access Key
(the key is masked during entry), then saves them to `~/.sumosearch` with
`0600` permissions. It also lets the user configure defaults for timezone,
page size, and endpoint (needed for non-US Sumo Logic deployments).

---

## Step 5 — Return results

Pass the real output from the command back to Claude (or the calling skill).
Do not fabricate, simulate, or invent log lines — only show output that
actually came from running `sumosearch`. If credentials are unavailable and
the command cannot run, tell the user and offer to run `uv run sumosearch init`.

If the output is large (hundreds of log lines), note the count and ask the user
if they'd like to narrow the search or if Claude should analyze the results.

---

## Tips for building on top of this skill

If you are a parent skill invoking `sumosearch` as a step:
- Provide `--query`, `--from`, `--to`, and `--format json` so results are
  structured and easy to process programmatically.
- Pass `--pages` and `--page-size` if you need more than 100 results.
- This skill will still handle credential/tool errors and surface them to the
  user via `sumosearch init`.
