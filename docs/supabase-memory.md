# Supabase: fundação da memória persistente

## Estado

A migração inicial está em `supabase/migrations/202610140001_create_atlas_memories.sql`. Ela define a tabela e as políticas de segurança, mas **não foi aplicada a nenhum projeto Supabase** e o backend ainda não lê nem grava memórias.

## Modelo de dados

- `id`: identificador UUID gerado no banco.
- `user_id`: usuário autenticado em `auth.users`; exclusão em cascata.
- `kind`: session, episodic, semantic, project ou operational.
- `content`: conteúdo limitado a 12.000 caracteres.
- `source`: origem limitada a 200 caracteres.
- `scope`: escopo descritivo limitado a 200 caracteres.
- `confidence`: valor entre 0 e 1.
- `created_at`: timestamp definido pelo banco.

Índices atendem listagens recentes por usuário e por categoria.

## Segurança

1. RLS está habilitado na tabela.
2. As políticas de leitura, criação, atualização e exclusão exigem que `auth.uid() = user_id`.
3. O papel `anon` não recebe permissões de tabela.
4. A chave `service_role` ignora RLS e nunca deve ser enviada à interface desktop.
5. O backend ainda precisa de um fluxo de autenticação para obter a identidade verificada do usuário. Não aceite `user_id` arbitrário vindo do corpo da requisição.
6. Não conecte a memória ao endpoint de chat antes de estabelecer esse fluxo.

## Aplicar a migração, quando o projeto correto estiver confirmado

Com Supabase CLI instalado e autenticado:

```powershell
supabase login
supabase link --project-ref SEU_PROJECT_REF
supabase db push
```

Substitua o marcador pelo identificador do projeto pretendido. Confira o destino antes de executar `db push`. Esta etapa não foi executada por este repositório.

## Próxima implementação

1. Decidir o modelo de autenticação desktop: Supabase Auth com sessão de usuário é a opção preferida.
2. Validar tokens no backend e derivar o ID do usuário a partir da identidade verificada.
3. Implementar um repositório de memória que receba um cliente autenticado, sem credenciais privilegiadas na interface.
4. Adicionar testes com cliente/banco simulado e teste de isolamento entre dois usuários.
5. Só então integrar recuperação de memórias ao contexto do Gemini, com limite de quantidade e controle do que pode ser salvo.

Não há busca semântica/embeddings nesta etapa. Primeiro garantir isolamento e operações básicas; depois avaliar recuperação semântica.
