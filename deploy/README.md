# Operação do catálogo estático

**Publicado: `https://libs-microarca.traceedu.com.br/v1/catalog.json`, via Cloudflare.**
O usuário criou um CNAME para `traceedu.com.br` e aprovou o diff de Caddy/Compose.
Release atual: `4f7454ef3afa48f0414d0184379d8a442703af1f`, incluindo `microarca-teste`.
O primeiro provisionamento recriou somente Caddy; a publicação seguinte manteve
os sete containers sem reinícios. [Medição de publicação](../docs/catalog-latency-test.md).
O provisionamento inicial recebeu a confirmação exigida após diff exato e backups.
Deploy normal de arquivos não altera infraestrutura. As instruções abaixo também
servem para uma futura reinstalação; não reaplicar o diff sobre a configuração ativa.

## DNS

O hostname foi alterado pelo usuário para usar um único nível de subdomínio,
coberto pelo Universal SSL da Cloudflare. Configuração informada na zona
`traceedu.com.br`:

| Tipo | Nome | Valor | TTL |
| --- | --- | --- | --- |
| CNAME | libs-microarca | traceedu.com.br | Automático |

Inspeção em 2026-09-23 02:24 UTC: o novo nome e `traceedu.com.br` resolvem para
`104.21.74.162`, `172.67.204.66` e IPv6 da Cloudflare, indicando proxy ativo.
O IPv4 da VPS continua `2.25.196.49`; não deve ser confundido com os IPs do proxy.
A resposta pública inicial foi HTTP 525; após habilitar o host no Caddy e emitir
o certificado Let’s Encrypt, passou a HTTP 200. Não alterar DNS dos hosts existentes.

```bash
ssh vps 'dig +short libs-microarca.traceedu.com.br A'
ssh vps 'dig +short libs-microarca.traceedu.com.br AAAA'
bash scripts/deploy.sh --dry-run --cloudflare
```

O modo padrão de deploy continua exigindo DNS direto para a VPS. Para o CNAME
aprovado, usar `--cloudflare`: exige que o nome resolva para os mesmos endereços
de `traceedu.com.br`, todos dentro das redes oficiais publicadas pela Cloudflare
via HTTPS. Isso valida o proxy, mas não comprova a configuração de origem.
Depois da ativação, a verificação HTTPS deve comprovar o catálogo e os bytes
exatos dos arquivos. Não aceitar DNS ausente, IPs inesperados ou ignorar falhas.

Usar SSL/TLS Full (strict) na Cloudflare para HTTPS também até a origem; não
alterar o modo da zona inteira sem avaliar o impacto nos hosts TraceEdu. Caddy
obtém o certificado público do novo hostname por ACME. Se houver regras de WAF
ou redirects interferindo no desafio HTTP, diagnosticar sem desligar proteções
da zona inteira. O catálogo precisa chegar ao app com `Cache-Control: no-cache`.

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
dos arquivos reais da VPS e aplicado após aprovação. Ele representa a diferença
exata em relação aos backups registrados, não um patch a reaplicar.

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

Preparação executada em 23/09/2026: backups com sufixo
`.bak-microarca-20260923T023344651705Z` nos dois arquivos. Hashes de originais,
backups e propostas estão em [approval-evidence.json](approval-evidence.json).
A configuração completa proposta passou por `caddy validate` via stdin, sem
carregar os servidores. Após confirmação, os dois arquivos foram atualizados com
os hashes aprovados e somente Caddy foi recriado. Evidências finais em
[publication-evidence.json](publication-evidence.json).

## Após autorização e DNS correto

1. Criar apenas `/var/www/MicroARCA-libs` e seus subdiretórios `releases/`, com
   permissões de leitura para Caddy. Não alterar donos/permissões do TraceEdu.
2. Preparar o primeiro release completo antes de habilitar o host usando
   `bash scripts/deploy.sh --bootstrap --cloudflare`. Esse modo exige DNS correto, testes,
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

O verificador usa `User-Agent: MicroARCA-RegistryVerifier/1.0`. A identificação
genérica do urllib recebeu HTTP 403/erro Cloudflare 1010; a identificação explícita
do cliente foi aceita. Nenhuma configuração de segurança da Cloudflare foi alterada.
O app deve usar seu identificador próprio, conforme o contrato do cliente.

Na primeira emissão, o desafio ACME TLS-ALPN falhou através do proxy e o Caddy
obteve automaticamente o certificado via HTTP-01. Não houve erro novo nos dois
minutos anteriores à verificação final. O certificado da origem também foi
validado diretamente por TLS, com verificação de hostname/cadeia.

Repetir requisições a `traceedu.cloud`, `traceedu.com.br`, `www.traceedu.com.br`,
`app.traceedu.com.br` e `staging.traceedu.com.br`; redirecionamento 301 do `www`
é esperado. Comparar IDs/StartedAt de todos os containers: backend/frontend/bancos
devem ser idênticos aos anteriores. Confirmar recursos e ausência de erros no Caddy.

Não executar `compose down`, prune, reiniciar backend/frontend/PostgreSQL,
alterar banco, firewall, redes, swap ou instalar outro proxy. Produção e staging
compartilham `traceedu-net`; esse fato e ausência de swap ficam só documentados.

Veja [rollback.md](rollback.md) e [o relatório](../docs/implementation-status.md).
