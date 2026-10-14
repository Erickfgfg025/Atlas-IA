# ATLAS AI

Assistente pessoal para Windows 10/11 com Python, PySide6, FastAPI e Gemini via `google-genai`. O projeto começa com memória local SQLite; Supabase fica como opção futura de autenticação e armazenamento em nuvem.

## Arquitetura atual
- `src/atlas/desktop/`: interface nativa, chat e modo local sem cadastro remoto.
- `src/atlas/backend/`: API e seleção de modo local ou Supabase.
- `src/atlas/providers/`: adaptador Gemini.
- `src/atlas/memory/`: contrato de memória, SQLite local e repositório Supabase.
- `src/atlas/windows_agent/`: fronteira futura para ferramentas locais seguras; sem shell arbitrário.
- `supabase/migrations/`: migração de memória com RLS, versionada para uso futuro e ainda não aplicada a um projeto real.
- `tests/`: testes sem credenciais externas.
- `docs/`: arquitetura, segurança, autenticação e memória.

## Modos de operação
- **local (padrão):** memória SQLite no computador, sem conta Supabase. A API deve permanecer vinculada a `127.0.0.1`.
- **supabase (futuro/opcional):** autenticação Supabase e armazenamento remoto com RLS. Requer URL, chave publicável/anon e a migração aplicada ao projeto escolhido.

A API implementa `GET /memories`, `POST /memories` e `DELETE /memories/{id}`. A recuperação automática de memórias no contexto do Gemini ainda não está ativada.

## Requisitos
Python 3.11, 3.12 ou 3.13. Windows 10/11 para validar a interface. Para conversar, é necessário configurar `GEMINI_API_KEY`.

## Instalar no PowerShell
```powershell
git clone https://github.com/Erickfgfg025/Atlas-IA.git
cd Atlas-IA
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Configure `GEMINI_API_KEY` em `.env`. Por padrão, `ATLAS_MEMORY_BACKEND=local`. O arquivo SQLite é criado automaticamente no diretório de dados do usuário. Para escolher outro local, defina `ATLAS_LOCAL_DB_PATH`. Não comite `.env`.

Para ativar o modo remoto posteriormente, defina `ATLAS_MEMORY_BACKEND=supabase`, configure `SUPABASE_URL` e `SUPABASE_KEY` com a chave publicável/anon e habilite Email Auth. Nunca use `service_role` ou chave secreta no desktop.

## Executar
Terminal 1:
```powershell
uvicorn atlas.backend.main:app --reload --host 127.0.0.1 --port 8000
```
Terminal 2:
```powershell
python -m atlas.desktop.app
```

## Testar
```powershell
pytest
ruff check .
```

## Limites atuais
- Nenhum deploy ou migração remota foi executado.
- A memória local persiste em SQLite; ainda não é recuperada automaticamente pelo Gemini.
- Modo Supabase está mantido como caminho opcional, mas não foi validado com um projeto real nesta etapa.
- Sem voz ou automação autônoma do Windows.
- Não exponha a API além de `127.0.0.1` nesta fase.
