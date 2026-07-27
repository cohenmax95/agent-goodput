# Prior art and clean-room policy

Agent Goodput combines public ideas that are already well established:

- command and tool-output compression;
- cache-aware context handling;
- repository indexing and deterministic retrieval;
- model and reasoning-effort routing;
- paired agent benchmarks;
- deterministic task oracles;
- shadow, canary, promotion, and rollback control;
- append-only evidence logs;
- managed plugin installation.

The original contribution claimed by this project is the implementation and integration of those ideas into one quality-gated Codex control loop. No novelty or patent claim is made here.

## Source policy

- Study public behavior, documentation, benchmark design, interfaces, and licenses.
- Reimplement from first principles inside this repository.
- Do not copy code from projects with incompatible, noncommercial, preview, or proprietary terms.
- Preserve attribution for benchmark and design influences even when a license does not require it.
- Keep external repositories out of this repository and its history.

## Main references

- [RTK at inspected commit](https://github.com/rtk-ai/rtk/tree/1d6798de8aee0940b490719153e7554845f8f43c)
- [Headroom at inspected commit](https://github.com/headroomlabs-ai/headroom/tree/904bc675b35072dc61191963cbe485fa692927d1)
- [Repowise at inspected commit](https://github.com/repowise-dev/repowise/tree/82cd55b0fc6a4fd823c034f14045a660c8113f71)
- [CodexZero at inspected commit](https://github.com/Retro2512/CodexZero/tree/4304774a944a842703b00ada2c533c9872ddd6bb)
- [Crucible at inspected commit](https://github.com/Siddhant-Goswami/Crucible/tree/156a4b899a61d987360458ba7e8287fa1e19a61f)
- [Agent-as-a-Router at inspected commit](https://github.com/LanceZPF/agent-as-a-router/tree/e43839edb0d5d0a9feec2f7078019406ab4d64bd)
- [GitHub Next agentic-ops at inspected commit](https://github.com/githubnext/agentic-ops/tree/1115d071436896bba2115678d453c0fa545d7345)
- [ECC at inspected commit](https://github.com/affaan-m/ECC/tree/6a9f075cd97c139a5f7e84e1e3f2c9ab095adf64)
- [Token Optimizer at inspected commit](https://github.com/alexgreensh/token-optimizer/tree/bc0e2bdfb8ac5a72ce455121197ad8d33242130a)
- [Portable subagent configs at inspected commit](https://github.com/nsEytgXm/subagents_configs/tree/36bbd6a805b2122217b59db99f8868d69c766b48)
- [JFrog Boost public repository](https://github.com/jfrog/boost/tree/2ab14fd0feca752bb5e9e899ee4d687ebb222f17), used as evidence only
- [GitHub research on token efficiency in agentic workflows](https://github.blog/ai-and-ml/github-copilot/improving-token-efficiency-in-github-agentic-workflows/)
- [OpenAI Codex issue #35050 on bounded Code Mode batching](https://github.com/openai/codex/issues/35050)
- [OpenAI Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [OpenAI Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)

## License notes

At the snapshot date:

- RTK and Headroom use Apache-2.0.
- CodexZero, Crucible, Agent-as-a-Router, and ECC use MIT.
- Repowise uses AGPL-3.0.
- Token Optimizer uses PolyForm Noncommercial 1.0.0.
- JFrog Boost is All Rights Reserved under a preview agreement, with a separate license for some skills.
- agentic-ops and subagents_configs did not expose an SPDX license through the GitHub repository API.

This summary is informational and not legal advice. Check the current upstream license before reuse.
