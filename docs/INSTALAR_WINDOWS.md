# ATLAS AI para Windows

O fluxo de build do GitHub Actions empacota a interface, a API local e um inicializador de um clique em executáveis Windows.

## Baixar o aplicativo

1. Abra a aba **Actions** do repositório.
2. Entre na execução mais recente de **Windows Desktop Build** que terminou com sucesso.
3. Na seção **Artifacts**, baixe **ATLAS-AI-Windows**.
4. Extraia o ZIP inteiro para uma pasta de sua preferência. Não separe os três arquivos EXE.

## Primeira abertura

Execute `ATLAS AI.exe`. Na primeira execução, o inicializador solicita a chave da API Gemini e salva a configuração em `.env` na pasta do aplicativo. A chave não é enviada ao repositório.

A chave Gemini é necessária para respostas de IA. O aplicativo usa SQLite local para memória e histórico no modo padrão. A API fica vinculada a `127.0.0.1`, não à rede pública.

## Diagnóstico

Se a API não iniciar, consulte `logs/api.log`. Verifique se a porta local 8000 já está ocupada. O inicializador espera a rota `/health` responder antes de abrir a interface.

## Atualizações e limitações

O artefato de build fica disponível por 14 dias. Cada novo build pode gerar um pacote atualizado. O fluxo atual gera um pacote portátil, não um instalador MSI/Setup; a criação de atalhos permanentes e a desinstalação formal são etapas futuras.

O executável deve ser construído e validado pelo Windows GitHub Actions. Não considere o pacote pronto até que a execução do workflow termine com sucesso.
