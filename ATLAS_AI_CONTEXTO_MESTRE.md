# ATLAS AI --- Contexto Mestre do Projeto

**Documento de contexto para ChatGPT Projects**\
**Plataforma:** Windows 10/11 · **IA principal:** Google Gemini ·
**Backend e memória:** Supabase + serviço Python na nuvem ·
**Repositório:** GitHub\
**Status:** definição e planejamento de um produto real, profissional e
evolutivo. Não tratar como protótipo descartável.

------------------------------------------------------------------------

## 1. Visão e objetivo

Construir um assistente pessoal de IA para Windows 10 e Windows 11,
inspirado na ideia de JARVIS, mas limitado às capacidades técnicas
reais. Deve ser um aplicativo desktop instalável, com interface própria,
voz, memória persistente, capacidade de interpretar contexto e executar
tarefas autorizadas no computador.

O assistente deve fazer mais do que conversar: interpretar a intenção do
usuário, elaborar um plano, selecionar ferramentas, executar etapas,
verificar os resultados, recuperar-se de falhas quando seguro e explicar
honestamente o que conseguiu ou não conseguiu fazer.

**Não é um projeto de demonstração.** Código, arquitetura, documentação,
testes, segurança, empacotamento, atualizações e manutenção devem ser
considerados desde o início.


## Identidade visual do produto

- Nome de trabalho: **ATLAS AI**.
- Direção escolhida: **minimalista e premium**.
- Usar tipografia limpa, espaçamento generoso, ícone geométrico próprio e paleta contida: grafite/carvão, prata ou titânio e um acento azul elétrico discreto.
- Evitar estética genérica de “IA”, excesso de gradientes, anéis decorativos, efeitos holográficos exagerados e elementos que prejudiquem legibilidade.
- A marca, domínio e nome do repositório ainda precisam de verificação de disponibilidade antes de lançamento público.

## 2. Requisitos obrigatórios

-   Aplicativo desktop próprio para Windows 10/11, distribuído como
    `.exe`/instalador.
-   Não usar um site, navegador, interface web ou `localhost` como
    interface principal do produto.
-   Janela própria, histórico de conversas, configurações, indicador de
    estado do agente e painel de atividades.
-   Ícone na bandeja do sistema (system tray), atalho e entrada no Menu
    Iniciar; inicialização com o Windows deve ser opcional e
    configurável.
-   Gemini como modelo principal por meio da API oficial e do SDK atual
    `google-genai`.
-   Supabase para PostgreSQL, autenticação, dados persistentes e, quando
    necessário, pesquisa semântica com pgvector.
-   Backend Python hospedado na nuvem para proteger credenciais,
    coordenar tarefas, aplicar políticas e sincronizar dados.
-   Agente local no Windows para realizar operações que só podem
    acontecer no PC do usuário.
-   Comunicação autenticada entre desktop, backend e agente local. O
    agente local deve iniciar a conexão de saída; não abrir uma porta
    pública no PC por padrão.
-   Comandos em português natural, tanto informais quanto formais, com
    resolução de referências contextuais.
-   Memória de sessão, memória persistente, preferências e memória de
    projetos, com possibilidade de consultar, corrigir e apagar
    informações.
-   Voz e texto. A arquitetura de voz deve permitir STT, TTS, streaming
    e interrupção da fala (barge-in) quando tecnicamente viável.
    ElevenLabs pode ser avaliado como opção de TTS, sem tornar o produto
    dependente dele.
-   Integração futura com e-mail, navegador, arquivos, aplicações,
    calendário e ferramentas de desenvolvimento.
-   Logs úteis, tratamento de exceções, métricas, testes automatizados,
    documentação e pipeline de CI.
-   GitHub como fonte de verdade do código. Nenhuma chave, token, senha,
    dado pessoal ou arquivo `.env` deve ser commitado.
-   Otimizar o custo inicial, mas não prometer que o uso contínuo de
    APIs de IA ou hospedagem será sempre gratuito.

## 3. Arquitetura de referência

Separar responsabilidades para evitar um monólito frágil.

### A. Aplicativo desktop Windows

Responsável pela interface, captura de voz, apresentação de respostas,
status das tarefas e preferências locais. Opção inicial prática:
Python + PySide6, empacotado como executável. Manter a interface
separada do núcleo do agente para que a UI possa ser substituída no
futuro sem reescrever a lógica.

### B. Agente local Windows

