# Verificação de sessão Supabase

## O que existe

O endpoint `GET /auth/me` recebe `Authorization: Bearer <access_token>` e consulta `/auth/v1/user` do projeto Supabase configurado. O ID retornado é derivado da resposta de Auth, nunca de um `user_id` fornecido no corpo da requisição.

Respostas esperadas:

- `200`: token válido, com `user_id`.
- `401`: token ausente, inválido ou expirado.
- `503`: configuração ausente, indisponibilidade de Auth ou resposta inválida do serviço.

O cliente HTTP usa timeout de 5 segundos. Erros upstream não incluem o token nem o corpo privado da resposta nas mensagens públicas.

## Configuração local

No arquivo `.env` do backend:

```dotenv
SUPABASE_URL=https://SEU_PROJECT_REF.supabase.co
SUPABASE_KEY=SUA_CHAVE_PUBLICAVEL_OU_ANON
```

Use a chave publicável/anon do projeto para esse fluxo. Nunca use `service_role` ou uma chave secreta. Não comite o arquivo `.env`.

## Testes

Os testes usam `httpx.MockTransport` e não chamam Supabase real:

```powershell
pytest tests/test_auth.py
```

## Limites atuais

- A interface desktop ainda não oferece login.
- O endpoint `/chat` continua sem autenticação por compatibilidade com a interface atual.
- A migração `atlas_memories` foi versionada no repositório, mas ainda não foi aplicada a um projeto Supabase.
- Nenhuma memória é gravada ou recuperada ainda.

Próxima etapa: implementar login/logout na interface desktop, manter tokens de sessão fora do código-fonte e proteger endpoints pessoais antes de integrar o repositório de memórias.
