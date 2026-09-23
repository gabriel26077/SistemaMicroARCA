# Relatório da implementação inicial

Data: 22/09/2026, São Paulo; inspeção remota em 23/09/2026 01:13 UTC.

## Resultado

Catálogo local completo, com schemas JSON, validação estrita, dependências exatas,
detecção de ciclos/conflitos, lock de versões imutáveis, build determinístico e
substituição atômica de dist. Inclui CI de validação, deploy SSH/rsync em releases,
verificação de integridade antes da troca de current e rollback testado localmente.
Não há backend, banco, painel, hooks, secrets ou implantação automática.

A estrutura final está no README: `packages/`, `schemas/`, `scripts/`, `tests/`,
`dist/v1/`, `deploy/`, `docs/`, `.github/workflows/` e `packages.lock.json`.

## Verificações locais

- `python3 -m unittest discover -s tests -v`: **54 testes**, cobrindo catálogo
  válido, determinismo, SHA-256, tamanho, limite 64 KiB, UTF-8, sintaxe, nomes,
  reservados, traversal, dependências, ciclos, versões, duplicatas, arquivo ausente,
  symlinks, imutabilidade, falhas de escrita/troca, transferência incompleta,
  concorrência, retenção de releases e rollback.
- `python3 scripts/validate_catalog.py`: duas versões válidas.
- `python3 scripts/build_catalog.py` e `--check`: distribuição sincronizada.
- `bash -n scripts/deploy.sh` e `git diff --check`: aprovados.
- `bash scripts/deploy.sh --dry-run`: validação local, sem SSH/escrita remota.
- Comparação binária da cópia OLED com a fonte local e do SSD1306 com o download
  oficial; hashes/tamanhos também conferidos no catálogo.
- Revisão e busca por padrões comuns de credenciais: nenhum segredo identificado.
- Snippet aceito por `caddy adapt` na versão instalada 2.11.4; apenas aviso de
  formatação. Não foi carregado, não solicitou certificado e não reiniciou Caddy.
  Validação da configuração completa continua obrigatória antes do provisionamento.

## Pacotes preparados — ainda não publicados

| Pacote | Versão | Bytes do módulo | SHA-256 |
| --- | --- | --- | --- |
| oled-pintor | 1.0.0 | 2916 | `82623d73823719c5fa7a2afcc956eacc44de9aaefb2b8896d64d4c3d1dcb1d90` |
| ssd1306 | 1.0.0 | 4922 | `b9f5331c75297774bced61bdfd12c37d4363336d064d7cf58967c88d807efbe5` |

OLED foi copiado byte a byte de `ProjetoARCA/embedded/lib_oled_pintor.py`, incluindo
finais de linha mistos. A origem tinha alterações locais; seu HEAD não identifica
sozinho o conteúdo copiado. ProjetoARCA não foi modificado.

SSD1306 veio de [MicroPython/micropython-lib](https://github.com/micropython/micropython-lib/blob/4fa59bd6a5916783e8503e9f2339627c8cffa5bf/micropython/drivers/display/ssd1306/ssd1306.py),
commit `4fa59bd6a5916783e8503e9f2339627c8cffa5bf`, versão upstream **0.1.0**, licença
MIT. O arquivo de licença agregador e a licença original do MicroPython, com
copyright de Damien P. George, foram preservados integralmente. URLs e histórico
de migração estão no README do pacote; UPSTREAM.json e LICENSE acompanham a
distribuição pública. O catálogo usa versão própria 1.0.0 para esse snapshot.

Revisão de imports: OLED usa math, machine e ssd1306; o driver usa micropython,
framebuf e time. Os módulos de firmware são esperados em MicroPython ESP32_GENERIC.
Não foi executado ensaio físico no ESP32/display; sintaxe e proveniência não
substituem esse teste.

## VPS, DNS e Caddy

- DNS de `libs.microarca.traceedu.com.br`: consultas `dig +short` A/AAAA vazias;
  resolução do sistema retorna nome desconhecido.
- Registro necessário: **A `libs.microarca` → `2.25.196.49`**, zona
  `traceedu.com.br`, TTL sugerido 300. Não alteramos DNS.
- VPS: carga 0.00, 2510 MiB disponíveis, 37 GB livres, sem swap e sem unidades
  systemd em falha. Não ajustamos recursos/redes/swap.
- Sete containers em execução, RestartCount 0; sem healthchecks Docker definidos.
- HTTPS: traceedu.cloud 200, traceedu.com.br 200, www.traceedu.com.br 301,
  app.traceedu.com.br 200, staging.traceedu.com.br 200; curl sem erros TLS.
- Nenhum backend, frontend, banco ou Caddy reiniciado. Nenhuma alteração de dados,
  arquivo de configuração, volume ou container do TraceEdu.
- `/var/www/MicroARCA-libs` ainda não existe. Nenhum release foi enviado.
- Caddyfile e trechos relevantes dos três Compose foram lidos. O
  [diff proposto](../deploy/proposed-infrastructure.patch) foi calculado em memória
  na VPS e salvo somente localmente. Não aplicado. Backups remotos não foram
  criados, pois o provisionamento está bloqueado pelo DNS e não houve edição.

StartedAt observados (UTC), para comparar antes/depois da futura implantação:

| Container | StartedAt |
| --- | --- |
| traceedu-frontend | 2026-09-21T16:03:20.419193352Z |
| traceedu-backend | 2026-09-21T16:03:20.221226637Z |
| traceedu-db | 2026-08-08T19:02:04.28108359Z |
| traceedu-dev-frontend | 2026-09-21T16:01:57.792134695Z |
| traceedu-dev-backend | 2026-09-21T16:01:57.560774103Z |
| traceedu-dev-db | 2026-08-30T22:33:29.92891813Z |
| traceedu-caddy | 2026-09-13T02:36:22.259568595Z |

## Git e próximos passos

Commits da implementação inicial, posteriormente enviados para `origin/main`:

- `c8bf161` — schemas e bibliotecas com proveniência.
- `e679c13` — validador e build atômico determinístico.
- `bbdece6` — testes de validação e build.
- `4b45f89` — deploy, verificação pública, testes de releases e CI.
- `docs: document client contract and blocked DNS deployment` — documentação e
  este relatório; consultar `git log -5 --oneline` para o hash final.

Atualização após autorização de publicação: código enviado ao GitHub em
`gabriel26077/SistemaMicroARCA`; o CI da implementação passou
([execução 35808052618](https://github.com/gabriel26077/SistemaMicroARCA/actions/runs/35808052618)).
O repositório estava público e sua visibilidade foi corrigida para **privado**,
conforme a especificação. Nova inspeção da VPS confirmou DNS A/AAAA ainda ausentes,
os mesmos StartedAt dos sete containers e os mesmos códigos HTTP dos domínios
TraceEdu. A publicação na VPS continua bloqueada pelo DNS; nenhuma configuração
remota foi alterada e nenhum release foi transferido.

A URL prevista ainda não está disponível:
`https://libs.microarca.traceedu.com.br/v1/catalog.json`.

Próximo passo externo: criar o registro DNS indicado. Depois, repetir a inspeção,
refazer o diff se necessário, fazer backups timestampados e obter a confirmação
única antes de alterar Caddy/Compose. Publicar o release completo, configurar
somente Caddy e executar `python3 scripts/verify_public.py`, comparando também os
domínios TraceEdu e StartedAt. Comandos em [deploy/README.md](../deploy/README.md).

Limitações restantes: ensaio físico OLED/ESP32, publicação HTTPS condicionada a
DNS/autorização e futura assinatura Ed25519 com gerenciamento real de chaves.