Executa ações locais através de adaptadores pequenos e testáveis.
Possíveis ferramentas: - `pywinauto` e APIs do Windows para automação de
aplicações; - PowerShell e `subprocess` com comandos estruturados e
allowlist; - `pyautogui` somente quando uma API de automação mais
robusta não estiver disponível; - Playwright para automação de navegador
quando necessário e explicitamente habilitado; - operações de arquivo
com escopo, validação de caminhos e prevenção contra traversal.

Não permitir que o modelo execute texto arbitrário diretamente no shell.
O modelo propõe uma chamada de ferramenta estruturada; o executor valida
os argumentos, verifica a política e executa uma ação conhecida.

### C. Backend de orquestração na nuvem

Serviço Python com API autenticada (FastAPI é uma opção).
Responsabilidades: - autenticação e autorização; - integração com
Gemini; - planejamento e ciclo de chamadas de ferramentas; - aplicação
de políticas de segurança; - coordenação de tarefas longas e estado de
execução; - acesso ao Supabase usando credenciais protegidas no
servidor; - auditoria, limites de uso, tratamento de erros e telemetria
sem conteúdo sensível desnecessário.

Não assumir que uma instância gratuita permanece acordada ou disponível
24/7. Confirmar limites, política de suspensão, custos e monitoramento
antes de escolher o provedor definitivo.

### D. Gemini

Usar a API oficial do Google e o SDK `google-genai`. Implementar
tool/function calling com esquemas tipados. A IA não executa ferramentas
por si só: a aplicação valida e executa as chamadas e envia os
resultados ao modelo. Tratar respostas inválidas, chamadas repetidas,
timeouts, limites de taxa, erros de rede e respostas incompletas.

### E. Supabase

-   PostgreSQL para usuários, dispositivos, preferências, conversas,
    fatos de memória, tarefas, execuções e auditoria.
-   Supabase Auth para identidade e sessões quando adequado.
-   Row Level Security (RLS) em tabelas acessíveis por clientes.
-   pgvector apenas quando a recuperação semântica realmente for
    necessária.
-   Migrações versionadas no GitHub; não depender de mudanças manuais
    não documentadas no painel.
-   A `service_role` nunca pode ser enviada ao desktop nem incorporada
    ao executável.
-   Guardar no backend os segredos de Gemini e Supabase que precisem de
    privilégio elevado.

Manter um cache local mínimo (por exemplo, SQLite) para preferências
essenciais, estado offline e recuperação de sessão. Definir claramente
qual dado é fonte de verdade local e qual é fonte de verdade na nuvem.

## 4. Memória e contexto

Implementar memória com tipos explícitos, em vez de guardar tudo como um
bloco de texto indistinto.

1.  **Memória de sessão:** mensagens e estado da tarefa atual.
2.  **Memória episódica:** resumo de conversas e ações passadas que
    sejam úteis no futuro.
3.  **Memória semântica:** fatos e preferências estáveis aprovados para
    reutilização.
4.  **Memória de projeto:** repositórios, stack, decisões, tarefas
    abertas e convenções de cada projeto.
5.  **Memória operacional:** estado e resultado de tarefas em andamento,
    com identificadores e timestamps.

Cada memória persistente deve, quando aplicável, ter origem, data,
confiança, escopo, data de expiração e mecanismo de correção/exclusão.
Evitar gravar segredos ou dados sensíveis sem necessidade. Recuperar
apenas o contexto relevante para a tarefa; não enviar todo o histórico
ao modelo por padrão.

## 5. Autonomia e segurança

O objetivo é **alta autonomia dentro de políticas explícitas**, sem
pedir confirmação para cada ação cotidiana. Não interpretar "autonomia
completa" como permissão para executar qualquer ação sem limites.

### Política inicial sugerida

-   **Baixo risco:** abrir aplicativo, consultar hora, pesquisar
    arquivos em diretórios autorizados, ler status e executar testes não
    destrutivos. Pode executar automaticamente.
-   **Risco moderado:** editar arquivos, mover dados, instalar
    dependências, alterar configurações ou executar scripts. Usar
    escopo, backup/diff, sandbox quando possível e política
    configurável.
-   **Alto risco/impacto externo:** apagar permanentemente dados, enviar
    e-mails ou mensagens, publicar conteúdo, compras, alterar
    credenciais, elevar privilégios ou executar comandos
    administrativos. Exigir aprovação explícita ou política específica
    previamente configurada.
