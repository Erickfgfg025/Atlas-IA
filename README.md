# ATLAS

Assistente pessoal para Windows 10 e 11, construído em C# e .NET 10, com interface WinUI 3. O Atlas foi projetado para operar localmente sempre que possível, com provedores de IA intercambiáveis e automação do Windows protegida por permissões explícitas.

> **Estado desta branch:** fundação arquitetural e primeira revisão da experiência principal. A interface concentra a conversa em uma tela e mantém preferências em um diálogo separado. O modo de voz possui reconhecimento pt-BR e síntese nativos do Windows em fluxo half-duplex: o microfone pausa durante a fala sintetizada para evitar que o Atlas transcreva a própria voz. Barge-in real e streaming ainda não estão implementados. A integração precisa de validação em hardware Windows real. A animação roxa atual é vetorial provisória; o GIF original ainda precisa ser adicionado como ativo do projeto.

## Stack

- C# / .NET 10
- WinUI 3 / Windows App SDK
- MVVM com CommunityToolkit.Mvvm
- Arquitetura modular: Domain, Application, Infrastructure e adaptadores
- SQLite para índice operacional; Obsidian/Markdown como memória legível pelo usuário
- Gemini como provedor cloud principal; Ollama como alternativa local
- Hermes Agent opcional por processo filho isolado (web-only; exige checkout e Python configurados)
- Serviço de voz Windows (STT/TTS half-duplex; streaming e barge-in são etapas futuras)

## Estrutura

```text
src/
  Atlas.Desktop/       # Aplicativo WinUI 3
  Atlas.Domain/        # Entidades e regras centrais
  Atlas.Application/   # Casos de uso e orquestração
  Atlas.Contracts/     # DTOs e contratos entre módulos
  Atlas.Infrastructure/# Configuração, persistência e serviços de plataforma
  Atlas.AI/            # Abstrações e roteamento de provedores
  Atlas.AgentHost/     # Host isolado do runtime de agente
  Atlas.WindowsBridge/ # Fronteira segura com APIs do Windows
  Atlas.Memory/        # SQLite + integração futura com vault Obsidian
  Atlas.Audio/         # Pipeline de áudio
  Atlas.Security/      # Políticas, permissões e auditoria
tests/
  Atlas.UnitTests/
```

## Requisitos

- Windows 10 versão 19041 ou superior / Windows 11
- .NET 10 SDK
- Visual Studio 2022/2026 com workload **Desenvolvimento para aplicativos Windows** e Windows App SDK
- Para executar a interface, ambiente Windows. A CI usa runner Windows.

## Desenvolvimento

```powershell
dotnet restore Atlas.sln
dotnet build Atlas.sln -c Debug
dotnet test Atlas.sln -c Debug
```

Abra `Atlas.sln` no Visual Studio para executar o projeto `Atlas.Desktop`.

## Configuração opcional do Hermes Agent

O Hermes não é iniciado automaticamente. Para habilitar o provedor, configure estas variáveis no ambiente do usuário antes de abrir o Atlas:

- `ATLAS_HERMES_ENABLED=true`
- `ATLAS_HERMES_PATH=C:\\caminho\\para\\hermes` (checkout que contém `run_agent.py`)
- `ATLAS_HERMES_MODEL=nome-do-modelo`
- `ATLAS_HERMES_PYTHON=python` (opcional; executável Python)
- `ATLAS_HERMES_TIMEOUT_SECONDS=180` (opcional; entre 10 e 900)

O adaptador executa o Hermes em processo filho encerrável, transmite somente variáveis de ambiente permitidas e habilita apenas o toolset `web`. Terminal, arquivos, computador, execução de código e browser são desabilitados. A integração não concede controle do Windows.

## Princípios de segurança

1. Nenhuma ferramenta de controle do computador é executada diretamente a partir de texto gerado pelo modelo.
2. Ferramentas serão tipadas, allowlisted e validadas no backend local.
3. Ações destrutivas, administrativas, financeiras ou que exponham dados exigem confirmação explícita.
4. Não haverá elevação automática para administrador.
5. A chave Gemini é protegida por DPAPI no perfil do usuário Windows; segredos nunca devem entrar no repositório nem no executável.
6. Conteúdo externo, páginas web e documentos são dados não confiáveis, nunca instruções de sistema.
7. Toda ação privilegiada terá trilha de auditoria sem registrar segredos ou conteúdo sensível desnecessário.

## Estado de implementação

- [x] Solução modular e projetos iniciais
- [x] Shell WinUI 3 com tema escuro e tela principal simplificada
- [x] Preferências recolhidas em diálogo
- [x] Animação vetorial de ondas sonoras provisória
- [x] Configurações locais tipadas e chave protegida pelo Windows
- [x] Abstrações iniciais para provedores e memória
- [x] CI Windows para build e testes
- [ ] Integrar o GIF Sound Wave fornecido como ativo final (a imagem recebida ainda não está no repositório)
- [x] Primeira integração de voz Windows (SpeechRecognizer pt-BR + SpeechSynthesizer)
- [x] Fluxo de conversa por voz conectado ao roteador de modelos
- [ ] Validar captura e síntese em hardware Windows real e configurar permissões de microfone no empacotamento
- [x] Persistência local Markdown + índice SQLite reconstruível
- [x] Roteamento básico Gemini/Ollama com validação de respostas e erros HTTP
- [x] Adaptador Hermes local isolado, com ferramentas web habilitadas e execução de comandos/arquivos/computador desabilitada
- [x] Arquivos Markdown compatíveis com Obsidian + índice SQLite; seleção/abertura de vault pela interface ainda pendente
- [x] Base inicial de abertura de URLs HTTP(S) com confirmação explícita e sem execução arbitrária de comandos
- [x] Inicialização automática por usuário e opção sempre visível
- [ ] Automação segura do Windows (demais ferramentas tipadas e auditadas)
- [x] Workflow de empacotamento Windows x64 configurado (artefato ainda não publicado)
- [ ] Assinatura de código e atualização automática

A presença de um contrato ou projeto não significa que a integração externa esteja operacional. Cada integração será marcada como concluída somente após implementação e testes verificáveis.
