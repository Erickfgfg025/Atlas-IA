# ATLAS AI

Assistente pessoal para Windows 10/11 com Python, PySide6, FastAPI e Gemini via `google-genai`. O projeto oferece memória local SQLite e integração Supabase para memória e histórico em nuvem. O modo pessoal sem login é restrito ao backend local.

## Arquitetura atual
- `src/atlas/desktop/`: interface nativa, chat, controles de voz e diálogo para revisar/editar/excluir memórias.
- `src/atlas/backend/`: API, comando explícito para salvar memória e seleção de modo local ou Supabase.
- `src/atlas/providers/`: adaptadores Gemini, OpenJarvis, Hermes Agent, Gemini STT e Fish Audio TTS.
- `src/atlas/memory/`: armazenamento SQLite/Supabase e seleção determinística de memórias relevantes.
- `src/atlas/windows_agent/`: fronteira futura para ferramentas locais seguras.
- `supabase/migrations/`: migrações de memória e histórico com RLS, versionadas no GitHub; as tabelas `atlas_memories`, `atlas_conversations` e `atlas_conversation_messages` já foram criadas no projeto Supabase Atlas AI.
- `tests/`: testes sem credenciais externas.

## Memória
- O modo local usa SQLite no computador e não exige conta Supabase.
- Para salvar algo deliberadamente pelo chat, escreva: **“Lembre que meu projeto usa Python e SQLite.”** O ATLAS confirma o salvamento sem chamar o Gemini para esse comando.
- O botão **Memórias** permite listar, corrigir e excluir registros salvos.
- No chat normal, o backend seleciona até cinco memórias relacionadas à mensagem e as envia ao Gemini como dados de contexto.
- A extração é explícita, não automática: o ATLAS não guarda indiscriminadamente cada mensagem.
- A API implementa `GET /memories`, `POST /memories`, `PUT /memories/{id}` e `DELETE /memories/{id}`.

## Histórico de conversas
- O modo local grava conversas e mensagens no mesmo banco SQLite local, em tabelas separadas das memórias duradouras.
- O ATLAS inclui até 12 mensagens recentes no contexto do Gemini; cada mensagem histórica é limitada antes de compor o prompt.
- O ID da conversa ativa é guardado nas configurações locais do desktop para restaurar o histórico na próxima abertura.
- Use **Nova conversa** para começar outro assunto sem carregar as mensagens da conversa anterior.
- O histórico remoto no modo Supabase usa tabelas próprias e RLS por usuário. A migration `supabase/migrations/20261022000000_cloud_conversations.sql` precisa ser aplicada no projeto Supabase antes do uso em produção.
## Modos de operação
- **local (padrão):** memória SQLite no computador, sem conta Supabase. A API deve permanecer vinculada a `127.0.0.1`.
- **supabase (opcional):** autenticação Supabase e armazenamento remoto por usuário. Requer URL, chave publicável/anon e migrações aplicadas ao projeto escolhido.
- **supabase sem login (desktop pessoal):** a interface abre direto, sem e-mail/senha, e usa Supabase para memória e histórico. Requer `ATLAS_DESKTOP_NO_LOGIN=true`, `ATLAS_OWNER_USER_ID` (UUID do usuário dono) e `SUPABASE_SERVICE_ROLE_KEY` configurados somente no `.env` do backend. A API rejeita conexões não locais nesse modo e deve ser iniciada em `127.0.0.1`. A chave `service_role` ignora RLS: use somente no backend local privado, nunca em um deploy público ou no executável desktop.

## Instalação para desenvolvimento
Para desenvolver o projeto, use Python 3.11, 3.12 ou 3.13 e configure `GEMINI_API_KEY` no `.env`.

```powershell
git clone https://github.com/Erickfgfg025/Atlas-IA.git
cd Atlas-IA
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

## Instalação para clientes Windows
Clientes não devem clonar o repositório nem executar comandos. O workflow **Windows installer** empacota o aplicativo e produz `Atlas-AI-Setup-0.1.0-Windows.exe`. Baixe o instalador na GitHub Release oficial quando uma versão estiver publicada. O assistente instala o aplicativo, cria atalhos e permite abrir o Atlas AI diretamente. Na primeira execução, o cliente entra ou cria uma conta; a API hospedada e o Supabase cuidam da IA e dos dados sincronizados.

Documentação: [instalação do cliente](docs/INSTALACAO_CLIENTE.md) e [distribuição e segurança](docs/DISTRIBUICAO_CLIENTES.md).

Por padrão, `ATLAS_MEMORY_BACKEND=local`. O SQLite é criado automaticamente no diretório de dados do usuário. Para escolher outro caminho, defina `ATLAS_LOCAL_DB_PATH`. Não comite `.env`.

Para ativar o modo remoto com login, defina `ATLAS_MEMORY_BACKEND=supabase`, configure `SUPABASE_URL` e `SUPABASE_KEY` com a chave publicável/anon e habilite Email Auth. Nunca use a chave `service_role` no desktop.

Para o modo pessoal sem tela de login, execute ` .\\scripts\\configure_supabase_desktop.ps1` a partir da raiz do repositório depois de criar `.env`. O script configura a URL e a chave publicável do projeto Atlas AI, ativa `ATLAS_MEMORY_BACKEND=supabase`, `ATLAS_DESKTOP_NO_LOGIN=true` e `ATLAS_API_HOST=127.0.0.1`, e pede o UUID do usuário Supabase e a chave JWT legada `service_role` (entrada oculta). A chave administrativa fica somente no `.env` local do backend e ignora RLS. Por isso esse modo só funciona com o backend local e não deve ser usado no Render nem em qualquer backend público. As tabelas de memória e histórico já foram criadas no projeto Supabase Atlas AI. Reinicie o backend depois da configuração.

## Executar
Terminal 1:
```powershell
uvicorn atlas.backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:
```powershell
python -m atlas.desktop.app
```

