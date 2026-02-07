# GxP.MD

**GxP compliance instructions for AI coding agents.**

GxP.MD is a markdown-based compliance instruction standard for AI-assisted software development in regulated pharmaceutical and life sciences industries. Drop a `GxP.MD` file in your project root — your AI agent handles the rest.

## Repository Structure

```
gxp-md/
├── spec/          # The GxP.MD specification (source of truth)
│   ├── GxP.MD     # Canonical specification document
│   ├── schema/    # JSON Schema for frontmatter validation
│   └── profiles/  # Built-in regulatory profiles
├── templates/     # Starter templates for adoption
└── site/          # Documentation microsite (gxp.md)
```

## Quick Start

1. Copy `templates/GxP.MD.starter` to your project root as `GxP.MD`
2. Choose a regulatory profile from `spec/profiles/`
3. Initialize your `.gxp/` directory using the templates
4. Start developing — your AI agent reads the GxP.MD file automatically

## Specification

Read the full specification at [gxp.md](https://gxp.md) or in `spec/GxP.MD`.

## Related Projects

- **ROSIE RFC-001** — Artifact/evidence standard that GxP.MD wraps
- **Nexus** — GxP validation platform that consumes GxP.MD contracts

## License

Copyright 2026 PharmaLedger Association. All rights reserved.
