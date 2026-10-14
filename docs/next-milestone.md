# Próximo marco: primeira conversa ponta a ponta

## Validação automatizada

- [x] Backend inicia no ambiente de CI e `/health` responde.
- [x] `/chat` rejeita mensagem vazia.
- [x] Caminho de chat testado com provedor simulado, sem consumir API paga.
- [x] Erro de configuração retorna 503.
- [x] Erros internos do provedor não são expostos ao cliente.
- [x] A interface executa chamadas de chat em uma thread separada.
- [x] Texto do usuário e do modelo é escapado antes de ser renderizado como HTML.
- [ ] Confirmar no Windows que a janela PySide6 abre e permanece responsiva.
- [ ] Testar uma conversa real com `GEMINI_API_KEY` válida.
- [ ] Confirmar a configuração local de Supabase; persistência ainda não está implementada.
- [ ] Revisar migrações e RLS antes de armazenar dados reais.

## Smoke test manual no Windows

1. Crie e ative o ambiente virtual conforme o README.
2. Copie `.env.example` para `.env` e configure `GEMINI_API_KEY`.
3. Em um terminal, execute `uvicorn atlas.backend.main:app --host 127.0.0.1 --port 8000`.
4. Em outro terminal, execute `python -m atlas.desktop.app`.
5. Confirme o status da API, envie uma mensagem e verifique a resposta.
6. Enquanto aguarda a resposta, redimensione a janela e mova-a para confirmar que a interface continua responsiva.
7. Envie texto contendo `<script>alert(1)</script>`; ele deve aparecer como texto literal, sem ser executado.

A validação automatizada usa um provedor simulado. Ela não substitui o teste manual com credenciais reais nem comprova o funcionamento do SDK Gemini, do Supabase ou da interface neste ambiente.