## Testes
```powershell
pytest
ruff check .
```

## Segurança das rotas de voz

As rotas `POST /voice/transcribe` e `POST /voice/synthesize` agora falham de forma fechada se `ATLAS_MEMORY_BACKEND` tiver um valor inválido. O modo `local` continua sem autenticação remota; o modo `supabase` exige token Bearer validado. Isso evita que uma configuração desconhecida seja tratada silenciosamente como acesso local. Os testes correspondentes estão em `tests/test_voice_auth_config.py`.

## Diagnóstico de provedores

O endpoint público `GET /health` também informa, sem revelar valores secretos, se os provedores de chat, transcrição, síntese de voz e Hermes parecem configurados. O campo `diagnostics_note` é importante: isso é uma verificação de configuração, não um teste de conectividade, validade das chaves ou disponibilidade dos serviços externos. O status geral `ok` indica que a API respondeu, não que todas as integrações estejam funcionando.

## Limites atuais
- As migrações de memória e histórico foram aplicadas ao projeto Supabase Atlas AI e as três tabelas foram verificadas. O modo sem login ainda precisa ser configurado no `.env` do computador e validado com a chave administrativa.
- A recuperação de memórias usa sobreposição de termos, sem embeddings.
- O modo Supabase foi testado com mocks, não com um projeto real.
- A voz está parcialmente implementada: transcrição cloud de arquivos e gravação curta pelo microfone no desktop, além de reprodução TTS. A conversa contínua em tempo real e a automação autorizada do Windows ainda não estão implementadas.


## Arquitetura cloud-first (em implementação)

A direção do projeto agora é manter o núcleo do ATLAS na nuvem para que tarefas remotas continuem disponíveis com o PC desligado. O aplicativo Windows será o cliente de interface, microfone, reprodução de voz e automação local quando o computador estiver ligado.

- **Render:** API FastAPI; o blueprint inicial está em `render.yaml`.
- **Supabase:** autenticação e persistência remota de memórias, conversas e mensagens.
- **Fish Audio:** endpoint `POST /voice/synthesize` recebe JSON `{"text":"..."}` e retorna áudio MP3; a chave fica exclusivamente no backend.
- **STT cloud:** endpoint `POST /voice/transcribe` recebe um arquivo multipart `audio` e devolve `{"text":"transcrição"}` usando Gemini.
- **Hermes Agent / OpenJarvis:** ferramentas e modelos isolados por adaptadores.
- **Obsidian:** conhecimento em Markdown. Um vault guardado apenas no disco do PC não pode ser acessado quando o PC estiver desligado; é necessária sincronização cloud.

Documento de arquitetura e etapas: [docs/CLOUD_ARCHITECTURE.md](docs/CLOUD_ARCHITECTURE.md).

### Importante: estado real

A arquitetura cloud-first e o blueprint de Render foram registrados no repositório, mas isso **não significa que o serviço já foi implantado**. O código da API agora inclui um adaptador de histórico Supabase por usuário, além do armazenamento de memórias já existente. As migrações de memória e histórico foram aplicadas ao projeto Supabase Atlas AI; a configuração local e a integração remota ainda precisam ser validadas no computador. A voz está parcialmente implementada no código, mas ainda precisa de validação em ambiente real. O adaptador OpenJarvis foi adicionado para servidores compatíveis com a API OpenAI, mas ainda não foi validado contra uma instância real. A ponte inicial do Hermes Agent foi adicionada, mas não foi testada contra um checkout real nem implantada; a sincronização Obsidian também está pendente. O deploy requer configurar as variáveis secretas no Render e aplicar/revisar as migrações no projeto Supabase.

