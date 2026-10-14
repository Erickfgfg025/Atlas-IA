# Arquitetura inicial

Fluxo atual: PySide6 desktop → FastAPI local → Supabase Auth para sessão → Gemini para respostas. A API possui endpoints de memória que usam o token autenticado do usuário e dependem de RLS.

A migração versionada está no repositório, mas ainda não foi aplicada a um projeto Supabase real. Leitura/criação/exclusão estão implementadas; persistência real depende da migração e validação no projeto correto.

- Desktop nunca importa SDKs Gemini ou Supabase.
- Backend mantém as credenciais dos provedores.
- Cadastro/login/logout passam pelo backend e usam Supabase Auth.
- `GET /auth/me` valida o bearer token.
- `POST /chat` exige token válido antes de chamar o Gemini.
- `GET /memories`, `POST /memories` e `DELETE /memories/{id}` exigem sessão validada.
- O repositório usa chave publicável/anon e access token do usuário para preservar RLS.
- O ID do usuário vem da identidade validada, nunca do corpo.
- Nunca usar `service_role` para contornar RLS.
- O access token fica apenas na memória do desktop; não há renovação automática.
- Agente Windows permanece desativado.
- A recuperação de memórias no contexto do Gemini ainda não está ligada.
- Testes externos usam HTTPX MockTransport.

## Sequência

1. Base de interface e chat. **Implementada; validação manual no Windows pendente.**
2. Migração de memória com RLS. **Versionada, não aplicada ao projeto real.**
3. Cadastro/login/logout e chat autenticado. **Implementados; validação manual pendente.**
4. Endpoints de memória com identidade validada. **Implementados; CI e testes simulados pendentes nesta PR.**
5. Aplicar migração e testar isolamento com duas contas.
6. Implementar armazenamento seguro/renovação de sessão no Windows.
7. Recuperar memórias relevantes no contexto do Gemini.
8. Planejar protocolo autenticado para ferramentas locais do Windows.