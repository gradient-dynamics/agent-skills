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
| `plugin.json`, `mcp.json` | The [Agent Plugins](https://agent-plugins.org) manifest and server for ChatGPT and Codex |

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
