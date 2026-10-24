# Autenticação Supabase

## Fluxo implementado

O cliente desktop autentica pelo backend hospedado. O backend valida a sessão com Supabase Auth e usa o token do usuário nas operações de dados; não deve expor a chave `service_role` ao aplicativo desktop.

Endpoints principais:

- `POST /auth/signup`: cadastro com e-mail e senha.
- `POST /auth/login`: login e retorno do access token e duração da sessão.
- `GET /auth/me`: valida o bearer token e retorna a identidade confirmada pelo Supabase.
- `POST /auth/logout`: solicita encerramento da sessão.
- `POST /chat`: exige autenticação no modo de nuvem.
- As operações de conversas e memórias também devem usar a identidade validada e as políticas RLS do Supabase.

## Configuração do backend

Configurar no ambiente privado do serviço:

```dotenv
ATLAS_ENVIRONMENT=production
ATLAS_MEMORY_BACKEND=supabase
SUPABASE_URL=https://SEU_PROJECT_REF.supabase.co
SUPABASE_KEY=SUA_CHAVE_PUBLICAVEL
GEMINI_API_KEY=SUA_CHAVE_GEMINI
```

Nunca definir `SUPABASE_KEY` com uma chave `service_role` ou secret. Não colocar chaves privadas no cliente, no repositório ou em documentação. Não habilitar `ATLAS_DESKTOP_NO_LOGIN=true` no serviço público de clientes.

No Supabase Auth, configurar confirmação de e-mail e recuperação de senha de acordo com a política do produto. Se a confirmação estiver habilitada, um cadastro pode exigir a confirmação antes do primeiro login.

## Sessão no Windows

O cliente usa o cofre de credenciais do sistema por meio da biblioteca `keyring` para guardar o token da sessão. Se o cofre não estiver disponível, o comportamento seguro é exigir login novamente em vez de gravar o token em texto simples.

A renovação automática por refresh token ainda precisa ser validada/implementada. Por isso, uma sessão pode expirar e exigir novo login. O logout deve limpar a credencial local e encerrar a sessão no provedor.

## Verificações automatizadas

Os testes unitários de autenticação usam transporte simulado e não comprovam a conectividade com o projeto Supabase real:

```powershell
pytest tests/test_auth.py tests/test_auth_sessions.py
pytest
ruff check .
```

O CI do repositório já executou os testes Python com sucesso em Python 3.11 e 3.12. Isso não substitui os testes manuais abaixo.

## Testes obrigatórios antes de disponibilizar a clientes

- [ ] Confirmar cadastro, confirmação de e-mail, login e logout em um projeto Supabase real.
- [ ] Criar duas contas de teste e comprovar que conversas e memórias não atravessam contas.
- [ ] Confirmar RLS habilitado em todas as tabelas de dados do cliente e políticas baseadas em `auth.uid() = user_id`.
- [ ] Confirmar que token ausente, inválido ou expirado é rejeitado em todos os endpoints privados.
- [ ] Verificar persistência no Windows Credential Manager e comportamento quando `keyring` não está disponível.
- [ ] Testar expiração da sessão e exigir novo login de forma clara se não houver renovação.
- [ ] Instalar o pacote em uma máquina Windows 10/11 limpa e testar login, chat, histórico, reinicialização, logout e desinstalação.

## Limites conhecidos

- O plano gratuito do Render pode suspender o serviço por inatividade, aumentando o tempo da primeira requisição.
- O instalador atual não está assinado digitalmente e pode exibir avisos do Windows SmartScreen.
- A compilação bem-sucedida do instalador não é prova de funcionamento em uma máquina Windows limpa.
- Não anunciar o aplicativo como pronto para clientes até que os testes reais de autenticação, isolamento e instalação estejam concluídos.