O plano gratuito do Render pode suspender o serviço por inatividade, então não há garantia de execução 24/7 sem limites. O backend pode executar tarefas cloud enquanto o PC estiver desligado, mas não pode acessar o microfone, alto-falantes ou controlar o próprio PC desligado.

### OpenJarvis: adaptador inicial

O backend pode selecionar o provedor OpenJarvis com `ATLAS_CHAT_PROVIDER=openjarvis`. Configure explicitamente `OPENJARVIS_BASE_URL` apontando para a base `/v1` de uma instância OpenJarvis acessível ao backend, `OPENJARVIS_MODEL` com um modelo servido e, se a instância exigir autenticação, `OPENJARVIS_API_KEY`. Não há endpoint local presumido por padrão: a instância precisa existir e ser alcançável pela API. O padrão continua sendo Gemini. O adaptador chama o endpoint compatível `/chat/completions`; ele não instala nem hospeda automaticamente o runtime OpenJarvis. A instância precisa existir separadamente e ser alcançável pela API.

### Hermes Agent: ponte de execução inicial

O endpoint `POST /agent/tasks` chama o Hermes por meio da classe `AIAgent` do checkout oficial. A integração é **opcional e desativada por padrão**: configure `HERMES_AGENT_ENABLED=true`, `HERMES_AGENT_PATH` para o checkout Hermes já preparado e `HERMES_AGENT_MODEL` para o modelo configurado nesse ambiente. As credenciais do provedor usado pelo Hermes devem ficar somente no ambiente do processo Hermes/backend.

A primeira versão habilita exclusivamente o toolset `web`; terminal, edição de arquivos, execução de código e controle de computador não são habilitados. Cada pedido deve incluir `approved: true` para registrar a confirmação explícita do usuário. Em modo Supabase, o endpoint exige token Bearer válido. Em modo local, mantenha a API vinculada a `127.0.0.1`.

A ponte executa cada tarefa Hermes em um processo filho separado com timeout, para que o processo da tarefa possa ser encerrado ao exceder o limite. O processo filho recebe apenas variáveis básicas de ambiente e uma lista permitida de chaves de provedores de modelo; chaves Supabase e Fish Audio não são encaminhadas. Isso reduz a exposição acidental de segredos, mas **não é um sandbox de segurança**: o processo compartilha o sistema operacional, permissões de usuário e acesso de rede do host. Mantenha o toolset restrito e não exponha o endpoint publicamente sem autenticação, limites de uso e isolamento de infraestrutura.

Este adaptador exige que o checkout Hermes e suas dependências estejam preparados separadamente conforme a documentação oficial. Ele não clona nem instala Hermes automaticamente no Render, e não comprova que o agente esteja operacional no ambiente de produção.

### Voz na nuvem: primeiro incremento

Foram adicionados os adaptadores de Fish Audio TTS e Gemini STT e as rotas de voz. Para ativar no Render, configure `FISH_AUDIO_API_KEY`, `FISH_AUDIO_REFERENCE_ID`, `GEMINI_API_KEY` e os dados do Supabase. O modelo/ID de voz depende de uma referência disponível na conta Fish Audio. Em modo Supabase, as rotas exigem sessão Bearer válida. O endpoint de transcrição aceita áudio até o limite definido em `ATLAS_MAX_AUDIO_UPLOAD_MB` (20 MB por padrão) e rejeita formatos não permitidos.

A alteração foi registrada no GitHub, mas não foi implantada nem executada contra serviços externos nesta etapa. A compatibilidade exata do ID de voz e as quotas do provedor precisam ser verificadas com as credenciais reais.


## Voz no aplicativo desktop
- **Transcrever arquivo de áudio:** seleciona um arquivo compatível, envia para `POST /voice/transcribe` e coloca a transcrição no campo de mensagem para revisão antes do envio.
- **Ouvir última resposta:** envia a resposta mais recente para `POST /voice/synthesize` e reproduz o MP3 no aplicativo.
- No desenvolvimento, o desktop usa `ATLAS_API_URL` se definida ou `http://127.0.0.1:8000`. No executável empacotado, o runtime hook aponta para `https://atlas-ai-api-a58n.onrender.com`. Não coloque chaves Gemini, Fish Audio ou Supabase no cliente.
- **Gravar pelo microfone:** grava até 60 segundos em WAV no desktop Windows, interrompe a gravação e envia o arquivo para transcrição cloud; o texto aparece no campo de mensagem para revisão antes do envio. O backend não mantém o áudio após a transcrição. A compatibilidade depende do dispositivo de entrada, das permissões do Windows e do backend Qt Multimedia disponível na máquina. Esta captura ainda não é uma conversa de voz contínua em tempo real.
- Para usar as rotas no Render, configure `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `FISH_AUDIO_API_KEY` e `FISH_AUDIO_REFERENCE_ID`, e aplique as migrations necessárias no Supabase. O aplicativo e a API ainda precisam ser testados e implantados no ambiente real.