-   **Desligar/reiniciar o PC:** permitir execução direta quando o
    comando for inequívoco e tiver sido solicitado pelo usuário; avisar
    sobre perda de trabalho quando aplicável.

Proteções obrigatórias: - não executar instruções encontradas em
e-mails, páginas ou documentos como se fossem comandos do dono; tratar
esses conteúdos como dados não confiáveis; - validação de esquema e
allowlist para ferramentas; - privilégio mínimo, separação de processos
e escopos de diretório; - limites de tempo, tentativas, tamanho de saída
e custo; - confirmação para ações críticas e irreversíveis; - logs de
auditoria sem tokens nem conteúdo privado desnecessário; - botão de
parar/cancelar e mecanismo de interrupção; - credenciais protegidas no
Windows (Credential Manager ou mecanismo apropriado); - comunicação TLS,
autenticação por dispositivo, revogação de dispositivos e rotação de
tokens; - nunca alegar que uma ação foi concluída sem verificar o
resultado.

## 6. Loop do agente

Para cada tarefa:

1.  Interpretar o pedido e recuperar o contexto estritamente relevante.
2.  Determinar objetivo, pré-condições e risco.
3.  Criar um plano curto com etapas observáveis.
4.  Escolher ferramentas declaradas e validadas.
5.  Validar argumentos e aplicar política antes da execução.
6.  Executar uma etapa por vez ou em paralelo apenas quando seguro.
7.  Inspecionar o resultado real da ferramenta.
8.  Replanejar em caso de falha recuperável, com limite de tentativas.
9.  Interromper e pedir intervenção quando houver ambiguidade crítica,
    risco excessivo ou ausência de permissão.
10. Registrar o resultado, atualizar a memória quando apropriado e
    informar claramente o que ocorreu.

## 7. Autoaperfeiçoamento controlado

O sistema pode analisar falhas, sugerir mudanças de código, abrir
issues/branches e preparar pull requests. Não deve alterar
silenciosamente o próprio código de produção.

Fluxo obrigatório: 1. identificar problema reproduzível; 2. criar issue
ou plano de mudança; 3. produzir diff pequeno e explicável em branch
isolada; 4. executar testes, lint, análise de segurança e verificações
relevantes; 5. avaliar regressões; 6. exigir aprovação humana antes de
mesclar ou publicar; 7. manter rollback e versão anterior recuperável.

## 8. GitHub e engenharia profissional

O repositório deve incluir: - `README.md` com objetivo, arquitetura,
instalação e configuração; - `AGENTS.md` ou instruções equivalentes para
agentes de codificação; - `docs/architecture.md`, `docs/security.md`,
`docs/decisions/` (ADRs) e guia de contribuição; - `.env.example` sem
valores reais; - dependências fixadas e atualizações controladas; -
testes unitários e de integração; - GitHub Actions para lint, type
checking, testes e verificações de segurança; - migrações de banco
versionadas; - templates de issues e pull requests; - política de
versões, changelog e releases; - licença escolhida conscientemente após
revisar dependências e referências.

Nunca editar o repositório inteiro sem antes inspecionar a estrutura e
os arquivos relevantes. Antes de uma alteração: entender a arquitetura
atual, identificar impacto, criar diff mínimo, testar e relatar com
honestidade o que foi e não foi executado.

## 9. Projetos públicos para estudar, sem copiar cegamente

Usar os repositórios como referências de padrões e ideias. Antes de
reutilizar código, verificar licença, atividade recente, dependências,
segurança, compatibilidade Windows e avisos de marca.

-   Personal Jarvis --- experiência de assistente desktop, voz, agentes
    e memória: https://github.com/PersonalJarvis/PersonalJarvis
-   OpenClaw --- assistente extensível e sistema de ferramentas:
    https://github.com/openclaw/openclaw
-   Open Interpreter Workstation --- runtime, ferramentas e adaptadores
    de computador:
    https://github.com/openinterpreter/interpreter-workstation
-   Goose --- agente extensível e arquitetura de ferramentas:
    https://github.com/block/goose
-   JARVIS-6 --- integração de Gemini, voz e automação Windows:
    https://github.com/psycoks/Jarvis
-   OpenHands --- execução de tarefas de desenvolvimento e ciclo de
    agente: https://github.com/All-Hands-AI/OpenHands
-   IRIS --- foco Windows/local, memória controlada e limites de
    ferramentas: https://github.com/supermang617/IRIS
-   Google Gemini function calling:
    https://ai.google.dev/gemini-api/docs/function-calling
