---
name: thermal-simulation
description: Runs thermal and CFD simulations of cooling hardware with the Gradient Dynamics MCP server, covering cold plates, heat sinks, battery-pack cooling, electronics enclosures and other liquid or air cooling. Use when the user wants temperatures, junction or case temperature against a limit, coolant temperature rise, pressure drop, flow distribution, heat transfer or conjugate heat transfer (CHT), or wants to compare cooling designs from a template or their own STEP or STL. Covers template or upload, geometry inspection, cost estimate, meshing, GPU simulation and reading quality flags, within a budget a person set. Not for hand calculations, electrical, structural or acoustic analysis, or arbitrary solver scripts.
compatibility: Requires network access to the Gradient Dynamics MCP server at https://api.gradient-dynamics.com/mcp (Streamable HTTP) and a signed-in connection (OAuth) or API key for anything beyond discovery and estimates.
metadata:
  author: gradient-dynamics
  version: "0.1.0"
---

# Thermal and CFD simulation with Gradient Dynamics

Gradient Dynamics runs GPU-native CFD and conjugate heat transfer (CHT) for
cooling hardware. You drive it through the MCP server
`https://api.gradient-dynamics.com/mcp`. Meshing and simulation cost real money
from a budget a person set, so **estimate first, get a yes, and never loop on
failures.**

## When to use this skill

Use it when the user wants to:

- predict temperatures of a cold plate, heat sink, battery module, power
  electronics (GPU, CPU, IGBT) or an enclosure under a given heat load and
  coolant flow;
- check a design against limits: maximum junction or case temperature, coolant
  temperature rise, pressure drop, pump or fan budget;
- compare cooling concepts (channel count, fin type, plate size) or run a small
  parameter study;
- run steady RANS, URANS or CHT flow on geometry they have (STEP or STL), or on a
  template;
- see 3D results: geometry, mesh sections, temperature, pressure and velocity
  fields, streamlines.

## When not to use it

- **Quick estimates:** back-of-envelope thermal resistance or a ΔT = P/(ṁ·cp)
  check. Do those by hand, or use `estimate_cost` only if the user asks what a
  simulation would cost.
- **Other physics:** structural, electrical, EMC, acoustic or chemistry analysis.
- **Arbitrary solvers:** the server runs its own validated solvers on its own
  inputs, with no OpenFOAM scripts, shell or custom code.
- **Certification:** a single simulation is not a certification. Say so when the
  user treats one run as sign-off.

## Connect first

1. **Check the tools.** Look for tools such as `list_templates`, `estimate_cost`
   and `create_mesh`. If your client loads tools on demand, search for
   "Gradient Dynamics" or call `search_tools`.
2. **If they're missing,** tell the user how to connect, and don't improvise
   another route:
   - **Claude Code:**
     `claude mcp add --transport http gradient-dynamics https://api.gradient-dynamics.com/mcp`,
     then `/mcp` → **Authenticate**.
   - **Claude app:** Customize → Connectors → Add custom connector → the URL
     above, with **Use Claude's published identity**.
   - **Cursor:** `{"mcpServers":{"gradient-dynamics":{"url":"https://api.gradient-dynamics.com/mcp"}}}`
     in `~/.cursor/mcp.json`.
   - **Codex:** `[mcp_servers.gradient_dynamics]` with
     `url = "https://api.gradient-dynamics.com/mcp"`, then
     `codex mcp login gradient_dynamics`.
   - **Headless:** an API key as `Authorization: Bearer …` from an environment
     variable, or `gd login`.
   - **All options:** https://gradient-dynamics.com/llms.txt
3. **Without signing in,** you can use discovery and estimates:
   `get_capabilities`, `list_templates`, `get_template`, `get_request_schema`,
   `search_tools`, `get_tool_schema` and `estimate_cost`. Anything else returns
   401. When that happens, ask the user to sign in through their client's
   connect or authenticate button; the sign-up happens there too.
4. **Never ask for an API key in chat,** never echo one, and never put one in a
   URL or file the user might commit.

## Workflow

### 0. Pin down the question

Before any compute, ask for what changes the answer and isn't given:

- heat load in W, and where it's applied (which face, component or zone);
- coolant (water, water-glycol percentage, dielectric fluid or air), inlet
  temperature, and flow rate (L/min or m/s);
