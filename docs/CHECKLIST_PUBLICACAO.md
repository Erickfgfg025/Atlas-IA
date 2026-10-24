# Checklist de publicação do Atlas AI para clientes

Este checklist é o portão de qualidade antes de disponibilizar o instalador publicamente. CI verde, isoladamente, não comprova que a instalação e o fluxo completo funcionam em uma máquina de cliente.

## 1. Infraestrutura e configuração

- [ ] Confirmar que o serviço Render está `live` e que `/health` responde com `status: ok`.
- [ ] Confirmar no ambiente privado do Render: `ATLAS_ENVIRONMENT=production`, `ATLAS_MEMORY_BACKEND=supabase`, `SUPABASE_URL`, `SUPABASE_KEY` publicável e `GEMINI_API_KEY`.
- [ ] Confirmar que o backend de produção não usa `ATLAS_DESKTOP_NO_LOGIN=true`, `ATLAS_OWNER_USER_ID` nem `SUPABASE_SERVICE_ROLE_KEY` para o fluxo de clientes.
- [ ] Confirmar configuração de confirmação de e-mail e recuperação de senha no Supabase Auth.
- [ ] Nunca copiar segredos do backend para o cliente, para o GitHub ou para os documentos.

## 2. Segurança e isolamento de dados

- [ ] Criar duas contas de teste independentes.
- [ ] Na conta A, criar conversas e memórias de teste.
- [ ] Entrar na conta B e confirmar que nenhum dado da conta A aparece ou pode ser acessado alterando IDs de requisição.
- [ ] Testar sem token, com token inválido e com token expirado: endpoints privados devem negar acesso.
- [ ] Confirmar políticas RLS nas tabelas de conversas, mensagens e memórias.
- [ ] Testar logout e verificar que a sessão local é apagada.
- [ ] Testar persistência da sessão no Windows e o comportamento quando o cofre de credenciais não está disponível.

## 3. Instalador Windows

- [ ] Executar GitHub Actions → **Windows installer** → **Run workflow**.
- [ ] Confirmar que o job terminou com sucesso e produziu `Atlas-AI-Setup-*-Windows.exe`.
- [ ] Baixar o artefato e calcular/guardar o SHA-256.
- [ ] Instalar em uma VM ou PC Windows 10/11 limpo, sem Python, Git ou ferramentas de desenvolvimento.
- [ ] Abrir o aplicativo, criar conta, confirmar e-mail quando exigido, entrar e enviar uma mensagem.
- [ ] Fechar e reabrir o app; verificar sessão e histórico.
- [ ] Testar logout, novo login, atualização por cima da versão anterior e desinstalação.
- [ ] Confirmar que o app não depende de arquivos presentes apenas na máquina de desenvolvimento.
- [ ] Registrar a versão do instalador, o SHA-256, o commit de origem e o resultado dos testes manuais.

## 4. Publicar uma versão

1. Só depois de todos os itens críticos acima estarem marcados, atualizar a versão em `pyproject.toml` e `build/windows/atlas-ai.iss`.
2. Criar e enviar uma tag de versão no formato `vX.Y.Z`.
3. Aguardar o workflow de Windows Installer.
4. Confirmar que a GitHub Release contém o instalador correspondente à tag.
5. Publicar a página de download com versão, SHA-256, requisitos do Windows, política de privacidade, canal de suporte e instruções de instalação.

## 5. Limitações conhecidas

- O serviço Render gratuito pode suspender-se por inatividade, causando demora na primeira requisição.
- O instalador não está assinado digitalmente; o Windows pode exibir alertas de reputação/SmartScreen.
- A renovação de sessão por refresh token precisa ser validada/implementada antes de prometer sessões persistentes sem novo login.
- Não anunciar como pronto para clientes até concluir testes reais de isolamento, login e instalação limpa.