-   Google GenAI SDK migration:
    https://ai.google.dev/gemini-api/docs/migrate
-   Supabase docs: https://supabase.com/docs
-   PySide6 docs: https://doc.qt.io/qtforpython/

Essas referências não são dependências obrigatórias nem endosso de que
qualquer projeto seja seguro para produção. O produto final deve ter
arquitetura própria e selecionar componentes com base em evidências.


## 9.1 Pesquisa de arquitetura de agentes de IA

**Objetivo da pesquisa:** aproveitar padrões públicos e documentados de agentes maduros sem copiar projetos inteiros, sem assumir que popularidade equivale a segurança e sem adicionar frameworks por moda. As referências abaixo devem ser revalidadas antes de adotar código, dependências ou decisões de implementação.

### Projetos e padrões estudados

| Referência | Padrões úteis para o ATLAS | O que não copiar automaticamente |
|---|---|---|
| Personal Jarvis — https://github.com/PersonalJarvis/PersonalJarvis | Experiência desktop integrada; voz; controle do computador; agentes persistentes; memória visível; acompanhamento do trabalho | Não adotar toda a aplicação, marketplace ou arquitetura de modelos se isso aumentar complexidade sem atender aos requisitos do ATLAS |
| OpenClaw runtime — https://github.com/openclaw/openclaw/blob/main/docs/agent-runtime-architecture.md | Separação entre loop do agente, provedores de modelo, sessões, ferramentas, políticas e hooks; contratos explícitos entre componentes | Não importar seu runtime inteiro nem presumir que sua superfície de plugins seja necessária |
| OpenClaw memory — https://github.com/openclaw/openclaw/blob/main/docs/concepts/memory-architecture.md | Memória com níveis de confiança, origem dos dados, curadoria, recuperação com limites e falhas que não bloqueiam a resposta | Não guardar toda conversa como memória permanente; não permitir que conteúdo externo promova a si próprio a memória confiável |
| Goose — https://github.com/block/goose/blob/main/ARCHITECTURE.md | Extensões modulares, ferramentas separadas da interface, plano de execução e distinção entre eventos persistentes e status transitórios | Não dar acesso irrestrito ao shell apenas porque uma extensão o oferece |
| Google ADK — https://google.github.io/adk-docs/ | Agentes, ferramentas, sessões, memória, workflows, avaliação e telemetria; proximidade conceitual com o ecossistema Gemini | Não adicionar ADK automaticamente. Começar com `google-genai` e um loop pequeno; avaliar ADK por protótipo comparativo quando houver benefício comprovado |
| Microsoft Agent Framework — https://learn.microsoft.com/agent-framework/overview | Separação entre agente e workflow; estado de tarefas longas; middleware, telemetria e pontos de intervenção humana | Não usar workflows multiagente para tarefas simples que uma função determinística resolve |
| OpenHands — https://github.com/All-Hands-AI/OpenHands | Execução orientada a eventos, ambientes isolados e limites claros para tarefas de desenvolvimento | Não executar código arbitrário gerado pelo modelo no computador pessoal sem sandbox e política própria |
| Anthropic, Building Effective AI Agents — https://resources.anthropic.com/building-effective-ai-agents | Escolher entre fluxo determinístico, agente único e múltiplos agentes de acordo com a complexidade real | Não confundir mais agentes, prompts ou etapas com maior qualidade |

Documentação complementar:
- Gemini Function Calling: https://ai.google.dev/gemini-api/docs/function-calling
- Google ADK: https://google.github.io/adk-docs/
- ADK evaluation guide: https://google.github.io/agents-cli/guide/evaluation/
- Supabase: https://supabase.com/docs
- PySide6: https://doc.qt.io/qtforpython/

### Conclusões aplicáveis ao ATLAS