- limits: maximum temperature (junction or case), maximum pressure drop, envelope.

If the user delegates choices, use reasonable stated assumptions and list them.

### 1. Geometry

- **Template:** call `list_templates`, then `get_template` for parameters,
  bounds and output names. Then call `create_design_preview`, which creates a
  project if needed and shows a 3D viewer; continue a pending design with
  `get_design_preview`. The generic `cold_plate` template has a `Solid` body and a
  `Coolant` body. It's a concept, not a verified GPU package.
- **The user's CAD:** use `import_surface_attachment` for a file attached in chat
  (STL, STEP or 3MF). Use `open_surface_upload` only when the host can't hand the
  attachment over. Reuse an existing ready artifact rather than asking for another
  upload. Run 3MF through `reconstruct_cad` first.
- **Show it:** `view_geometry` opens it in the browser. Ask whether this is the
  geometry they meant before spending money on it.

### 2. Inspect: get the real names

- `inspect_mesh_geometry` returns actual component IDs, bounds in mm and
  watertightness. Structured internal-fluid, solid and CHT meshes must use these
  IDs.
- `read_artifact_summary` on the design (`design.json`) shows outputs and mesh
  requirements.
- `get_request_schema` with `operation: "mesh"`, then `"simulation"`, returns the
  exact contract, units and limits.

### 3. Estimate, then get approval (always)

Call `estimate_cost` before every mesh, simulation or study:

```json
{"operation": "mesh", "cells": 2000000}
{"operation": "simulation", "simulation_type": "cht", "cells": 2000000}
```

It returns A100-hours, £ and wall time as a low, expected and high range. Signed
in, it also says whether the plan, credits and connection budget would admit the
run. Tell the user the range and what's left in their budget, then ask: "Proceed?"
Wait for an explicit yes, unless they have already approved a spending limit for
this task and you're inside it.

### 4. Mesh

1. Check the request with `validate_mesh`. It costs nothing.
2. Submit `create_mesh` with a **fresh** `idempotency_key` for every new job.
   Reuse a key only to retry the same job after a network error.
3. Pick the engine:
   - `engine: "structured"`: stair-step or cut-cell; workflows external, internal,
     CHT and solid;
   - `engine: "openfoam"`: snappyHexMesh with optional prism layers.

   Ask about consequential choices (stair-step or cut-cell, boundary layers, cell
   budget); otherwise disclose your defaults.
4. Know the limits: at most 20 million cells, and less on the sandbox plan.
   Leave the default ±30% cell-count tolerance unless asked.
5. Poll `get_job` at least 5 seconds apart, and use `get_job_events` for
   progress.
6. On success, `read_artifact_summary` on the `mesh_cgns` artifact lists the real
   **zone and patch names** and the mesh quality. Use `view_mesh_section` to show
   cells.

### 5. Set up the simulation

1. Map the user's words onto the **actual** patch and zone names from step 4.
   "Inlet", "outlet", "heated base" and "coolant" must each match a real name.
   If the mapping is ambiguous, show the candidates and ask. **Never invent a
   patch or zone name, and never rename one to make validation pass.**
2. Use SI units:
   - temperature in K (25 °C = 298.15 K);
   - volumetric flow in m³/s (L/min ÷ 60000);
   - power in W;
   - pressure absolute in Pa (convert gauge explicitly);
   - viscosity in Pa·s.
3. CHT needs explicit material properties:
   - coolant: density, dynamic viscosity and molecular weight;
   - solid: conductivity, density and heat capacity.

   Air-like defaults aren't a coolant. State the values you assumed.
4. Check with `validate_simulation`. For GPU or IGBT designs from a brief with a
   CSV heat map, use `prepare_cold_plate_simulation`. It assigns every heat-map
   cell to a solid zone exactly once and conserves total watts. Don't average
   hotspots without telling the user.

### 6. Estimate again on the real mesh, then run

1. Call `estimate_cost` with `mesh_artifact_id` (uses the verified cell count),
   and confirm with the user.
2. Call `run_simulation` with a **fresh** `idempotency_key`. It returns a job ID
   immediately.
3. Follow progress with `get_job` (at least 5 seconds apart) and
   `get_job_events`. A closed chat doesn't cancel the job; use `cancel_job` only
   when the user asks.

### 7. Read results honestly

