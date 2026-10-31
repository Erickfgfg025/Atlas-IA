# ATLAS

Assistente pessoal para Windows 10 e 11, construído em C# e .NET 10, com interface WinUI 3. O Atlas foi projetado para operar localmente sempre que possível, com provedores de IA intercambiáveis e automação do Windows protegida por permissões explícitas.

> **Estado desta branch:** fundação arquitetural e primeira revisão da experiência principal. A interface concentra a conversa em uma tela e mantém preferências em um diálogo separado. O modo de voz contínuo ainda não está implementado; a próxima etapa adicionará captura, transcrição e síntese com interrupção de fala.

## Stack

- C# / .NET 10
- WinUI 3 / Windows App SDK
- MVVM com CommunityToolkit.Mvvm
- Arquitetura modular: Domain, Application, Infrastructure e adaptadores
- SQLite para índice operacional; Obsidian/Markdown como memória legível pelo usuário
- Gemini como provedor cloud principal; Ollama como alternativa local
- Hermes Agent isolado por adaptador
- Pipeline de voz desacoplado da interface (STT/TTS e streaming)

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

## Princípios de segurança

1. Nenhuma ferramenta de controle do computador é executada diretamente a partir de texto gerado pelo modelo.
2. Ferramentas serão tipadas, allowlisted e validadas no backend local.
3. Ações destrutivas, administrativas, financeiras ou que exponham dados exigem confirmação explícita.
4. Não haverá elevação automática para administrador.
5. Segredos ficam no Windows Credential Manager ou em armazenamento protegido, nunca no repositório nem no executável.
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
- [ ] Integrar o GIF Sound Wave fornecido como ativo final
- [ ] Modo de voz contínuo (captura, STT, TTS, streaming e barge-in)
- [ ] Persistência SQLite real
- [ ] ModelRouter Gemini/Ollama com validação de erros
- [ ] Adaptador Hermes
- [ ] Memória Obsidian + índice SQLite
- [ ] Automação segura do Windows
- [ ] Instalador assinado e atualização

A presença de um contrato ou projeto não significa que a integração externa esteja operacional. Cada integração será marcada como concluída somente após implementação e testes verificáveis.
