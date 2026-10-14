# ATLAS AI

Assistente pessoal para Windows 10/11. Base inicial em Python com PySide6, FastAPI, Gemini via SDK oficial `google-genai` e integração preparada para Supabase.

## Arquitetura inicial
- `src/atlas/desktop/`: interface PySide6, cliente HTTP da API.
- `src/atlas/backend/`: API FastAPI e configuração.
- `src/atlas/providers/`: adaptadores Gemini e Supabase.
- `src/atlas/memory/`: contrato tipado inicial de memória, sem persistência automática ainda.
- `src/atlas/windows_agent/`: fronteira reservada para ferramentas locais seguras; nada de shell arbitrário.
- `tests/`: testes sem credenciais externas.
- `docs/`: arquitetura, segurança, ADRs e próximo marco.

Fluxo: desktop → API local → Gemini. Supabase está preparado como adaptador, mas a persistência só será ativada após migrações, autenticação e RLS revisadas.

## Requisitos
Python 3.11, 3.12 ou 3.13. Windows 10/11 para validar a interface desktop.

## Instalar no PowerShell
```powershell
git clone https://github.com/Erickfgfg025/Atlas-IA.git
cd Atlas-IA
py -3.12 -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```
Edite `.env` localmente. Nunca faça commit desse arquivo.

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
Os testes unitários não precisam de chaves nem chamam serviços externos. Testes reais de Gemini/Supabase serão adicionados quando os contratos de integração estiverem definidos.

## Limites desta base
- Sem deploy ou migração remota.
- Sem automação autônoma do Windows, voz ou memória persistente de produção.
- Não exponha a API além de `127.0.0.1` nesta fase.
- Chaves Gemini/Supabase ficam apenas no ambiente do backend. Nunca embuta `service_role` em builds desktop.
