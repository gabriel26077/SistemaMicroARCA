# Operação do catálogo estático

**Estado atual: publicação bloqueada por DNS ausente.** Nenhuma mudança foi feita
na VPS. O snippet `Caddyfile.microarca` é preparação local, não configuração ativa.
O provisionamento exige uma única confirmação após diff exato e backups, conforme
`IA_SPEC.md`. Deploy de arquivos e provisionamento de infraestrutura são separados.

## DNS

Inspeção em 2026-09-23 01:13 UTC (22/09, 22:13 em São Paulo): consultas A e AAAA
sem resposta para `libs.microarca.traceedu.com.br`. A VPS informa IPv4 público
`2.25.196.49` e IPv6 `2a02:4780:75:e43::1`.

Criar no provedor DNS da zona `traceedu.com.br`:

| Tipo | Nome | Valor | TTL sugerido |
| --- | --- | --- | --- |
| A | libs.microarca | 2.25.196.49 | 300 |

Não é necessário criar AAAA. Só o criar se o IPv6 da VPS estiver validado para
HTTPS; qualquer A/AAAA errado pode provocar falha de certificado. Não alterar
registros dos hosts existentes. O agente não modifica o provedor DNS.

```bash
ssh vps 'dig +short libs.microarca.traceedu.com.br A'
ssh vps 'dig +short libs.microarca.traceedu.com.br AAAA'
bash scripts/deploy.sh --dry-run
```

Sem DNS correto, não aplicar o host ao Caddy, não solicitar certificado e não
iniciar publicação incompleta.

## Preparação antes da confirmação

Repetir recursos, `docker inspect` (estado, RestartCount, StartedAt), requisições
HTTPS e leitura dos arquivos atuais. Os containers observados não definem
healthcheck Docker; `running` e HTTP são evidências distintas, não prova de todos
os componentes internos. Guardar a evidência de StartedAt para comparação final.

Arquivos relevantes:

- `/var/www/TraceEdu/docker-compose.yml` — ler, sem alteração.
- `/var/www/TraceEdu/docker-compose.prod.yml` — adicionar só a montagem no Caddy.
- `/var/www/TraceEdu/Caddyfile.domains` — acrescentar só o snippet do catálogo.
- `/var/www/TraceEdu-dev/docker-compose.staging.yml` — ler, sem alteração.

Menor mudança de Compose, no serviço `caddy`, sob `volumes`:

O [diff proposto](proposed-infrastructure.patch) foi gerado em memória a partir
dos arquivos reais da VPS e salvo apenas neste repositório. Deve ser refeito se a
configuração mudar. Não foi aplicado e não substitui backups ou aprovação.

```yaml
      - /var/www/MicroARCA-libs:/srv/microarca-libs:ro
```

Montar o **diretório pai**, mantendo os symlinks relativos dentro dele. Montar
diretamente `current` impediria que a troca de release fosse refletida corretamente.
Não ativar `file_server browse`. O snippet mantém catálogo com `no-cache`, arquivos
com `public, max-age=31536000, immutable`, CORS e `nosniff`.

Antes de editar, criar backups com timestamp de Caddyfile.domains e
docker-compose.prod.yml usando `cp -a`, registrar SHA-256 dos originais/backups e
gerar o diff contra os arquivos lidos novamente. Exemplo **para a fase aprovada de
preparação**, não executado nesta implementação:

```bash
ssh vps 'stamp=$(date -u +%Y%m%dT%H%M%SZ); cp -a /var/www/TraceEdu/Caddyfile.domains /var/www/TraceEdu/Caddyfile.domains.bak-$stamp; cp -a /var/www/TraceEdu/docker-compose.prod.yml /var/www/TraceEdu/docker-compose.prod.yml.bak-$stamp'
```

Mostrar o diff exato e caminhos dos backups; pedir **uma confirmação** para aplicar
essas alterações e recriar somente Caddy. Não pedir confirmação genérica antes
de preparar o resultado revisável. Se arquivos mudaram, recalcular o diff.

## Após autorização e DNS correto

1. Criar apenas `/var/www/MicroARCA-libs` e seus subdiretórios `releases/`, com
   permissões de leitura para Caddy. Não alterar donos/permissões do TraceEdu.
2. Preparar o primeiro release completo antes de habilitar o host usando
   `bash scripts/deploy.sh --bootstrap`. Esse modo exige DNS correto, testes,
   integridade e árvore limpa como o deploy normal, mas adia a verificação HTTPS
   até o Caddy estar configurado. Não usar como substituto do deploy normal.
3. Aplicar os dois diffs aprovados. Validar o Caddyfile **completo** antes de reload
   ou recreate. A montagem individual de Caddyfile é read-only: manter seu inode
   quando atualizar ou recriar Caddy para obter a nova montagem; evitar assumir que
   um rename no host atualiza um bind mount de arquivo já aberto.

```bash
ssh vps 'docker exec traceedu-caddy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile'
ssh vps 'cd /var/www/TraceEdu && CADDY_CONFIG_FILE=Caddyfile.domains docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet'
```

Se o arquivo montado não refletir a proposta (por troca de inode), validar a
proposta completa em container temporário da **mesma imagem local**, sem publicar
portas e com config/diretório da proposta montados read-only; só então recriar Caddy.
Não iniciar esse container como servidor; executar somente `caddy validate`.

4. A primeira montagem nova exige recriar apenas Caddy. Confirmar os mesmos
   parâmetros de projeto/arquivos Compose dos labels do container existente.

```bash
ssh vps 'cd /var/www/TraceEdu && CADDY_CONFIG_FILE=Caddyfile.domains docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --force-recreate caddy'
```

Em futuras mudanças apenas de configuração, usar `caddy reload` após validação.
Deploy normal de bibliotecas só troca `current`, sem reload/recreate.

## Verificação final

```bash
python3 scripts/verify_public.py
ssh vps 'docker logs --since 10m traceedu-caddy'
```

O verificador exige HTTPS válido, HTTP 200, igualdade do catálogo com dist local,
headers de cache/CORS/nosniff, todos os downloads, tamanhos e SHA-256, incluindo
licenças/proveniência. Inspecionar logs sem compartilhar tokens/dados sensíveis.

Repetir requisições a `traceedu.cloud`, `traceedu.com.br`, `www.traceedu.com.br`,
`app.traceedu.com.br` e `staging.traceedu.com.br`; redirecionamento 301 do `www`
é esperado. Comparar IDs/StartedAt de todos os containers: backend/frontend/bancos
devem ser idênticos aos anteriores. Confirmar recursos e ausência de erros no Caddy.

Não executar `compose down`, prune, reiniciar backend/frontend/PostgreSQL,
alterar banco, firewall, redes, swap ou instalar outro proxy. Produção e staging
compartilham `traceedu-net`; esse fato e ausência de swap ficam só documentados.

Veja [rollback.md](rollback.md) e [o relatório](../docs/implementation-status.md).
