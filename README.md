# Gradient Dynamics agent skills

Skills and a Claude Code plugin that teach AI agents to run thermal and CFD
simulations of cooling hardware with [Gradient Dynamics](https://gradient-dynamics.com).
The hardware covered is cold plates, heat sinks, battery packs and electronics.

The agent:

1. picks a template or imports the user's CAD;
2. inspects it for real component, zone and patch names;
3. estimates the cost and asks before spending;
4. meshes and runs GPU CFD or conjugate heat transfer;
5. reports results with their convergence and quality flags.

It stops instead of looping when a run isn't funded or can't succeed.

| Path | What it is |
|---|---|
| `skills/thermal-simulation/SKILL.md` | The `thermal-simulation` [Agent Skill](https://agentskills.io/specification): when to use it, the workflow, boundary tagging, estimate-before-run, budget etiquette and stopping rules |
| `.claude-plugin/plugin.json` | Claude Code plugin manifest (`gradient-dynamics`) |
| `.mcp.json` | The plugin's MCP server: `https://api.gradient-dynamics.com/mcp` over HTTP, signing in with OAuth |
| `.claude-plugin/marketplace.json` | Makes this repository a plugin marketplace (also named `gradient-dynamics`) that lists the plugin at the repository root |
| `assets/icon.png` | Listing icon (1250×1250 logo) |
| `plugin.json`, `mcp.json` | The [Agent Plugins](https://agent-plugins.org) manifest and server for OpenAI's plugin directory (ChatGPT and Codex). OpenAI's listing, test cases and commerce declaration are under `extensions.com.openai` |
| `assets/composer-icon.png` | OpenAI composer icon (128×128, from the logo) |

## Install

### Claude Code plugin (skill plus MCP server)

```text
/plugin marketplace add gradient-dynamics/agent-skills
/plugin install gradient-dynamics@gradient-dynamics
```

Then run `/mcp`, select **gradient-dynamics** and choose **Authenticate**. You can
sign in or create an account in the browser, then choose a budget for the
connection.

To try it from a local checkout, run `claude --plugin-dir ./agent-skills`.

The plugin's server uses OAuth. To use an API key instead, see
[Connect from Claude](https://docs.gradient-dynamics.com/connect/from-claude.html).

### The skill only (any Agent Skills client)

Copy `skills/thermal-simulation/` into your client's skills folder, for example
`~/.claude/skills/thermal-simulation/` for Claude Code. The frontmatter uses only
the portable Agent Skills fields: `name`, `description`, `compatibility` and
`metadata`.

With the open `skills` CLI:

```sh
npx skills add gradient-dynamics/agent-skills
```

The skill still needs the MCP server connected. See
https://gradient-dynamics.com/llms.txt for Claude, Cursor, Codex, ChatGPT and
headless setup.

## Status

- **Public on GitHub (2026-11-17)** at `github.com/gradient-dynamics/agent-skills`.
  Not yet submitted to Claude's or OpenAI's directory.
- **Validated (2026-10-22, Claude Code 2.1.300):**
  - `claude plugin validate --strict .` passes for the marketplace and its plugin;
  - `claude plugin validate --strict .claude-plugin/plugin.json` passes;
  - the skill name and description were checked against the Agent Skills
    constraints: name ≤64 characters in lowercase-hyphen form and matching the
    folder; description 718 of 1,024 characters.
- **Directory-ready (2026-11-17):** MIT licence (`LICENSE`, `"license": "MIT"`), and
  support, privacy and terms URLs in `.claude-plugin/plugin.json`.
  `claude plugin validate . --profile directory` passes, also on a fresh clone
  from GitHub. The submission steps are in
  `api/docs/directory-submission-checklist.md` in the API repository.
- **Cursor** uses its own manifest (`.cursor-plugin/plugin.json` and `mcp.json`).
  That isn't included yet; the same `skills/` folder can be reused. The root
  `mcp.json` is now in Agent Plugins format, so check whether Cursor reads that
  format before adding a Cursor-specific one.
- **Behaviour still rolling out:** OAuth sign-in, sign-up inside the connection,
  no-sign-in discovery, the sandbox and the Developer tier are being enabled in
  stages. Until then, connect with an API key from Studio → Developer.

## OpenAI plugin directory (ChatGPT and Codex)

One listing covers ChatGPT and Codex. The build script lives in the API repository
(`api/scripts/build_openai_plugin.py`), because Claude's plugin directory refuses
scripts in this repository. From the API repository, with this checkout next to it:

```sh
python3 scripts/build_openai_plugin.py
```

Pass `--source PATH` if this checkout is somewhere else. It checks `plugin.json` and `mcp.json` against OpenAI's rules (field lengths, icon
sizes, exactly 5 positive and 3 negative test cases, one HTTPS server with no
headers, no credentials in the package) and writes
`dist/gradient-dynamics-openai-<version>.zip`. While anything is missing it lists
the problems and stops; `--draft` builds anyway (`…-draft.zip`) so you can try
the dashboard's automated checks. Both manifests also validate against the
official Agent Plugins 1.0.0 schemas.

`plugin.json` is complete: the support, privacy and terms URLs point at live pages
on `gradient-dynamics.com`, and `review.demo_recording_url` is
`https://gradient-dynamics.com/media/demo_codex.mp4`.

Chosen in the dashboard, not in the ZIP:

- **Category:** `plugin.json` says `Productivity`, OpenAI's documented example;
  pick the closest category the dashboard offers.
- **Authentication:** OAuth with CIMD, or DCR as a fallback. See "Mixed sign-in"
  in `api/docs/directory-submission-checklist.md` before choosing Mixed.
- **Domain verification:** the dashboard shows a token; serve it with
  `GD_OPENAI_APPS_CHALLENGE` on the API (route `/.well-known/openai-apps-challenge`).
- **Reviewer credentials and countries.** Credentials never go in the ZIP.

The review test cases name real tools, and cases 4 and 5 need the reviewer
account's sample project to hold a finished mesh and simulation.

## Updating

The skill names real MCP tools (`estimate_cost`, `create_mesh`,
`run_simulation`, `view_simulation_result`, …). When tools are renamed or added
on the server, update the skill and the OpenAI test cases, and bump `version` in
`.claude-plugin/plugin.json`, `plugin.json` and the skill's `metadata.version`.
