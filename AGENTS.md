# ATLAS AI coding rules

- Read ATLAS_AI_CONTEXTO_MESTRE.md and docs before architectural changes.
- Never commit .env, tokens, API keys, passwords, personal data or dumps.
- Gemini proposes structured tool calls; deterministic executors validate scope and risk.
- Never execute arbitrary model output in a shell.
- Destructive, administrative or external-impact actions require explicit approval.
- Keep desktop, API, providers, memory and local tools separated.
- Prefer small, reversible, typed changes covered by tests.
- Do not claim tests, deployments or repository changes without evidence.
