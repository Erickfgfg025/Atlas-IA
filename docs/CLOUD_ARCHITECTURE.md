# ATLAS AI: arquitetura cloud-first

## Objetivo

O núcleo do ATLAS deve continuar disponível quando o computador Windows estiver desligado. O aplicativo Windows é um cliente opcional, não o servidor principal.

## Componentes

- **Render Web Service:** hospeda a API FastAPI e a orquestração remota.
- **Supabase Auth:** autentica o usuário e emite tokens de acesso.
- **Supabase PostgreSQL:** fonte principal para memórias, conversas, mensagens, preferências e tarefas.
- **Fish Audio:** sintetiza respostas em voz. A chave fica somente no backend.
- **STT em nuvem:** transcreve áudio enviado pelo cliente autorizado.
- **Hermes Agent:** executor de tarefas com ferramentas explicitamente autorizadas.
- **OpenJarvis:** camada de experimentação/seleção de modelos, integrada por adaptador. Não executar Hermes e OpenJarvis em duplicidade para cada solicitação.
- **Obsidian:** vault Markdown como camada de conhecimento legível. Para acesso quando o PC estiver desligado, o vault precisa estar sincronizado com um armazenamento cloud suportado; um diretório local isolado não é acessível pelo Render.
- **Windows desktop:** interface, captura de microfone, reprodução de áudio e ferramentas locais. Quando o PC estiver desligado, o backend pode continuar com tarefas cloud, mas não pode usar microfone, alto-falantes ou controlar aquele PC desligado.

## Fluxo de conversa

1. O cliente autentica com Supabase Auth.
2. O cliente envia texto ou áudio para a API no Render com token de acesso.
3. A API valida a identidade e carrega histórico/memórias daquele usuário.
4. O orquestrador decide entre resposta normal, recuperação de conhecimento ou ferramenta do agente.
5. Resposta em texto é persistida no Supabase.
6. Se solicitado, Fish Audio gera áudio; o backend retorna ou transmite o resultado.
7. Operações locais no Windows só são executadas quando o cliente estiver online e com autorização explícita.

## Regras de segurança

- Nunca colocar chaves Gemini, Fish Audio, Supabase service-role ou credenciais de agentes no aplicativo desktop, no GitHub ou no Obsidian.
- Render recebe segredos pelas Environment Variables do serviço, configuradas no painel.
- Desktop usa somente a chave publicável do Supabase e o token individual de sessão.
- Todas as tabelas de dados pessoais usam Row Level Security (RLS) e políticas vinculadas a `auth.uid()`.
- Validar tamanho e tipo de uploads de áudio; limitar duração, tamanho, concorrência e tempo de execução.
- Ferramentas de shell, arquivos, navegador e controle do Windows exigem lista de permissões e confirmação antes de ações destrutivas.
- Não gravar áudio bruto por padrão. Permitir que o usuário habilite retenção explicitamente.
- Redigir tokens e dados pessoais dos logs.

## Disponibilidade e custo

O plano gratuito do Render pode suspender serviços por inatividade e tem limites de uso. Portanto, “cloud-first” não significa disponibilidade contínua garantida a custo zero. Para tarefas agendadas, é necessário usar um agendador persistente suportado ou um worker que permaneça ativo. Nunca simular que uma tarefa foi executada enquanto o serviço estava suspenso.

## Ordem de implementação

1. Configuração de deploy e health check.
2. Autenticação remota e armazenamento Supabase para conversas e memórias.
3. Adaptadores de STT cloud e Fish Audio TTS, com timeouts e limites.
4. Orquestrador e adaptadores isolados para Hermes/OpenJarvis.
5. Camada de pesquisa/sincronização do Obsidian.
6. Cliente Windows com streaming, cancelamento de áudio e estado de conexão.
7. Testes automatizados, migrações revisadas e checklist de deploy.

## Critério de pronto

Uma versão só deve ser considerada implantada quando o deploy real, migrações do Supabase, autenticação, persistência remota, chamadas de voz e testes de integração forem verificados. Criar arquivos de configuração não comprova que esses serviços estejam conectados.
