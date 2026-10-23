# Atlas AI para Windows: instalação e configuração

Este guia prioriza o caminho simples: baixar o instalador, instalar e abrir o aplicativo. Não é necessário instalar Python ou compilar o projeto para usar uma versão já empacotada.

## Instalação rápida (recomendada)

### 1. Baixar o instalador

1. Abra [Windows installer no GitHub Actions](https://github.com/Erickfgfg025/Atlas-IA/actions/workflows/windows-installer.yml).
2. Clique na execução mais recente com resultado **Success**.
3. Na parte inferior da página, encontre **Artifacts** e baixe **atlas-ai-windows-installer**.
4. O download é um arquivo ZIP. Extraia-o e localize o instalador `.exe`.

Se não aparecer **Artifacts**, confirme que a execução terminou com sucesso e que o artefato ainda não expirou. Os artefatos de validação são temporários.

### 2. Instalar

1. Dê dois cliques no arquivo `Atlas-AI-Setup-...-Windows.exe`.
2. Siga o assistente de instalação.
3. Se quiser, marque a opção para criar um atalho na área de trabalho.
4. Ao terminar, deixe marcada a opção para abrir o Atlas AI ou abra-o pelo menu Iniciar.

O instalador ainda não é assinado digitalmente, então o SmartScreen pode mostrar “Editor desconhecido”. Só execute instaladores baixados do repositório oficial do Atlas AI e confirme a origem antes de permitir a execução.

### 3. Usar o aplicativo

O Atlas AI usa arquitetura cloud-first: a interface é executada no Windows e conversa com a API hospedada no Render. Em condições normais, não é necessário iniciar um servidor manualmente.

- É necessária conexão com a internet.
- A disponibilidade dos recursos depende da API e dos serviços externos configurados no backend.
- O serviço gratuito do Render pode suspender-se após inatividade. A primeira chamada depois disso pode demorar.
- Não coloque chaves Gemini, tokens Fish Audio ou credenciais Supabase dentro do aplicativo ou em arquivos públicos. As credenciais dos provedores devem ficar no backend.

## Se não funcionar

### O aplicativo não abre
- Tente iniciar pelo menu Iniciar.
- Se o Windows bloquear o arquivo, confirme que ele veio do repositório oficial.
- Baixe e extraia novamente o ZIP caso o download tenha sido interrompido.

### Abre, mas não responde
- Verifique a conexão com a internet.
- Abra [o status da API](https://atlas-ai-api-a58n.onrender.com/health). Se a API estiver acordando no plano gratuito, aguarde um pouco e tente novamente.
- Se o status não carregar ou o aplicativo continuar sem resposta, o problema pode estar na API ou em um serviço externo, não necessariamente na instalação local.

### Login ou recursos de IA falham
- A configuração de provedores é feita no backend. Não adicione chaves privadas no cliente Windows.
- O login depende de como a autenticação está configurada na versão implantada.
- Anote a mensagem de erro e a etapa em que ocorreu. Nunca compartilhe tokens ou chaves.

## Baixar o artefato atual

Para o artefato de instalador verificado em 23/10/2026, abra a [execução do Windows installer](https://github.com/Erickfgfg025/Atlas-IA/actions/runs/40035369295), desça até **Artifacts** e baixe **atlas-ai-windows-installer**. O artefato pode expirar conforme a retenção do GitHub.

## Para quem desenvolve: gerar o instalador

1. Abra [Actions → Windows installer](https://github.com/Erickfgfg025/Atlas-IA/actions/workflows/windows-installer.yml).
2. Clique em **Run workflow** e execute a branch padrão.
3. Aguarde a execução terminar com **Success**.
4. Baixe `atlas-ai-windows-installer` em **Artifacts**.

O workflow empacota o aplicativo com PyInstaller, compila o instalador com Inno Setup, verifica se o `.exe` foi produzido e calcula SHA-256 nos logs. Para publicar uma versão, envie uma tag `v*`; o workflow cria um GitHub Release com o instalador.

### Build local (Windows)

Requer Python 3.12 e Inno Setup 6. Em PowerShell, na raiz do repositório:

```powershell
python -m pip install --upgrade pip
python -m pip install . pyinstaller==6.16.0
pyinstaller --noconfirm --clean --windowed --onedir --name AtlasAI --paths src --runtime-hook build/windows/runtime_hook.py --collect-all PySide6 --collect-all shiboken6 --hidden-import atlas.desktop.memories_dialog --hidden-import atlas.desktop.voice_orb src/atlas/desktop/app.py
choco install innosetup --no-progress -y
New-Item -ItemType Directory -Force -Path dist/installer
& "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe" build/windows/atlas-ai.iss
```

## Limitações e checklist de lançamento

O sucesso do workflow confirma que o pacote foi construído, mas não substitui testes funcionais em um Windows limpo. Antes de uma distribuição mais ampla, teste instalação, abertura, login, chat, histórico, memórias, microfone, transcrição, reprodução de áudio, atualização e desinstalação.

A primeira versão não usa certificado pago de assinatura de código. Não armazene certificados, senhas de assinatura, `.env` ou credenciais privadas no repositório.
