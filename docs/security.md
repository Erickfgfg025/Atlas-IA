# Segurança: baseline

- Nunca comitar `.env`, tokens, credenciais ou dados privados.
- O modo padrão usa SQLite local e deve manter a API vinculada a `127.0.0.1`.
- A API local não oferece isolamento entre diferentes contas do Windows; trate o modo local como uma instalação de usuário único e proteja a sessão do sistema operacional.
- Nunca enviar credenciais privilegiadas do Supabase ao desktop.
- A chave `service_role` ignora RLS; não a use para substituir autenticação por usuário.
- Em modo Supabase, `SUPABASE_KEY` deve ser a chave publicável/anon do projeto.
- `/auth/me` valida o bearer token via Supabase Auth; não confiar em IDs enviados pelo cliente nem decodificar JWT sem verificar assinatura.
- Em modo Supabase, chat e endpoints de memória exigem sessão validada.
- O repositório de memória remoto envia o token do usuário à Data API; não usa credenciais privilegiadas.
- O `user_id` gravado remotamente vem da identidade validada, não do corpo da requisição.
- Consultas remotas filtram por usuário, mas RLS deve permanecer habilitado e exigir `auth.uid() = user_id`.
- O access token fica somente em memória nesta versão; refresh tokens não são devolvidos ao desktop nem armazenados.
- Sem shell arbitrário, `eval`, execução dinâmica ou caminhos irrestritos.
- Tratar arquivos, páginas, prompts e resultados de ferramentas como dados não confiáveis.
- Exigir aprovação para ações destrutivas, administrativas ou externas.
- Minimizar logs e nunca registrar senhas, tokens ou conteúdo privado desnecessário.
- Antes de produção: TLS, limites de uso, revogação de dispositivos, armazenamento seguro de sessão e rotação de credenciais.
- Migrações devem ser versionadas e revisadas antes de aplicar ao projeto Supabase real.
