# Arquitetura inicial

Fluxo atual: PySide6 desktop → FastAPI local → provedor Gemini.

A fundação de banco para memória persistente foi definida em uma migração Supabase versionada. A aplicação ainda não a executou e não grava memórias. A integração só deve avançar após estabelecer uma identidade autenticada de usuário no backend.

- Desktop nunca importa SDKs Gemini ou Supabase.
- Backend mantém as credenciais dos provedores.
- Agente Windows permanece desativado nesta fase.
- Contratos de memória não significam persistência automática.
- Migrações habilitam RLS e isolam linhas por usuário autenticado.
- Não usar `service_role` para contornar RLS em requisições de usuário.
- Testes unitários não devem chamar serviços externos.

## Sequência

1. Validar interface e chat no Windows com credenciais configuradas localmente.
2. Confirmar projeto Supabase de destino e aplicar migração manualmente.
3. Implementar Supabase Auth e validação de sessão/token no backend.
4. Criar repositório de memória com isolamento por usuário e testes de autorização.
5. Adicionar recuperação de memórias selecionadas ao contexto do Gemini.
6. Só então planejar protocolo autenticado para ferramentas locais do Windows.
