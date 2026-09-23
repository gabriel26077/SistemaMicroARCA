# Relatório de publicação MicroARCA

Publicado e verificado em 23/09/2026 às 03:05 UTC (00:05 em São Paulo).

**Endpoint público:** https://libs-microarca.traceedu.com.br/v1/catalog.json

**Release ativo:** `0e4bff12fad2829c2f4ebf8b162e1b43aa8d10f6`.
GitHub: `gabriel26077/SistemaMicroARCA`, privado, branch `main`.

## Implementado

Catálogo estático com schemas, validação de nomes, versões, arquivos, UTF-8,
sintaxe, dependências exatas, ciclos e conflitos; ledger de versões imutáveis;
build determinístico e atômico; `--check`; CI; publicação SSH/rsync em releases;
verificação de integridade e troca atômica de `current`; documentação do cliente,
segurança, publicação, migração e rollback. Sem backend, banco ou hooks.

Estrutura: `packages/`, `packages.lock.json`, `schemas/`, `scripts/`, `tests/`,
`dist/v1/`, `deploy/`, `docs/`, `.github/workflows/`. O Git é privado; somente
`dist/` é distribuído publicamente. Não foram identificados segredos na revisão.

## Pacotes publicados e proveniência

| Pacote | Versão | Bytes do módulo | SHA-256 |
| --- | --- | --- | --- |
| oled-pintor | 1.0.0 | 2916 | `82623d73823719c5fa7a2afcc956eacc44de9aaefb2b8896d64d4c3d1dcb1d90` |
| ssd1306 | 1.0.0 | 4922 | `b9f5331c75297774bced61bdfd12c37d4363336d064d7cf58967c88d807efbe5` |

OLED foi copiado byte a byte do workspace ProjetoARCA, sem modificar a origem,
com finais de linha preservados e licença MIT. O arquivo de origem tinha
alterações locais; seu hash identifica a cópia efetiva, não somente o HEAD.

SSD1306 veio do repositório oficial MicroPython/micropython-lib, commit
`4fa59bd6a5916783e8503e9f2339627c8cffa5bf`, versão upstream 0.1.0, licença MIT.
A distribuição preserva a licença agregadora integral e a licença original
MicroPython com copyright de Damien P. George. URLs fixas e histórico estão no
[README do pacote](../packages/ssd1306/1.0.0/README.md); LICENSE e UPSTREAM.json
são públicos junto com o código. `oled-pintor` depende de `ssd1306==1.0.0`.

## Verificação

- **62 testes unittest passaram**, incluindo builds determinísticos/atômicos,
  hashes, tamanhos, entradas inválidas, dependências, imutabilidade, proxy DNS,
  transferência incompleta, concorrência e rollback local.
- Validação de fontes, `build_catalog.py --check`, `deploy.sh --dry-run --cloudflare`,
  `bash -n` e `git diff --check` aprovados.
- `verify_public.py`: HTTPS válido, catálogo HTTP 200 e igual a dist local;
  headers cache/CORS/nosniff; todos os módulos, tamanhos, SHA-256, licenças e
  proveniência conferidos pela URL pública.
- Catálogo: 1662 bytes; SHA-256
  `5e933361ff82b1e29bd3dcaed9a73fe0e0b377cfe7e003cf76f82426feedd305`.
  Cache `no-cache`, ETag presente. Pacotes com cache imutável de um ano.
- TLS direto na origem validado com hostname e cadeia, TLS 1.3, Let’s Encrypt,
  certificado válido até 22/12/2026 01:57:56 UTC.
- Configuração completa do Caddy validada antes da recriação; montagem somente
  leitura do diretório pai confirmada. Hashes aplicados iguais ao diff aprovado.
- Sem novos erros nos logs do Caddy nos dois minutos anteriores à verificação
  final. Na emissão inicial, TLS-ALPN falhou através do proxy; o fallback HTTP-01
  automático obteve o certificado com sucesso.

O User-Agent genérico do urllib recebeu HTTP 403/Cloudflare 1010. O verificador
foi corrigido para identificar honestamente a aplicação como
`MicroARCA-RegistryVerifier/1.0`; depois disso todos os downloads passaram.
Não foram desativadas proteções Cloudflare. O contrato do app documenta seu
próprio User-Agent e o tratamento de bloqueios/desafios.

## DNS e VPS

O usuário substituiu o hostname inicial de dois níveis por
`libs-microarca.traceedu.com.br`, CNAME para `traceedu.com.br`. O proxy resolve
para redes Cloudflare. O deploy valida essas redes pela API pública oficial e
compara com o destino aprovado; a verificação pública comprova os bytes servidos.
A VPS de origem permanece em `2.25.196.49`. Nenhum DNS foi alterado pelo agente.

Apenas `/var/www/MicroARCA-libs` e seus releases foram criados para o catálogo.
Os dois arquivos de infraestrutura receberam somente o diff aprovado:

- `/var/www/TraceEdu/docker-compose.prod.yml`: montagem do pai no Caddy como `ro`.
- `/var/www/TraceEdu/Caddyfile.domains`: host do catálogo e headers estáticos.

Backups preservados:

- `/var/www/TraceEdu/docker-compose.prod.yml.bak-microarca-20260923T023344651705Z`
- `/var/www/TraceEdu/Caddyfile.domains.bak-microarca-20260923T023344651705Z`

Somente `traceedu-caddy` foi recriado, às 02:56:20 UTC. Nenhum backend, frontend
ou PostgreSQL reiniciou: os seis containers mantiveram IDs, StartedAt e contadores
RestartCount. Os sete estão em execução; não definem healthcheck Docker.

| Domínio existente | HTTP após publicação |
| --- | --- |
| traceedu.cloud | 200 |
| traceedu.com.br | 200 |
| www.traceedu.com.br | 301 |
| app.traceedu.com.br | 200 |
| staging.traceedu.com.br | 200 |

Na inspeção anterior havia cerca de 2,5 GiB de memória disponível, 37 GB livres,
carga baixa e nenhuma unidade systemd em falha. Não foram alterados banco, rede,
swap, firewall, imagens ou volumes do TraceEdu. Não houve compose down ou prune.

[Evidência da aprovação e backups](../deploy/approval-evidence.json) ·
[Evidência final de publicação](../deploy/publication-evidence.json) ·
[Diff exato aplicado](../deploy/proposed-infrastructure.patch).

## Git, rollback e limites

Commits enviados incluem `c8bf161` (schemas/bibliotecas), `e679c13` (build),
`bbdece6` (testes), `4b45f89` (deploy/CI), `ba7c5d1` (documentação), `25bef72`
(estado GitHub) e `0e4bff1` (hostname/Cloudflare, release publicado). A correção
posterior do identificador do verificador e este relatório não alteram dist;
a publicação continua vinculada ao release acima. Consultar `git log` para os
commits de documentação/verificação posteriores. O repositório foi tornado
privado conforme a especificação e os pushes foram autorizados pelo usuário.

É o primeiro release real, portanto não existe release anterior de produção.
Rollback por troca de symlink foi testado localmente com duas releases; rollback
da primeira instalação restaura os dois backups, valida e recria somente Caddy,
preservando o catálogo no disco. Procedimento em [rollback.md](../deploy/rollback.md).

Limitações: falta ensaio físico OLED/ESP32; SHA-256 não protege contra servidor e
catálogo comprometidos juntos. Assinatura Ed25519, rotação de chaves e proteção
anti-replay são evolução futura, sem assinatura simulada nesta versão.
