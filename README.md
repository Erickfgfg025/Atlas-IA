# ATLAS AI

Assistente pessoal para Windows 10/11 com Python, PySide6, FastAPI e Gemini via `google-genai`. O projeto começa com memória local SQLite; Supabase fica como opção futura de autenticação e armazenamento em nuvem.

## Arquitetura atual
- `src/atlas/desktop/`: interface nativa, chat e diálogo para revisar/editar/excluir memórias.
- `src/atlas/backend/`: API, comando explícito para salvar memória e seleção de modo local ou Supabase.
- `src/atlas/providers/`: adaptador Gemini.
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
- A recuperação usa sobreposição de termos, sem embeddings.
- O modo Supabase foi testado com mocks, não com um projeto real.
- Voz e automação do Windows ainda não foram implementadas.
