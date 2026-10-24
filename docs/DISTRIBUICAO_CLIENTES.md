# Distribuição do Atlas AI para clientes

## Experiência do cliente

1. Baixar um único instalador para Windows.
2. Instalar sem Python, Git, terminal, arquivo `.env` ou chaves técnicas.
3. Abrir o aplicativo pelo menu Iniciar ou atalho.
4. Entrar ou criar uma conta própria.
5. Usar o Atlas AI com memória e histórico sincronizados na nuvem.

## Arquitetura

- Cliente nativo Windows: PySide6 empacotado com PyInstaller.
- Instalador: Inno Setup.
- API hospedada: serviço `atlas-ai-api` no Render.
- Identidade: Supabase Auth.
- Memória e conversas: Supabase, com políticas RLS por usuário.
- Chaves de IA: somente no ambiente privado do backend.

## Segurança

- Nunca colocar `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY` ou chaves privadas no executável, instalador, repositório ou variáveis do cliente.
- O cliente não deve usar o modo pessoal sem login. Esse modo serve apenas ao backend local privado.
- A sessão de desktop é armazenada pelo pacote `keyring` no cofre de credenciais do sistema operacional quando o backend de keyring do Windows está disponível. Se o armazenamento seguro falhar, o aplicativo não grava o token em texto simples; o usuário precisará entrar novamente após reiniciar.
- Renovação automática de sessão com refresh token ainda precisa ser implementada. Um access token expirado pode exigir novo login.
- O instalador não está assinado; para distribuição comercial ampla, adquirir certificado de assinatura de código e assinar o instalador/executável.

## Build

O workflow `.github/workflows/windows-installer.yml` compila o executável num runner Windows, cria o instalador e publica um artefato. Também publica uma GitHub Release quando o build é acionado por uma tag `v*`.

- Build manual: GitHub → Actions → Windows installer → Run workflow.
- Build automático: push para `main` ou tag no padrão `v*`.
- O workflow atual envia o instalador como artefato e cria uma Release para tags.

## Configuração obrigatória do backend

O serviço Render precisa de `ATLAS_ENVIRONMENT=production`, `ATLAS_MEMORY_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_KEY` publicável e `GEMINI_API_KEY`. Configure o cadastro por e-mail e as regras de confirmação no Supabase Auth.

### Confirmação de e-mail e redirecionamento

- No Render, configure `ATLAS_AUTH_EMAIL_REDIRECT_URL` com uma URL HTTPS pública que pertença ao fluxo de confirmação realmente implementado. Não use `localhost` como destino para usuários do aplicativo Windows.
- No Supabase Dashboard → Authentication → URL Configuration, adicione essa mesma URL em `Redirect URLs`. O valor `Site URL` também deve apontar para um destino público válido, não para `localhost` em produção.
- Se ainda não existir uma página pública de callback, use temporariamente uma página HTTPS pública adequada como destino e instrua o usuário a voltar ao aplicativo e entrar novamente após confirmar o e-mail. A URL de callback, sozinha, não cria uma sessão automática no aplicativo Windows.
- Após alterar variáveis do Render, faça um redeploy e teste cadastro, confirmação e login com uma conta de teste.

Não configure `ATLAS_DESKTOP_NO_LOGIN=true`, `ATLAS_OWNER_USER_ID` nem `SUPABASE_SERVICE_ROLE_KEY` para o fluxo de clientes.

## Limites antes de anunciar o produto

- Confirmar que as variáveis de produção do Render estão preenchidas e que `/health` responde.
- Testar login, cadastro, acesso isolado por usuário, memória, histórico e logout no backend real.
- Executar o workflow e instalar o resultado numa máquina Windows limpa.
- O plano gratuito do Render pode suspender o serviço por inatividade e atrasar a primeira requisição.
- Não declarar o instalador pronto para clientes antes dessas verificações.