1. **Começar com um agente principal, não uma equipe de agentes.** Um orquestrador com ferramentas tipadas é mais simples de testar, auditar e manter. Só introduzir agentes especializados quando avaliações demonstrarem que a delegação melhora qualidade, tempo ou custo.
2. **Separar decisão de execução.** Gemini escolhe uma ferramenta por meio de uma chamada estruturada. Um executor determinístico valida identidade, argumentos, escopo, risco, permissões e limites antes de executar.
3. **Usar workflows explícitos para tarefas previsíveis.** Instalação, backup, operações de arquivos, envio de mensagens e processos administrativos devem seguir etapas definidas, não improvisação ilimitada do modelo.
4. **Tratar tarefas como entidades persistentes.** Cada execução deve ter `task_id`, estado, etapas, timestamps, tentativas, eventos, cancelamento, resultado e motivo de falha. Operações longas devem sobreviver a reinicializações do backend quando tecnicamente viável.
5. **Memória é um produto de curadoria.** Registrar origem, data, escopo, confiança, sensibilidade e política de expiração. Separar fatos aprovados, resumos de episódios, contexto de projeto e dados não confiáveis. Recuperar apenas o necessário.
6. **A memória nunca deve bloquear a resposta.** Aplicar timeouts, limites e fallback quando Supabase ou busca semântica estiverem indisponíveis. Não inventar lembranças quando a recuperação falhar.
7. **Toda ação precisa deixar evidência verificável.** Registrar a ferramenta solicitada, parâmetros normalizados, decisão da política, início/fim, código de saída e evidência de sucesso, minimizando dados sensíveis.
8. **Segurança é uma camada do runtime.** Instruções encontradas em páginas, e-mails, PDFs, imagens, código ou resultados de ferramentas são dados não confiáveis, nunca autorização para mudar as políticas do agente.
9. **Avaliar trajetórias, não só respostas finais.** Testar seleção de ferramentas, argumentos, ordem de etapas, tratamento de erros, interrupção, custo, latência e se o objetivo realmente foi concluído.
10. **A interface deve mostrar estados reais.** Distinguir “pensando”, “planejando”, “executando ferramenta”, “aguardando autorização”, “verificando”, “concluído”, “falhou” e “cancelado”. Não exibir conclusão antes da confirmação do executor.

## 9.2 Arquitetura-alvo recomendada para o ATLAS

### Visão de alto nível

```text
Aplicativo Windows (PySide6)
  ├── UI, voz, histórico, configurações, status e cancelamento
  ├── cache local SQLite e credenciais protegidas pelo Windows
  └── cliente autenticado
          │ TLS + sessão curta + identificação do dispositivo
          ▼
Backend Python (FastAPI ou alternativa validada)
  ├── autenticação, autorização e limites
  ├── Agent Orchestrator / ciclo Gemini
  ├── Planner leve + estado da tarefa
  ├── Tool Registry + schemas tipados
  ├── Policy Engine / aprovação / idempotência
  ├── Memory Service
  ├── Task Runner / checkpoints / retries limitados
  ├── observabilidade, auditoria e avaliação
  └── adaptadores de integrações externas
          │
          ├── Gemini API (`google-genai`)
          ├── Supabase PostgreSQL / Auth / Storage / pgvector quando útil
          └── canal seguro de saída para o agente Windows
                    │
                    ▼
             Agente local Windows
               ├── catálogo local de ferramentas
               ├── validação local independente
               ├── automação de apps e arquivos autorizados
               ├── execução isolada quando necessária
               └── evidência real do resultado
```

O backend não deve presumir que o agente Windows está sempre online. A conexão local deve ser iniciada pelo próprio agente e autenticada; não abrir uma porta pública no PC por padrão. Quando o dispositivo estiver offline, a tarefa deve permanecer em estado explícito de espera ou falhar com uma mensagem clara.

### Componentes e contratos

**1. Desktop shell**
- PySide6 como opção inicial; UI desacoplada da lógica de negócio.
- Streaming de respostas, cancelamento, histórico e painel de eventos.
- System tray e inicialização automática opcionais.
- Credenciais locais protegidas pelo Windows Credential Manager ou mecanismo equivalente.
- Cache SQLite limitado e com regra clara de sincronização.

**2. Agent Orchestrator**
- Um ciclo de execução controlado pelo servidor, com limite máximo de chamadas, tempo, tokens/custo e ferramentas por tarefa.
- Gemini via SDK oficial `google-genai`; manter uma interface interna para permitir troca de versão/modelo sem espalhar chamadas do SDK pelo código.
- Cada turno pode terminar em resposta final, chamada de ferramenta válida, pedido de autorização ou falha explícita.
- Limitar repetições de chamadas equivalentes e detectar ciclos improdutivos.
- Não delegar tarefas a múltiplos agentes na primeira versão.

**3. Tool Registry**
Cada ferramenta deve declarar:
- nome estável e versão;
- descrição curta e precisa para o modelo;
- schema de entrada tipado;
- permissões e escopos necessários;
- nível de risco;
- timeout e limites de saída;
- regra de idempotência;
- executor;
- schema de resultado e evidência verificável;
- política de retry e cancelamento.

