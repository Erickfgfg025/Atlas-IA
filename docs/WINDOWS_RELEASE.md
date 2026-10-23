# Entrega do Atlas AI para Windows

## Decisões da primeira versão

- Formato: instalador `.exe` criado com Inno Setup.
- Aplicativo: PySide6 empacotado pelo PyInstaller em modo `onedir`; o instalador reúne o executável e seus arquivos.
- Arquitetura: cloud-first. O cliente empacotado usa a API do Render configurada em `build/windows/runtime_hook.py`. O desenvolvimento local continua usando `http://127.0.0.1:8000`.
- Assinatura: não assinada nesta etapa. O Windows pode exibir o aviso do SmartScreen ou “Editor desconhecido”. Isso não significa, por si só, que o arquivo contenha malware.
- Segredos: nenhuma chave Gemini, Fish Audio, Supabase service role ou outra credencial privada deve ser incluída no cliente. As credenciais dos provedores ficam no backend.

## Gerar o instalador no GitHub Actions

1. Abra **Actions → Windows installer** no repositório.
2. Selecione **Run workflow** para gerar um artefato de validação a partir da branch padrão.
3. Aguarde o job terminar e baixe o artefato `atlas-ai-windows-installer`.
4. Para publicar uma versão, crie e envie uma tag de versão, por exemplo `v0.1.0`. A execução da tag anexa o instalador a um GitHub Release.

O workflow instala as dependências no Windows, gera a pasta `dist/AtlasAI`, compila o instalador com Inno Setup e verifica que um arquivo `.exe` foi produzido. O checksum SHA-256 aparece nos logs do job.

## Build local (Windows)

Com Python 3.12 instalado:

```powershell
python -m pip install --upgrade pip
python -m pip install . pyinstaller==6.16.0
pyinstaller --noconfirm --clean --windowed --onedir --name AtlasAI --paths src --runtime-hook build/windows/runtime_hook.py --collect-all PySide6 --collect-all shiboken6 --hidden-import atlas.desktop.memories_dialog --hidden-import atlas.desktop.voice_orb src/atlas/desktop/app.py
choco install innosetup --no-progress -y
New-Item -ItemType Directory -Force -Path dist/installer
& "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe" build/windows/atlas-ai.iss
```

## Checklist antes de distribuir

- Confirmar que o serviço Render está ativo e que `/health` responde.
- Testar login/cadastro se o modo Supabase estiver habilitado.
- Testar chat, histórico, memórias, microfone, transcrição e reprodução de áudio em uma instalação limpa do Windows.
- Verificar que o instalador não contém arquivos `.env`, chaves ou bancos locais de desenvolvimento.
- Testar instalação, abertura, desinstalação e atualização manual.
- Conferir o aviso de primeira execução do Windows em um computador que não tenha o ambiente de desenvolvimento.

O workflow constrói e verifica a existência do instalador, mas isso não substitui testes funcionais no Windows nem comprova disponibilidade da API e dos serviços externos. O plano gratuito do Render pode suspender o serviço após inatividade.

## Assinatura digital

A primeira versão não usa certificado pago. Antes de uma distribuição pública mais ampla, considere assinar o executável e o instalador com um certificado de assinatura de código. Não armazene certificados ou senhas de assinatura no repositório.
