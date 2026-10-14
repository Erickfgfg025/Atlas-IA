# ADR-0001: arquitetura modular inicial

- Status: aceita para a base inicial
- Data: 2026-10-14

## Contexto
O ATLAS precisa de desktop Windows, API Python, SDK oficial Gemini, Supabase e agente local seguro futuro.

## Decisão
Usar PySide6, FastAPI, google-genai e SDK Python do Supabase. Manter a UI como cliente HTTP e separar provedores, memória e ferramentas locais. Começar com um agente e chamadas tipadas, sem framework multiagente.

## Consequências
Componentes podem ser testados separadamente. O desenvolvimento usa dois processos. Persistência Supabase e execução do agente local não estão habilitadas para produção nesta base.
