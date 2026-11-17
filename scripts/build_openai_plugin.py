#!/usr/bin/env python3
"""Check plugin.json and mcp.json against OpenAI's plugin-directory rules and build the upload ZIP.

    python3 scripts/build_openai_plugin.py            # refuses while anything is missing
    python3 scripts/build_openai_plugin.py --draft    # builds anyway, to try the dashboard's checks

The ZIP is the portable Agent Plugins layout: plugin.json and mcp.json at the root, the skills and
the referenced assets. The Claude Code files (.claude-plugin/, .mcp.json) are left out. Rules come
from https://developers.openai.com/apps-sdk/deploy/submission (checked 2026-10-31).
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
MCP_SCHEMA = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
ROOT_KEYS = {"$schema", "name", "version", "description", "author", "homepage", "repository", "license",
             "keywords", "extensions"}
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LISTING_URLS = ("websiteURL", "supportURL", "privacyPolicyURL", "termsOfServiceURL")
# OpenAI's plugin guidelines: no selling of credits or other digital goods, and no pricing, free-trial or
# promotion wording in the listing. The API's /mcp/openai route leaves out the top-up tool and billing links.
LISTING_MCP_URL = "https://api.gradient-dynamics.com/mcp/openai"
SALES_WORDING = re.compile(r"\b(free|trial|price|prices|pricing|discount|cheap|credits?|top[- ]?up|subscribe|"
                           r"subscription|buy|purchase|checkout)\b|[£$€]", re.IGNORECASE)
MAX_IMAGE_BYTES = 5 * 1024 * 1024
FIXED_TIME = (2026, 1, 1, 0, 0, 0)  # identical inputs give an identical ZIP


class Checks:
    def __init__(self):
        self.problems: list[str] = []

    def require(self, ok: bool, problem: str) -> bool:
        if not ok:
            self.problems.append(problem)
        return ok

    def text(self, value, field: str, limit: int) -> None:
        if self.require(isinstance(value, str) and value.strip() != "", f"{field} is missing"):
            self.require(len(value) <= limit, f"{field} is {len(value)} characters (limit {limit})")
            self.require("TODO" not in value, f"{field} is still a placeholder: {value!r}")

    def url(self, value, field: str) -> None:
        self.text(value, field, 1024)
        if isinstance(value, str) and "TODO" not in value:
            self.require(value.startswith("https://"), f"{field} must be an https:// URL")

    def asset(self, value, field: str) -> Path | None:
        if not self.require(isinstance(value, str) and value.startswith("./"), f"{field} must be a ./ path"):
            return None
        path = ROOT / value[2:]
        if not self.require(path.is_file(), f"{field} {value} does not exist"):
            return None
        return path

    def icon(self, value, field: str) -> Path | None:
        path = self.asset(value, field)
        if path is None:
            return None
        self.require(path.stat().st_size <= MAX_IMAGE_BYTES, f"{field} is larger than 5 MiB")
        data = path.read_bytes()[:24]
        if self.require(data[:8] == b"\x89PNG\r\n\x1a\n", f"{field} must be a PNG (only PNG sizes are checked here)"):
            width, height = struct.unpack(">II", data[16:24])
            self.require(width == height, f"{field} must be square, not {width}x{height}")
            self.require(48 <= width <= 4096, f"{field} must be 48 to 4096 px, not {width}")
        return path


def check(plugin: dict, mcp: dict) -> tuple[list[str], set[Path]]:
    c = Checks()
    files = {ROOT / "plugin.json", ROOT / "mcp.json"}

    c.require(plugin.get("$schema") == PLUGIN_SCHEMA, f"plugin.json $schema must be {PLUGIN_SCHEMA}")
    c.require(set(plugin) <= ROOT_KEYS, f"plugin.json has unknown keys: {sorted(set(plugin) - ROOT_KEYS)}")
    name = plugin.get("name", "")
    c.require(isinstance(name, str) and len(name) <= 64 and bool(NAME.match(name)),
              "name must be lowercase letters, numbers and single hyphens, at most 64 characters")
    c.require(bool(SEMVER.match(str(plugin.get("version", "")))), "version must be semver, e.g. 0.1.0")
    c.text(plugin.get("description"), "description", 4000)
    c.require(bool((plugin.get("author") or {}).get("name")), "author.name is missing")

    openai = (plugin.get("extensions") or {}).get("com.openai") or {}
    ui = openai.get("interface") or {}
    c.text(ui.get("displayName"), "interface.displayName", 30)
    c.text(ui.get("shortDescription"), "interface.shortDescription", 30)
    c.text(ui.get("longDescription"), "interface.longDescription", 4000)
    c.text(ui.get("developerName"), "interface.developerName", 80)
    c.text(ui.get("category"), "interface.category", 120)
    capabilities = ui.get("capabilities", [])
    c.require(isinstance(capabilities, list) and len(capabilities) <= 20
              and all(isinstance(item, str) and len(item) <= 120 for item in capabilities),
              "interface.capabilities must be at most 20 strings of at most 120 characters")
    for field in LISTING_URLS:
        c.url(ui.get(field), f"interface.{field}")
    prompts = ui.get("defaultPrompt", [])
    prompts = [prompts] if isinstance(prompts, str) else prompts
    c.require(len(prompts) <= 3 and len(set(prompts)) == len(prompts), "defaultPrompt: at most 3 unique prompts")
    for prompt in prompts:
        c.require(len(prompt) <= 128, f"defaultPrompt over 128 characters: {prompt!r}")
        c.require("@" not in prompt, f"defaultPrompt must not @mention apps: {prompt!r}")
    for field, required in (("logo", True), ("composerIcon", True), ("logoDark", False), ("composerIconDark", False)):
        if required or field in ui:
            files.add(c.icon(ui.get(field), f"interface.{field}"))
    for shot in ui.get("screenshots", []):
        files.add(c.asset(shot, "interface.screenshots"))
    if "onboardingSkill" in openai:
        files.add(c.asset(openai["onboardingSkill"], "onboardingSkill"))

    review = openai.get("review") or {}
    cases = review.get("test_cases") or {}
    positive, negative = cases.get("positive", []), cases.get("negative", [])
    c.require(len(positive) == 5, f"review needs exactly 5 positive test cases, not {len(positive)}")
    c.require(len(negative) == 3, f"review needs exactly 3 negative test cases, not {len(negative)}")
    for kind, group, needed in (("positive", positive, ("description", "prompt", "tools_triggered", "expected_behavior")),
                                ("negative", negative, ("description", "prompt"))):
        for number, case in enumerate(group, 1):
            for key in needed:
                c.require(bool(case.get(key)), f"{kind} test case {number} is missing {key}")
    c.url(review.get("demo_recording_url"), "review.demo_recording_url")
    c.require(review.get("commerce") is not True, "review.commerce must be false: the listing sells nothing")
    for field in ("shortDescription", "longDescription"):
        found = sorted({match.group(0).lower() for match in SALES_WORDING.finditer(str(ui.get(field, "")))})
        c.require(not found, f"interface.{field} has pricing or sales wording: {found}")
    for prompt in prompts:
        c.require(not SALES_WORDING.search(prompt), f"defaultPrompt has pricing or sales wording: {prompt!r}")
    for forbidden in ("test_credentials", "reviewer_instructions"):
        c.require(forbidden not in review and forbidden not in openai,
                  f"{forbidden} must be entered in the dashboard, not the ZIP")

    c.require(mcp.get("$schema") == MCP_SCHEMA, f"mcp.json $schema must be {MCP_SCHEMA}")
    servers = mcp.get("mcpServers") or {}
    c.require(len(servers) == 1, f"mcp.json must declare exactly one server, not {len(servers)}")
    for server_name, server in servers.items():
        c.require(server.get("type") == "streamable-http", f"server {server_name} must be type streamable-http")
        c.require(str(server.get("url", "")).startswith("https://"), f"server {server_name} needs an https:// url")
        c.require(server.get("url") == LISTING_MCP_URL,
                  f"server {server_name} must use {LISTING_MCP_URL}, the route without purchase links")
        c.require(not server.get("headers"), f"server {server_name} must not send headers in a public submission")
        c.require("clientSecret" not in json.dumps(server), f"server {server_name} must not contain a clientSecret")

    for forbidden in (".app.json", "hooks", "hooks.json"):
        c.require(not (ROOT / forbidden).exists(), f"{forbidden} can't be submitted; remove it from the package")
    files.update(path for path in (ROOT / "skills").rglob("*") if path.is_file())
    return c.problems, {path for path in files if path is not None}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--draft", action="store_true", help="build even if checks fail (file name ends -draft)")
    args = parser.parse_args()

    plugin = json.loads((ROOT / "plugin.json").read_text())
    mcp = json.loads((ROOT / "mcp.json").read_text())
    problems, files = check(plugin, mcp)
    for problem in problems:
        print(f"- {problem}", file=sys.stderr)
    if problems and not args.draft:
        print(f"{len(problems)} problem(s); fix them, or pass --draft to build anyway.", file=sys.stderr)
        return 1

    out = ROOT / "dist" / f"{plugin['name']}-openai-{plugin['version']}{'-draft' if problems else ''}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            info = zipfile.ZipInfo(path.relative_to(ROOT).as_posix(), FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    print(f"{out.relative_to(ROOT)}: {len(files)} files" + (f", {len(problems)} problem(s) left" if problems else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
