# ATLAS AI

Assistente pessoal para Windows 10/11 com Python, PySide6, FastAPI, Gemini via `google-genai` e Supabase Auth.

## Arquitetura atual
- `src/atlas/desktop/`: interface com cadastro, login, chat autenticado e logout.
- `src/atlas/backend/`: API, configuração e autenticação.
- `src/atlas/providers/`: adaptadores Gemini e Supabase.
- `src/atlas/memory/`: contratos e repositório Supabase usando o token do usuário.
- `src/atlas/windows_agent/`: fronteira futura para ferramentas locais seguras; sem shell arbitrário.
- `supabase/migrations/`: migração de memória com RLS, ainda não aplicada a um projeto real.
- `tests/`: testes sem credenciais externas.
- `docs/`: arquitetura, segurança, autenticação e memória.

A API implementa `GET /memories`, `POST /memories` e `DELETE /memories/{id}`. A persistência real depende de aplicar a migração ao projeto Supabase correto. A recuperação automática de memórias no contexto do Gemini ainda não está ativada.

## Requisitos
Python 3.11, 3.12 ou 3.13. Windows 10/11 para validar a interface. Para conversar, é necessário um projeto Supabase com Email Auth e uma chave Gemini.

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

Configure localmente `GEMINI_API_KEY`, `SUPABASE_URL` e `SUPABASE_KEY`. Use a chave publicável/anon do Supabase, nunca `service_role` ou chave secreta. Não comite `.env`. Habilite Email Auth e confirme o endereço se o projeto exigir.

## Executar
Terminal 1:
```powershell
uvicorn atlas.backend.main:app --reload --host 127.0.0.1 --port 8000
```
Terminal 2:
```powershell
python -m atlas.desktop.app
```

O access token fica apenas na memória do processo. Não há login automático nesta versão.

## Testar
```powershell
pytest
ruff check .
```

Testes simulados verificam autenticação e uso do token/ID correto para operações de memória. Depois de aplicar a migração, valide a integração real com duas contas de teste.

## Limites
- Nenhum deploy ou migração remota foi executado.
- A memória ainda não está disponível até aplicar a migração e verificar o projeto.
- Memórias ainda não são recuperadas automaticamente pelo Gemini.
- Sem voz ou automação autônoma do Windows.
- Não exponha a API além de `127.0.0.1` nesta fase.