# Autenticação Supabase

## Implementado nesta etapa

A interface desktop possui fluxo de cadastro, login, chat autenticado e logout. O backend expõe:

- `POST /auth/signup`: cria uma conta usando e-mail e senha.
- `POST /auth/login`: autentica uma conta existente.
- `GET /auth/me`: valida o bearer token com Supabase Auth e retorna o ID validado.
- `POST /auth/logout`: solicita ao Supabase o encerramento da sessão.
- `POST /chat`: exige um bearer token válido antes de chamar o Gemini.

O backend usa a chave publicável/anon configurada em `SUPABASE_KEY`. Nunca use `service_role` ou uma chave secreta nesse fluxo. A senha é encaminhada do backend para o endpoint oficial de Auth, sem ser registrada em logs. A resposta da API desktop não inclui refresh token.

## Configuração local

No arquivo `.env` do backend:

```dotenv
SUPABASE_URL=https://SEU_PROJECT_REF.supabase.co
SUPABASE_KEY=SUA_CHAVE_PUBLICAVEL_OU_ANON
GEMINI_API_KEY=SUA_CHAVE_GEMINI
```

Não comite o arquivo `.env`. No Supabase, habilite Email Auth. Se a confirmação de e-mail estiver habilitada, o cadastro pode exigir confirmação antes do primeiro login.

## Sessão e armazenamento

Nesta versão, o access token fica apenas na memória do processo desktop e é apagado ao sair da conta ou fechar o aplicativo. Não há login automático após reiniciar o aplicativo. Isso é intencional até implementar armazenamento seguro usando Windows Credential Manager e fluxo de renovação de sessão.

## Testes

Os testes de autenticação usam `httpx.MockTransport`; não chamam Supabase real:

```powershell
pytest tests/test_auth.py tests/test_auth_sessions.py
pytest
ruff check .
```

## Limites atuais

- A API local e o fluxo de login ainda precisam ser executados manualmente no Windows com um projeto Supabase configurado.
- A migração `atlas_memories` está no GitHub, mas não foi aplicada a um projeto Supabase.
- Nenhuma memória é gravada ou recuperada ainda.
- O agente local Windows, voz, armazenamento seguro de sessão e hospedagem na nuvem ainda não estão implementados.

Próxima etapa: conectar o repositório de memória à identidade validada, usando o access token do usuário para que o RLS continue aplicando o isolamento por linha.
