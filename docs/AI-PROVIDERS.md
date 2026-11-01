# Provedores de IA

## Gemini
- Provedor remoto via Gemini API REST.
- Só pode ser chamado quando `EnableCloudRequests` estiver ativo e o provedor selecionado for Gemini.
- A chave é cadastrada pela interface e armazenada por `ISecretStore` usando Windows DPAPI (`CurrentUser`).
- A chave é enviada no cabeçalho `x-goog-api-key`, nunca na URL.
- Prompt e histórico da conversa são enviados ao Google. A opção de nuvem começa desativada.

## Ollama
- Provedor local via `POST /api/chat`.
- O endpoint padrão é `http://127.0.0.1:11434/`; a validação de configuração só permite HTTP em loopback.
- Modelo padrão: `llama3.2`; o modelo precisa estar baixado no Ollama do usuário.
- A disponibilidade depende da instalação local e dos recursos da máquina.

## Roteamento e privacidade
- O roteador seleciona exclusivamente o provedor salvo nas preferências.
- Não existe fallback silencioso de Gemini para Ollama nem o inverso.
- O Gemini é bloqueado se a permissão de nuvem estiver desativada.
- Os testes automatizados usam provedores HTTP simulados e não fazem chamadas externas.
- A configuração de endpoint/modelo Ollama pela interface, timeout configurável e gestão de histórico persistente ainda não fazem parte desta etapa.