1. Call `get_job` and `read_artifact_summary` for residuals, convergence and
   quality flags, and published metrics (temperatures, pressure drop, forces, y+).
2. **Completion isn't convergence.** Report `converged` and `usable` flags
   alongside any number. Report non-converged or diverged runs as such. Metrics
   that weren't published are unknown: don't estimate them.
3. Use `view_simulation_result` for surface, section or streamline views of saved
   fields, and `assemble_simulation_viewer` to combine up to 8 views. Share the
   viewer link as given.
4. Compare against the user's limits, state your assumptions, and propose the next
   step: mesh refinement for independence, a design change or a small study. Don't
   rerun automatically.

### Studies

`plan_geometry_study` validates up to 16 variants for free. `submit_study`
submits chosen variants with one combined estimate, one budget check and a
concurrency cap. Agree the number of cases and a total budget first. Only
converged, usable results go into `compare_cold_plate_candidates`. A finite study
never yields a "global optimum".

## Errors: when to stop

| Signal | What it means | What to do |
|---|---|---|
| HTTP 401, or "sign in required" | The tool needs the user's account, or the sign-in expired | Ask the user to connect or authenticate in their client. Don't retry in a loop |
| HTTP 402, or a tool error with `insufficient_allowance` | Not enough allowance or credit | **Stop.** Show the message, the estimate, `remaining` and the `top_up_url` or `upgrade_url`. A person can also ask for a payment link (`create_topup_link`); you never handle card details |
| `key_budget_exhausted` | This connection's own budget is used up | **Stop.** The person raises the budget in Studio → Developer |
| `overage_cap_reached` | The organisation's monthly cap is reached | **Stop.** An admin decides |
| `plan_limit_exceeded` (e.g. cells) | The request exceeds the plan | Offer a smaller mesh or the plan named in the error; never shrink the job silently |
| `"retryable": false` on any error | Retrying can't help | Don't retry. Report it and propose a change |
| Validation error (422) | The request contract is wrong | Fix the named field from the schema once. If unsure, ask; don't brute-force variants |
| `submission_unknown` | The submission may or may not have reached the provider | **Never resubmit.** Report the job ID; an operator reconciles it |
| Job failed or diverged | The solver ran and failed | It's charged for the GPU time used. Report the evidence (`get_job_events`, the summary) and propose one change; don't auto-rerun |
| 429 | Rate limited | Wait, honouring `Retry-After` if present, then continue at a slower pace |

**Never retry with another API key or connection to get round a budget or a
refusal.** Never switch the physics (for example CHT to external flow, or
internal to external) to get round a failure.

## Budget etiquette

- **Estimate first.** Quote the price range and the remaining budget before every
  charged step.
- **Use the cheap steps.** Validation, schemas, inspection and viewers of existing
  results cost little or nothing. Use them to get it right before meshing.
- **Start coarse.** Use a coarse mesh to check the setup, then refine for the
  answer, with the user's agreement.
- **One job at a time** unless the user approves a study. The sandbox allows one
  concurrent job.
- **Reuse finished work** (meshes, results) when the user agrees; don't recompute
  it.

## Tool quick reference

| Step | Tools |
|---|---|
| Discover | `search_tools`, `get_tool_schema`, `get_capabilities`, `get_request_schema` |
| Price | `estimate_cost`, `create_topup_link` |
| Geometry | `list_templates`, `get_template`, `create_design_preview`, `get_design_preview`, `create_geometry`, `import_surface_attachment`, `open_surface_upload`, `view_geometry` |
| Inspect | `inspect_mesh_geometry`, `read_artifact_summary`, `get_artifact` |
| Mesh | `validate_mesh`, `create_mesh`, `view_mesh`, `view_mesh_section` |
| Simulate | `validate_simulation`, `prepare_cold_plate_simulation`, `run_simulation` |
| Monitor | `get_job`, `get_job_events`, `list_jobs`, `cancel_job`, `get_operation` |
| Results | `read_artifact_summary`, `view_simulation_result`, `assemble_simulation_viewer`, `get_artifact_download` |
| Studies | `plan_geometry_study`, `submit_study`, `plan_cold_plate`, `compare_cold_plate_candidates` |

Full reference: https://gradient-dynamics.com/docs/mcp-tools.md.
Worked example: https://gradient-dynamics.com/docs/quickstart-cold-plate.md.