Ferramentas iniciais candidatas: consultar hora/data; abrir aplicativos de uma lista autorizada; listar diretórios permitidos; ler arquivos autorizados; consultar estado básico do Windows; criar/editar arquivos dentro de diretórios explicitamente autorizados; desligar o PC apenas quando solicitado de forma inequívoca.

**4. Policy Engine**
- Negar por padrão ferramentas desconhecidas ou não habilitadas.
- Validar novamente no agente local, mesmo que o backend já tenha validado.
- Separar autorização do usuário, autorização do dispositivo e autorização da ação.
- Baixo risco pode executar automaticamente; risco moderado exige escopo e salvaguardas; ação destrutiva, administrativa ou com impacto externo requer aprovação explícita ou regra previamente configurada.
- Aprovação vinculada a uma ação específica, parâmetros, prazo e `task_id`; nunca aceitar uma autorização genérica reutilizável para qualquer ação.
- Implementar botão global de interrupção e cancelamento por tarefa.

**5. Task Runner e estado durável**
Estados recomendados:
`queued → planning → awaiting_approval → running → verifying → succeeded | failed | cancelled | waiting_for_device`.

- Salvar transições importantes e resultados de ferramentas.
- Usar `task_id` e chaves de idempotência para reduzir ações duplicadas após timeout ou reconexão.
- Fazer retry apenas em falhas recuperáveis e operações seguras.
- Persistir checkpoints em tarefas longas e retomar somente após validar se o estado externo ainda corresponde ao esperado.
- Não prometer “exactly once” para sistemas externos que não oferecem essa garantia; usar idempotência, reconciliação e evidência.

**6. Memory Service**
Separar pelo menos:
- memória de sessão;
- memória episódica (resumos úteis de interações e tarefas);
- memória semântica (preferências e fatos estáveis);
- memória de projeto;
- memória operacional (tarefas e estado);
- documentos e fontes externas não confiáveis.

Cada registro deve poder conter `user_id`, tipo, conteúdo, origem, timestamp, confiança, escopo, sensibilidade, expiração, versão e estado de aprovação. Usar RLS no Supabase para dados acessíveis por clientes. Operações privilegiadas ficam no backend; nunca expor `service_role` ao desktop.

A busca deve combinar filtros estruturados e, quando útil, busca textual/semântica. Não introduzir pgvector antes de existir um caso de uso mensurável. O usuário deve poder consultar, corrigir, exportar e apagar memórias.

**7. Comunicação com o agente local**
- Conexão de saída do agente para backend; transporte autenticado e criptografado.
- Credenciais de dispositivo de curta duração ou rotacionáveis, revogação e limite de dispositivos.
- Protocolo de mensagens versionado, com `task_id`, `tool_call_id`, nonce/expiração quando apropriado e identificador de correlação.
- O agente local revalida ferramenta, parâmetros, caminho de arquivo e política antes da execução.
- Não aceitar texto arbitrário do modelo como comando de PowerShell, shell, Python ou `cmd.exe`.
- Preferir APIs específicas do Windows; usar automação de interface gráfica apenas quando uma API estável não existir.
- Execução de código gerado exige ambiente isolado, limites de recursos e diretório temporário. Não conceder sandbox de código livre ao agente local por padrão.

### Decisão de framework

**Decisão inicial:** usar `google-genai` diretamente e implementar um orquestrador pequeno, testável e orientado a estados. Isso mantém o ATLAS alinhado ao Gemini e evita acoplar prematuramente a lógica central a um framework amplo.

**Avaliar Google ADK** em um protótipo isolado se precisarmos de workflows, ferramentas, sessões e avaliação integradas. Comparar com a implementação própria usando o mesmo conjunto de testes, medindo qualidade de trajetória, latência, complexidade, dependências e custo.

**Avaliar um motor de workflow durável** apenas quando tarefas longas e retomáveis justificarem a dependência. Não introduzir LangGraph, Microsoft Agent Framework, filas distribuídas ou arquitetura multiagente sem requisito demonstrado.

### Esboço de módulos

```text
atlas/
  desktop/
    app.py
    views/
    controllers/
    audio/
    local_cache/
  backend/
    api/
    auth/
    orchestrator/
    policies/
    tasks/
    memory/
    tools/
    integrations/
    observability/
  windows_agent/
    service/
    tool_catalog/
    adapters/
    security/
  shared/
    contracts/
    schemas/
    errors/
  migrations/
  tests/
    unit/
    integration/
    security/
    evals/
  docs/
    architecture.md
    security.md
    decisions/
```

