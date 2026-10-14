# Arquitetura inicial

Fluxo padrão: PySide6 desktop → FastAPI local → Gemini para respostas; a memória é persistida em SQLite no computador. A API oferece uma opção de armazenamento Supabase para uma futura fase em nuvem.

- Desktop não importa SDKs Gemini ou Supabase.
- O backend mantém as credenciais do provedor Gemini.
- `ATLAS_MEMORY_BACKEND=local` é o padrão e dispensa conta remota.
- `ATLAS_LOCAL_DB_PATH` pode apontar para um arquivo SQLite específico; vazio usa o diretório de dados do usuário.
- `GET /memories`, `POST /memories` e `DELETE /memories/{id}` usam o adaptador selecionado.
- Em modo Supabase, a API exige sessão validada e o repositório usa a chave publicável/anon mais o token do usuário para preservar RLS.
- O ID do usuário remoto vem da identidade validada, nunca do corpo da requisição.
- Nunca usar `service_role` para contornar RLS.
- O access token fica apenas na memória do desktop; não há renovação automática.
- Agente Windows permanece desativado.
- A recuperação de memórias no contexto do Gemini ainda não está ligada.
- Testes externos usam HTTPX MockTransport; os testes SQLite usam banco temporário.

## Sequência

1. Base de interface e chat. **Implementada; validação manual no Windows pendente.**
2. Adaptador de memória local SQLite e modo local-first. **Implementados nesta alteração; CI ainda precisa confirmar.**
3. Endpoints de memória usando o adaptador selecionado. **Implementados; integração Supabase real pendente.**
4. Recuperar memórias relevantes no contexto do Gemini.
5. Validar manualmente no Windows e confirmar persistência após reinício.
6. Planejar migração/importação de memórias para Supabase quando houver projeto disponível.
7. Implementar armazenamento seguro/renovação de sessão no Windows.
8. Planejar protocolo autenticado para ferramentas locais do Windows.
