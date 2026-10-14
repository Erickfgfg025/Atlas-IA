# Arquitetura inicial

Fluxo atual: PySide6 desktop → FastAPI local → Supabase Auth para sessão → Gemini para respostas.

A migração versionada para memória persistente está no repositório, mas ainda não foi aplicada a um projeto Supabase real. A interface desktop já possui cadastro, login, chat autenticado e logout. A gravação/leitura de memórias continua pendente.

- Desktop nunca importa SDKs Gemini ou Supabase.
- Backend mantém as credenciais dos provedores.
- Login e cadastro passam pelo backend e usam Supabase Auth.
- `GET /auth/me` valida o bearer token com Supabase Auth e retorna somente o ID validado.
- `POST /chat` exige token válido antes de chamar o Gemini.
- `SUPABASE_KEY` deve ser a chave publicável/anon do projeto; nunca usar `service_role` ou chave secreta nesse fluxo.
- O access token fica apenas na memória do desktop e não há renovação automática nesta versão.
- Agente Windows permanece desativado nesta fase.
- Contratos de memória não significam persistência automática.
- Migrações habilitam RLS e isolam linhas por usuário autenticado.
- Não usar `service_role` para contornar RLS em requisições de usuário.
- Testes unitários não devem chamar serviços externos; autenticação externa é simulada por HTTPX MockTransport.

## Sequência

1. Base da interface e chat com Gemini. **Implementada; validação manual no Windows pendente.**
2. Migração Supabase para memória com RLS. **Versionada, ainda não aplicada ao projeto real.**
3. Verificação de sessão e endpoints de autenticação. **Implementados no backend.**
4. Cadastro/login/logout desktop e chat autenticado. **Implementados; validação manual no Windows pendente.**
5. Implementar armazenamento seguro/renovação de sessão no Windows.
6. Criar repositório de memória que use o token do usuário e preserve o RLS, com testes de isolamento.
7. Recuperar memórias relevantes no contexto do Gemini.
8. Só então planejar protocolo autenticado para ferramentas locais do Windows.
