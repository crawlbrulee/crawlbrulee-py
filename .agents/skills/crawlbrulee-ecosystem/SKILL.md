---
name: crawlbrulee-ecosystem
description: Use whenever working anywhere in this repo to recall it is one component of the crawlbrulee ecosystem. Points to the umbrella skill (one folder up) that holds the full cross-project map, shared-code locations, and conventions.
---

# crawlbrulee ecosystem (pointer)

This repository is **one component of the broader crawlbrulee ecosystem** — a family of
related projects (the core monorepo, the marketing + docs site, the language SDKs, the
MCP server, the CLI, and the public agent-skills bundle).

The authoritative `crawlbrulee-ecosystem` skill — the full map of how these projects
relate, where shared code and the OpenAPI spec live, and the cross-project conventions —
lives one level up, in the maintainer's umbrella checkout:

    ../.agents/skills/crawlbrulee-ecosystem/SKILL.md

**Read that file** whenever you need the bigger picture across projects.

If it is not present, this repository was most likely cloned on its own, outside the
umbrella — in which case there is no extra ecosystem context to load, and you can proceed
using only this repository.
