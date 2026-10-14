# Arquitetura inicial

Fluxo atual: PySide6 desktop → FastAPI local → provedor Gemini.

A migração versionada para memória persistente foi incorporada ao repositório, mas ainda não foi aplicada a um projeto Supabase real. A API agora possui uma fundação de verificação de sessão Supabase em `GET /auth/me`. O login da interface desktop e a gravação/leitura de memórias continuam pendentes.

- Desktop nunca importa SDKs Gemini ou Supabase.
- Backend mantém as credenciais dos provedores.
- `GET /auth/me` valida o bearer token com Supabase Auth e retorna somente o ID validado.
- `SUPABASE_KEY` deve ser a chave publicável/anon do projeto; nunca usar `service_role` ou chave secreta nesse fluxo.
- O endpoint `/chat` ainda não exige autenticação porque a interface desktop não implementa login. Não habilitar persistência nem ações sensíveis antes de fechar essa lacuna.
- Agente Windows permanece desativado nesta fase.
- Contratos de memória não significam persistência automática.
- Migrações habilitam RLS e isolam linhas por usuário autenticado.
- Não usar `service_role` para contornar RLS em requisições de usuário.
- Testes unitários não devem chamar serviços externos; autenticação externa é simulada por HTTPX MockTransport.

## Sequência

1. Validar interface e chat no Windows com credenciais configuradas localmente.
2. Confirmar projeto Supabase de destino e aplicar migração manualmente.
3. Implementar e testar verificação de sessão Supabase no backend. **Fundação adicionada** via `GET /auth/me`.
4. Criar fluxo de login na interface desktop e exigir identidade autenticada nos endpoints que acessam dados pessoais.
5. Criar repositório de memória com isolamento por usuário e testes de autorização.
6. Adicionar recuperação de memórias selecionadas ao contexto do Gemini.
7. Só então planejar protocolo autenticado para ferramentas locais do Windows.
