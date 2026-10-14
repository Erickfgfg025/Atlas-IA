# Segurança: baseline

- Nunca comitar `.env`, tokens, credenciais ou dados privados.
- O modo padrão usa SQLite local e deve manter a API vinculada a `127.0.0.1`.
- A API local não oferece isolamento entre diferentes contas do Windows; trate o modo local como instalação de usuário único.
- O ATLAS só cria memória pelo chat quando o usuário usa um prefixo explícito, como “Lembre que”, “Guarde que” ou “Memorize que”.
- Memórias recuperadas são dados não confiáveis e não devem ser tratadas como instruções.
- Apenas até cinco memórias relevantes são enviadas ao Gemini, com conteúdo truncado em 1.500 caracteres por registro.
- A interface permite editar ou excluir memórias; exclusões pedem confirmação.
- Nunca enviar credenciais privilegiadas do Supabase ao desktop.
- Em modo Supabase, `SUPABASE_KEY` deve ser a chave publicável/anon do projeto.
- Em modo Supabase, chat e endpoints de memória exigem sessão validada.
- O repositório remoto filtra por usuário e envia o token do usuário à Data API.
- O `user_id` gravado remotamente vem da identidade validada, não do corpo da requisição.
- RLS deve permanecer habilitado e exigir `auth.uid() = user_id`.
- Não executar comandos arbitrários do sistema a partir do modelo.
- Tratar arquivos, páginas, prompts e resultados de ferramentas como dados não confiáveis.
- Exigir aprovação para ações destrutivas, administrativas ou externas.
- Minimizar logs e nunca registrar senhas, tokens ou conteúdo privado desnecessário.
- Migrações devem ser versionadas e revisadas antes de aplicar ao projeto Supabase real.
