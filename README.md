# ATLAS AI

Assistente pessoal para Windows 10/11. Base em Python com PySide6, FastAPI, Gemini via SDK oficial `google-genai` e Supabase Auth.

## Arquitetura atual
- `src/atlas/desktop/`: interface PySide6 com cadastro, login, chat autenticado e logout.
- `src/atlas/backend/`: API FastAPI, configuração e autenticação.
- `src/atlas/providers/`: adaptadores Gemini e Supabase.
- `src/atlas/memory/`: contrato tipado inicial de memória; persistência ainda não conectada.
- `src/atlas/windows_agent/`: fronteira reservada para ferramentas locais seguras; nada de shell arbitrário.
- `supabase/migrations/`: migração versionada para memória com RLS, ainda não aplicada a um projeto real.
- `tests/`: testes sem credenciais externas.
- `docs/`: arquitetura, segurança, autenticação, ADRs e marcos seguintes.

Fluxo: desktop → API local → Supabase Auth para sessão e Gemini para respostas. O endpoint de chat exige token válido. A memória persistente e o agente local ainda não estão ativados.

## Requisitos
Python 3.11, 3.12 ou 3.13. Windows 10/11 para validar a interface desktop. É necessário um projeto Supabase configurado com Email Auth e uma chave Gemini para conversar com o modelo.

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

Edite `.env` localmente:
- `GEMINI_API_KEY`: sua chave da API Gemini.
- `SUPABASE_URL`: URL do projeto Supabase.
- `SUPABASE_KEY`: chave publicável/anon do projeto. **Nunca use `service_role` ou uma chave secreta.**

No Supabase, habilite Email Auth. Se a confirmação de e-mail estiver ativa, confirme o endereço antes de entrar. Não faça commit do `.env`.

## Executar
Terminal 1:
```powershell
uvicorn atlas.backend.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2:
```powershell
python -m atlas.desktop.app
```

Crie uma conta ou entre pela janela do ATLAS. O access token fica apenas na memória do processo e é apagado ao sair ou fechar o aplicativo. Não há login automático nesta versão.

## Testar
```powershell
pytest
ruff check .
```

Os testes unitários não precisam de chaves e não chamam serviços externos. O CI executa lint e testes automatizados; ainda é necessário fazer uma validação manual no Windows com as credenciais locais.

## Limites desta etapa
- Nenhum deploy ou migração remota foi executado.
- A migração `atlas_memories` está versionada, mas não aplicada ao projeto Supabase.
- Sem memória persistente funcional, voz ou automação autônoma do Windows.
- Não exponha a API além de `127.0.0.1` nesta fase.
- Nenhuma chave privilegiada deve ser embutida no desktop.
