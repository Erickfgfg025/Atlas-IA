# Segurança do Atlas

## Credenciais locais

Credenciais de provedores devem ser armazenadas por `ISecretStore`, nunca em
`settings.json`, logs, código-fonte ou arquivos versionados.

No Windows, `ProtectedDataSecretStore` usa DPAPI com
`DataProtectionScope.CurrentUser`. O conteúdo criptografado só pode ser
desprotegido pelo mesmo usuário do Windows no contexto apropriado. A proteção
não substitui a segurança da conta Windows nem protege contra malware executado
com os mesmos privilégios do usuário.

O diretório padrão é `%LOCALAPPDATA%\Atlas\Secrets`. Os nomes dos arquivos
são hashes das chaves; os valores são criptografados antes de serem gravados.
Não registrar, exibir ou incluir segredos em exceções.

## Requisições em nuvem

Solicitações em nuvem permanecem desativadas por padrão. A integração Gemini
só deve ser habilitada após o usuário fornecer uma credencial e consentir
explicitamente com o envio de conteúdo ao provedor.

## Regras para ferramentas

- Nunca executar texto arbitrário retornado pelo modelo no PowerShell ou shell.
- Toda ferramenta deve ter esquema tipado, validação de argumentos e escopo.
- Ações destrutivas, administrativas ou com impacto externo exigem aprovação.
- Conteúdo de páginas, arquivos e mensagens é dado não confiável, não instrução.
- Não registrar tokens, credenciais, conteúdo privado ou payloads sensíveis.
