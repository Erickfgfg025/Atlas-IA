# ATLAS AI

Assistente pessoal para Windows 10/11 com Python, PySide6, FastAPI e Gemini via `google-genai`. O projeto começa com memória local SQLite; Supabase fica como opção futura de autenticação e armazenamento em nuvem.

## Arquitetura atual
- `src/atlas/desktop/`: interface nativa, chat, controles de voz e diálogo para revisar/editar/excluir memórias.
- `src/atlas/backend/`: API, comando explícito para salvar memória e seleção de modo local ou Supabase.
- `src/atlas/providers/`: adaptadores Gemini, Gemini STT e Fish Audio TTS.
- `src/atlas/memory/`: armazenamento SQLite/Supabase e seleção determinística de memórias relevantes.
- `src/atlas/windows_agent/`: fronteira futura para ferramentas locais seguras.
- `supabase/migrations/`: migração de memória com RLS, versionada para uso futuro e ainda não aplicada a um projeto real.
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
- **supabase (opcional):** autenticação Supabase e armazenamento remoto com RLS. Requer URL, chave publicável/anon e migração aplicada ao projeto escolhido.

## Instalação no PowerShell
Python 3.11, 3.12 ou 3.13. Para conversar, configure `GEMINI_API_KEY` em `.env`.

```powershell
git clone https://github.com/Erickfgfg025/Atlas-IA.git
cd Atlas-IA
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Por padrão, `ATLAS_MEMORY_BACKEND=local`. O SQLite é criado automaticamente no diretório de dados do usuário. Para escolher outro caminho, defina `ATLAS_LOCAL_DB_PATH`. Não comite `.env`.

Para ativar o modo remoto posteriormente, defina `ATLAS_MEMORY_BACKEND=supabase`, configure `SUPABASE_URL` e `SUPABASE_KEY` com a chave publicável/anon e habilite Email Auth. Nunca use a chave `service_role` no desktop.

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

## Limites atuais
- Nenhum deploy ou migração remota foi executado.
- A recuperação de memórias usa sobreposição de termos, sem embeddings.
- O modo Supabase foi testado com mocks, não com um projeto real.
- Voz e automação do Windows ainda não foram implementadas.


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

A arquitetura cloud-first e o blueprint de Render foram registrados no repositório, mas isso **não significa que o serviço já foi implantado**. O código da API agora inclui um adaptador de histórico Supabase por usuário, além do armazenamento de memórias já existente. A migration precisa ser aplicada e a integração remota precisa ser validada no projeto real. Pipeline de voz, integração com agentes e sincronização Obsidian ainda precisam ser implementados e verificados. O deploy requer configurar as variáveis secretas no Render e aplicar/revisar as migrações no projeto Supabase.

O plano gratuito do Render pode suspender o serviço por inatividade, então não há garantia de execução 24/7 sem limites. O backend pode executar tarefas cloud enquanto o PC estiver desligado, mas não pode acessar o microfone, alto-falantes ou controlar o próprio PC desligado.

### Voz na nuvem: primeiro incremento

Foram adicionados os adaptadores de Fish Audio TTS e Gemini STT e as rotas de voz. Para ativar no Render, configure `FISH_AUDIO_API_KEY`, `FISH_AUDIO_REFERENCE_ID`, `GEMINI_API_KEY` e os dados do Supabase. O modelo/ID de voz depende de uma referência disponível na conta Fish Audio. Em modo Supabase, as rotas exigem sessão Bearer válida. O endpoint de transcrição aceita áudio até o limite definido em `ATLAS_MAX_AUDIO_UPLOAD_MB` (20 MB por padrão) e rejeita formatos não permitidos.

A alteração foi registrada no GitHub, mas não foi implantada nem executada contra serviços externos nesta etapa. A compatibilidade exata do ID de voz e as quotas do provedor precisam ser verificadas com as credenciais reais.


## Voz no aplicativo desktop
- **Transcrever arquivo de áudio:** seleciona um arquivo compatível, envia para `POST /voice/transcribe` e coloca a transcrição no campo de mensagem para revisão antes do envio.
- **Ouvir última resposta:** envia a resposta mais recente para `POST /voice/synthesize` e reproduz o MP3 no aplicativo.
- O desktop usa `ATLAS_API_URL` para apontar para a API implantada; sem essa variável, usa `http://127.0.0.1:8000`. Defina essa variável no ambiente do Windows para usar o backend do Render. Não coloque chaves Gemini, Fish Audio ou Supabase no cliente.
- A interface ainda não grava diretamente do microfone; este incremento faz transcrição de arquivos e reprodução de respostas. A gravação contínua e o modo de conversa por voz em tempo real ficam para uma etapa posterior.
- Para usar as rotas no Render, configure `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`, `FISH_AUDIO_API_KEY` e `FISH_AUDIO_REFERENCE_ID`, e aplique as migrations necessárias no Supabase. O aplicativo e a API ainda precisam ser testados e implantados no ambiente real.
