# Segurança: baseline

- Nunca comitar `.env`, tokens, credenciais ou dados privados.
- Nunca enviar credenciais privilegiadas do Supabase ao desktop.
- A chave `service_role` ignora RLS; não a use para substituir autenticação por usuário.
- Não confiar em `user_id` recebido do cliente; derivar a identidade de uma sessão/token validado.
- A tabela de memórias deve manter RLS habilitado e políticas limitadas a `auth.uid() = user_id`.
- API local vinculada a `127.0.0.1` no desenvolvimento.
- Sem shell arbitrário, `eval`, execução dinâmica ou caminhos irrestritos.
- Tratar arquivos, páginas, prompts e resultados de ferramentas como dados não confiáveis.
- Exigir aprovação para ações destrutivas, administrativas ou externas.
- Minimizar logs e nunca registrar segredos ou conteúdo privado desnecessário.
- Antes de produção: autenticação forte, TLS quando houver tráfego remoto, limites de uso, revogação de dispositivos e rotação de credenciais.
- Migrações devem ser versionadas e revisadas antes de aplicar ao projeto Supabase real.
