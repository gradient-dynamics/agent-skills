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

## Install

### Claude Code plugin (skill plus MCP server)

Once this repository is public on GitHub:

```text
/plugin marketplace add gradient-dynamics/agent-skills
/plugin install gradient-dynamics@gradient-dynamics
```

Then run `/mcp`, select **gradient-dynamics** and choose **Authenticate**. You can
sign in or create an account in the browser, then choose a budget for the
connection.

To try it from a local checkout, run `claude --plugin-dir ./agent-skills`.

The plugin's server uses OAuth. To use an API key instead:

1. Skip the plugin's server (toggle it off in `/mcp`).
2. Add the server yourself with
   `claude mcp add --transport http gradient-dynamics https://api.gradient-dynamics.com/mcp --header "Authorization: Bearer $GD_API_KEY"`.

### The skill only (any Agent Skills client)

Copy `skills/thermal-simulation/` into your client's skills folder, for example
`~/.claude/skills/thermal-simulation/` for Claude Code. The frontmatter uses only
the portable Agent Skills fields: `name`, `description`, `compatibility` and
`metadata`.

With the open `skills` CLI, once the repository is public:

```sh
npx skills add gradient-dynamics/agent-skills
```

The skill still needs the MCP server connected. See
https://gradient-dynamics.com/llms.txt for Claude, Cursor, Codex, ChatGPT and
headless setup.

## Status

- **Not published.** This is a local repository with no remote. Nothing has been
  pushed, submitted to a directory or published as a package.
- **Validated (2026-10-22, Claude Code 2.1.300):**
  - `claude plugin validate --strict .` passes for the marketplace and its plugin;
  - `claude plugin validate --strict .claude-plugin/plugin.json` passes;
  - the skill name and description were checked against the Agent Skills
    constraints: name ≤64 characters in lowercase-hyphen form and matching the
    folder; description 718 of 1,024 characters.
- **Before publishing, James must:**
  - choose a license and add `LICENSE`, plus `"license"` in `plugin.json`;
  - add `supportUrl`, `privacyPolicyUrl` and `termsOfServiceUrl` to `plugin.json`
    for Anthropic's plugin directory;
  - create `github.com/gradient-dynamics/agent-skills` and push.

  See `api/docs/directory-submission-checklist.md` in the API repository.
- **Cursor** uses its own manifest (`.cursor-plugin/plugin.json` and `mcp.json`).
  That isn't included yet; the same `skills/` folder can be reused.
- **Behaviour still rolling out:** OAuth sign-in, sign-up inside the connection,
  no-sign-in discovery, the sandbox and the Developer tier are being enabled in
  stages. Until then, connect with an API key from Studio → Developer.

## Updating

The skill names real MCP tools (`estimate_cost`, `create_mesh`,
`run_simulation`, `view_simulation_result`, …). When tools are renamed or added
on the server, update the skill and bump `version` in `plugin.json` and the
skill's `metadata.version`.
