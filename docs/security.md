# Segurança: baseline

- Nunca comitar `.env`, tokens, credenciais ou dados privados.
- Nunca enviar credenciais privilegiadas do Supabase ao desktop.
- A chave `service_role` ignora RLS; não a use para substituir autenticação por usuário.
- `SUPABASE_KEY` no fluxo de autenticação deve ser a chave publicável/anon do projeto.
- O endpoint `GET /auth/me` encaminha o bearer token para Supabase Auth validar a sessão; o backend não confia em IDs enviados pelo cliente nem decodifica JWT sem verificar assinatura.
- O endpoint `/chat` exige token válido antes de chamar o provedor Gemini.
- O access token fica somente em memória nesta versão; refresh tokens não são devolvidos ao desktop nem armazenados.
- A tabela de memórias deve manter RLS habilitado e políticas limitadas a `auth.uid() = user_id`.
- A API deve continuar vinculada a `127.0.0.1` no desenvolvimento.
- Sem shell arbitrário, `eval`, execução dinâmica ou caminhos irrestritos.
- Tratar arquivos, páginas, prompts e resultados de ferramentas como dados não confiáveis.
- Exigir aprovação para ações destrutivas, administrativas ou externas.
- Minimizar logs e nunca registrar senhas, tokens ou conteúdo privado desnecessário.
- Antes de produção: TLS, limites de uso, revogação de dispositivos, armazenamento seguro de sessão e rotação de credenciais.
- Migrações devem ser versionadas e revisadas antes de aplicar ao projeto Supabase real.
