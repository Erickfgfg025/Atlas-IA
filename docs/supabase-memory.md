# Supabase: memória persistente

## Estado atual

A migração está em `supabase/migrations/202610140001_create_atlas_memories.sql`. Os endpoints de leitura, criação e exclusão foram implementados, mas **a migração ainda não foi aplicada a nenhum projeto Supabase**. A persistência real depende de confirmar o projeto e aplicar a migração.

## Modelo de dados

- `id`: UUID gerado no banco.
- `user_id`: usuário de `auth.users`; exclusão em cascata.
- `kind`: session, episodic, semantic, project ou operational.
- `content`: até 12.000 caracteres.
- `source` e `scope`: até 200 caracteres cada.
- `confidence`: número entre 0 e 1.
- `created_at`: timestamp do banco.

## Endpoints implementados

Todos exigem `Authorization: Bearer <access_token>` válido:

- `GET /memories?limit=50`: lista até 100 memórias do usuário autenticado.
- `POST /memories`: cria uma memória.
- `DELETE /memories/{id}`: exclui uma memória própria; retorna 404 quando não há linha acessível com aquele ID.

O backend valida a sessão via Supabase Auth. Depois chama a Data API com a chave publicável/anon e o access token do usuário, sem `service_role`. O `user_id` é derivado da identidade validada, nunca do corpo da requisição. Consultas também filtram pelo usuário; RLS continua sendo a barreira principal.

## Segurança e limitações

1. A migração habilita RLS e exige `auth.uid() = user_id`.
2. `anon` não recebe permissões de tabela.
3. Se a migração não estiver aplicada ou a tabela não estiver exposta à Data API, os endpoints retornam erro de serviço indisponível.
4. Os testes usam HTTPX MockTransport. Eles não substituem integração real com o Supabase.
5. A recuperação automática de memórias no contexto do Gemini ainda não está implementada.

## Aplicar a migração quando o projeto correto estiver confirmado

```powershell
supabase login
supabase link --project-ref SEU_PROJECT_REF
supabase db push
```

Confira o destino antes de executar `db push`. Nenhuma migração remota foi executada por este repositório.

## Próxima implementação

1. Confirmar e aplicar a migração ao projeto correto.
2. Testar com duas contas que não haja leitura, criação ou exclusão cruzada.
3. Integrar recuperação limitada ao contexto do Gemini.
4. Adicionar controles para listar e apagar memórias na interface.

Busca semântica/embeddings fica para depois de validar isolamento e operações básicas.