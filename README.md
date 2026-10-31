# ATLAS

Assistente pessoal para Windows 10 e 11, construído em C# e .NET 10, com interface WinUI 3. O Atlas foi projetado para operar localmente sempre que possível, com provedores de IA intercambiáveis e automação do Windows protegida por permissões explícitas.

> **Estado desta branch:** fundação arquitetural inicial. A interface e os contratos-base estão sendo estabelecidos. Gemini, Ollama, Hermes, Obsidian, voz e automação ainda não estão integrados nesta entrega.

## Stack

- C# / .NET 10
- WinUI 3 / Windows App SDK
- MVVM com CommunityToolkit.Mvvm
- Arquitetura modular: Domain, Application, Infrastructure e adaptadores
- SQLite para índice operacional; Obsidian/Markdown como memória legível pelo usuário
- Gemini como provedor cloud principal; Ollama como alternativa local
- Hermes Agent isolado por adaptador
- Whisper para STT e Fish Speech para TTS, sujeitos à validação de compatibilidade e desempenho

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
- [x] Shell WinUI 3 com tema escuro e widget compacto
- [x] Orb visual inicial com estados explícitos
- [x] Configurações locais tipadas
- [x] Abstrações iniciais para provedores e memória
- [x] CI Windows para build e testes
- [ ] Persistência SQLite real
- [ ] ModelRouter Gemini/Ollama
- [ ] Adaptador Hermes
- [ ] Memória Obsidian + índice SQLite
- [ ] STT/TTS local
- [ ] Automação segura do Windows
- [ ] Instalador assinado e atualização

A presença de um contrato ou projeto não significa que a integração externa esteja operacional. Cada integração será marcada como concluída somente após implementação e testes verificáveis.
