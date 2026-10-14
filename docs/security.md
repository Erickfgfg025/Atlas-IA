# Segurança: baseline

- Nunca comitar `.env`, tokens, credenciais ou dados privados.
- Nunca enviar credenciais privilegiadas do Supabase ao desktop.
- A chave `service_role` ignora RLS; não a use para substituir autenticação por usuário.
- `SUPABASE_KEY` deve ser a chave publicável/anon do projeto.
- `GET /auth/me` valida o bearer token via Supabase Auth; não confiar em IDs enviados pelo cliente nem decodificar JWT sem verificar assinatura.
- `/chat` e os endpoints de memória exigem sessão validada.
- O repositório de memória envia o token do usuário à Data API; não usa credenciais privilegiadas.
- O `user_id` gravado vem da identidade validada, não do corpo da requisição.
- Consultas filtram por usuário, mas RLS deve permanecer habilitado e exigir `auth.uid() = user_id`.
- O access token fica somente em memória nesta versão; refresh tokens não são devolvidos ao desktop nem armazenados.
- A API deve continuar vinculada a `127.0.0.1` no desenvolvimento.
- Sem shell arbitrário, `eval`, execução dinâmica ou caminhos irrestritos.
- Tratar arquivos, páginas, prompts e resultados de ferramentas como dados não confiáveis.
- Exigir aprovação para ações destrutivas, administrativas ou externas.
- Minimizar logs e nunca registrar senhas, tokens ou conteúdo privado desnecessário.
- Antes de produção: TLS, limites de uso, revogação de dispositivos, armazenamento seguro de sessão e rotação de credenciais.
- Migrações devem ser versionadas e revisadas antes de aplicar ao projeto Supabase real.