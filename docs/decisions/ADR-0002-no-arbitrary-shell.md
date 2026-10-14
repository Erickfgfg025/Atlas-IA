# ADR-0002: não executar shell arbitrário

- Status: aceita
- Data: 2026-10-14

O modelo nunca pode devolver texto livre de shell para execução direta. Ferramentas futuras exigem schemas estáveis, validação de política, escopo, timeout e evidência de auditoria. Isso reduz riscos de prompt injection e abuso de privilégios.
