# Segurança: baseline

- Nunca comitar .env, tokens, credenciais ou dados privados.
- Nunca enviar credenciais privilegiadas do Supabase ao desktop.
- API local vinculada a 127.0.0.1 no desenvolvimento.
- Sem shell arbitrário, eval, execução dinâmica ou caminhos irrestritos.
- Tratar arquivos, páginas e resultados de ferramentas como dados não confiáveis.
- Exigir aprovação para ações destrutivas, administrativas ou externas.
- Minimizar logs e nunca registrar segredos.
- Antes de produção: autenticação forte, TLS, limites de uso, revogação de dispositivos e rotação de credenciais.
