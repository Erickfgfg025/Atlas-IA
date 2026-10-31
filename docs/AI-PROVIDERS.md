# Provedores de IA

## Gemini
- Provedor remoto via Gemini API REST.
- Só pode ser chamado quando `EnableCloudRequests` estiver ativo e o provedor selecionado for Gemini.
- A chave é obtida por `ISecretStore` (Windows DPAPI no aplicativo desktop).
- A chave é enviada no cabeçalho `x-goog-api-key`, nunca na URL.
- O conteúdo enviado à nuvem pode conter prompt, instruções e histórico da conversa. Não enviar sem consentimento.

## Ollama
- Provedor local via `POST /api/chat`.
- O endpoint é validado para aceitar somente HTTP em endereço loopback.
- Modelo padrão: `llama3.2`; deve estar baixado no Ollama do usuário.
- A disponibilidade do modelo depende da instalação local e dos recursos da máquina.

## Limites atuais
- O roteador seleciona o provedor salvo nas preferências.
- Não existe fallback silencioso de Gemini para Ollama nem o inverso.
- A configuração de credenciais Gemini e a tela de conversa serão ligadas na próxima etapa.
- Os testes automatizados usam provedores simulados e não fazem chamadas externas.
