# Arquitetura

Fluxo padrão: PySide6 desktop → FastAPI local → memória SQLite → seleção de memórias relevantes → Gemini. Supabase permanece como opção futura de armazenamento remoto.

- Desktop não importa SDKs Gemini ou Supabase.
- O backend mantém as credenciais do provedor Gemini.
- `ATLAS_MEMORY_BACKEND=local` é o padrão e dispensa conta remota.
- `ATLAS_LOCAL_DB_PATH` pode apontar para um arquivo SQLite específico; vazio usa o diretório de dados do usuário.
- `GET /memories`, `POST /memories`, `PUT /memories/{id}` e `DELETE /memories/{id}` permitem gerenciar registros.
- O botão Memórias usa uma janela separada e operações de rede em QThread para não congelar a interface.
- O comando explícito “Lembre que ...” grava uma memória sem chamar o Gemini. Não há captura automática de todas as conversas.
- Antes do chat normal, o backend busca até 100 registros e seleciona no máximo cinco por sobreposição de termos.
- As memórias são serializadas como JSON e identificadas no prompt como dados não confiáveis, nunca como instruções.
- O conteúdo de cada memória enviado ao Gemini é limitado a 1.500 caracteres.
- Em modo Supabase, a API exige sessão validada e o repositório usa a chave publicável/anon mais o token do usuário para preservar RLS.
- O ID do usuário remoto vem da identidade validada, nunca do corpo da requisição.
- O agente Windows permanece desativado.

## Sequência

1. Base de interface e chat: implementada; validação manual no Windows pendente.
2. Memória local SQLite e modo local-first: implementados.
3. Recuperação de memórias no contexto do Gemini: implementada com seleção lexical.
4. Salvamento explícito e gerenciamento pela interface: implementados nesta alteração; CI e validação manual pendentes.
5. Validar manualmente no Windows e confirmar persistência após reinício.
6. Planejar migração para Supabase quando houver projeto disponível.
7. Implementar armazenamento seguro/renovação de sessão no Windows.
8. Planejar protocolo autenticado para ferramentas locais do Windows.