É um mapa conceitual, não uma ordem para criar todos os diretórios imediatamente. A estrutura real deve acompanhar as primeiras entregas e o repositório existente.

## 9.3 Avaliação, monitoramento e critérios de qualidade

Manter um conjunto versionado de casos de avaliação. Cada caso deve especificar pedido, contexto, ferramentas esperadas ou proibidas, resultado observável e critérios de sucesso.

Cobertura mínima:
- intenção ambígua versus comando explícito;
- chamada de ferramenta correta e argumentos inválidos;
- acesso a arquivo fora do escopo;
- prompt injection em página, e-mail ou documento;
- Supabase/Gemini indisponível;
- dispositivo Windows offline;
- timeout e reconexão sem duplicar ação;
- cancelamento durante tarefa;
- autorização expirada ou concedida para parâmetros diferentes;
- memória incorreta, antiga ou contraditória;
- ação de alto risco que deve ser bloqueada;
- tarefa multi-etapas que falha no meio e precisa retomar com segurança.

Métricas:
- taxa de conclusão verificada por tarefa;
- precisão de seleção e parâmetros de ferramentas;
- taxa de ações indevidas bloqueadas nos testes;
- taxa de duplicação após retries;
- latência por etapa e tempo total;
- custo por tarefa;
- taxa de falha e recuperação;
- qualidade de recuperação de memória;
- taxa de cancelamento respeitado.

Não usar apenas avaliação por outro modelo. Combinar assertions determinísticas, testes de integração, revisão humana de amostras e avaliação de trajetórias. Logs não devem armazenar tokens, segredos ou conteúdo privado sem necessidade e política explícita.

## 9.4 Ordem de implementação revisada

1. **Contrato e base:** inspecionar repositório, definir interfaces, configuração, logging, testes, autenticação e schemas compartilhados.
2. **Uma tarefa ponta a ponta:** desktop envia uma mensagem; backend chama Gemini; resposta chega à UI; logs e tratamento de erros funcionam.
3. **Uma ferramenta segura:** consultar estado ou abrir um aplicativo permitido, com validação no backend e no agente local.
4. **Ciclo de ferramenta completo:** Gemini solicita ferramenta, executor valida, ferramenta executa, resultado é devolvido ao modelo, resposta final só após verificação.
5. **Estado durável e cancelamento:** persistência de tarefas, transições, timeout, idempotência e retomada segura.
6. **Memória básica:** preferências aprovadas e resumos curados, com consulta/edição/exclusão; medir antes de acrescentar busca vetorial.
7. **Voz:** STT/TTS, streaming, interrupção e estados visíveis.
8. **Integrações de risco controlado:** arquivos, navegador, e-mail e automações, cada uma com adaptador, política e testes próprios.
9. **Qualidade de produção:** avaliação contínua, CI, monitoramento, instalador, atualização, backups e procedimento de rollback.

Cada fase exige critérios de aceite e evidência de teste. Não marcar tarefas como concluídas apenas porque o código foi escrito.


## 10. Fases de entrega

### Fase 0 --- descoberta

Inspecionar o repositório e o ambiente existente. Registrar decisões,
riscos, requisitos não funcionais e critérios de aceite. Não começar por
uma grande interface visual.

### Fase 1 --- base confiável

Estrutura de pacotes, configuração, logging, testes, cliente Gemini,
backend, Supabase e autenticação.

### Fase 2 --- desktop

Janela funcional, chat, estados de execução, histórico e empacotamento
de desenvolvimento.

### Fase 3 --- agente Windows

Ferramentas iniciais seguras: hora/data, abrir aplicativo por mapeamento
conhecido, listar diretório permitido, ler arquivo permitido, consultar
estado e desligar o PC mediante comando inequívoco. Testes automatizados
e logs.

### Fase 4 --- memória

Memória de sessão e persistente, preferências, projetos, pesquisa
contextual, exclusão e exportação.

### Fase 5 --- voz

STT/TTS, fluxo de áudio, interrupção da fala, escolha de voz e gestão de
permissões do microfone.

### Fase 6 --- automação avançada

Navegador, e-mail e aplicativos com adaptadores isolados, limites por
ferramenta e verificação de resultados.

### Fase 7 --- robustez e lançamento

CI/CD, instalador, atualizações, diagnóstico, backups, testes de falha,
documentação de segurança e releases assinadas quando viável.

Não marcar uma fase como concluída sem critérios de aceite verificáveis.

## 11. Como o ChatGPT deve trabalhar neste projeto

-   Atuar como engenheiro de software sênior, arquiteto e revisor de
    segurança.
-   Ser direto, crítico e técnico; questionar decisões frágeis.
-   Não inventar execução de comandos, testes, deploys ou alterações no
    GitHub.
-   Antes de editar código existente, inspecionar os arquivos relevantes
    completos e entender o fluxo.
-   Propor alterações pequenas, reversíveis e testáveis.
-   Explicar decisões arquiteturais e consequências práticas.
-   Priorizar segurança, confiabilidade, manutenção, desempenho e custo
    total.
-   Usar documentação oficial e repositórios originais para fatos
    atuais; citar fontes quando fizer pesquisa.
-   Não adicionar tecnologias apenas por moda; cada dependência precisa
    justificar seu valor.
-   Distinguir fatos confirmados, hipóteses e decisões pendentes.
-   Não usar Telegram como interface do produto. A interface principal é
    um aplicativo desktop Windows.
-   Não transformar o projeto em site ou interface web.
-   Não introduzir Ollama como cérebro principal por padrão: a decisão
    atual é Gemini. Modelos locais só entram como opção complementar se
    houver justificativa.
-   Não substituir o Supabase sem explicar uma razão técnica concreta.
-   Nunca publicar segredos, tokens, chaves de API ou dados pessoais.
-   Quando faltar um dado essencial, fazer uma pergunta objetiva; caso
    contrário, avançar com uma proposta explícita e verificável.

## 12. Instruções resumidas para o campo "Project Instructions" do ChatGPT

Você é o arquiteto e engenheiro principal do ATLAS AI, um assistente
pessoal profissional para Windows 10/11. O produto é um aplicativo
desktop instalável, não um protótipo, site ou interface web. A IA
principal é Google Gemini via SDK oficial `google-genai`; Supabase
fornece PostgreSQL, autenticação e memória persistente; um backend
Python na nuvem coordena as tarefas; um agente local autenticado executa
ações no Windows. A interface inicial pode usar Python + PySide6, com
núcleo independente da UI. Não usar Telegram como interface do produto.

Priorize arquitetura modular, segurança, testes, logs, documentação,
empacotamento e custos controlados. Nunca exponha segredos no cliente ou
GitHub; nunca envie `service_role` ao desktop. O Gemini propõe chamadas
estruturadas de ferramentas, mas o executor local deve validar
argumentos, escopo e permissões antes de executar. Não permitir comandos
arbitrários de shell diretamente a partir da saída do modelo. A
autonomia deve ser alta para tarefas de baixo risco e limitada por
políticas para ações destrutivas, administrativas ou com impacto
externo.

O agente deve planejar, executar, verificar, recuperar-se de falhas
seguras e relatar apenas resultados confirmados. Memória deve ser
estruturada, contextual, persistente, corrigível e apagável. O
autoaperfeiçoamento só pode propor diffs/branches e executar testes em
ambiente controlado; publicação ou mesclagem exige aprovação humana e
rollback.

Antes de editar repositórios existentes, inspecione os arquivos e a
arquitetura. Faça mudanças mínimas e reversíveis, execute testes quando
houver ambiente disponível e nunca afirme testes, deploys ou operações
que não realizou. Use documentação oficial e repositórios públicos como
referências, não copie projetos inteiros sem auditoria de licença e
segurança. Mantenha decisões e critérios de aceite documentados. Se
faltar informação essencial, pergunte; caso contrário, avance com uma
solução concreta e explique os trade-offs.

------------------------------------------------------------------------

## 13. Primeira mensagem recomendada para iniciar o trabalho no ChatGPT Project

"Leia integralmente o contexto mestre deste projeto. Antes de
implementar qualquer recurso, apresente um plano de execução
profissional, a arquitetura inicial, os principais riscos, as decisões
ainda pendentes e os critérios de aceite da Fase 0. Se o GitHub já
estiver conectado, inspecione o repositório existente antes de propor
alterações. Não crie uma reescrita desnecessária e não afirme ter
executado nada sem evidência. Nosso objetivo é construir e manter um
produto real para Windows 10/11, com Gemini, Supabase, backend na nuvem
e agente local seguro."