# Rollback

## Somente catálogo

Release atual: `4f7454ef3afa48f0414d0184379d8a442703af1f`.
Release anterior preservado: `0e4bff12fad2829c2f4ebf8b162e1b43aa8d10f6`.
Voltar ao anterior remove `microarca-teste` do catálogo servido, mantendo OLED e
SSD1306. O fluxo de troca foi testado em diretório local temporário. Para desfazer
toda a instalação, usar a restauração de infraestrutura adiante e preservar arquivos.

Escolher o commit anterior entre os diretórios de release, conferir catálogo e
integridade e garantir que não há deploy concorrente (`.deploy-lock`). Criar o
symlink temporário no mesmo diretório e substituí-lo atomicamente:

```bash
ssh vps 'cd /var/www/MicroARCA-libs && test ! -e .deploy-lock && test -d releases/COMMIT_ANTERIOR && ln -s releases/COMMIT_ANTERIOR .current-rollback && mv -Tf .current-rollback current'
```

Substituir `COMMIT_ANTERIOR` pelo hash real de 40 caracteres. A checagem do lock
acima não reserva a implantação: coordenar janela sem deploy; para operação
concorrente usar a mesma reserva exclusiva `.deploy-lock` do publicador. Não
apagar o release retirado. Não é necessário recarregar Caddy.

Executar `verify_public.py` usando um checkout local limpo do commit selecionado,
pois ele compara o catálogo público com `dist/` local. Confirmar todos os URLs,
headers, hashes e domínios TraceEdu. Clientes com catálogo anterior ainda podem
usar arquivos antigos porque cada release novo preserva as versões anteriores;
após rollback, catálogos mais novos em cache podem apontar para versões ausentes:
o app deve revalidar o catálogo e tratar 404 sem instalar parcialmente.

O teste `test_prior_release_retained_and_rollback` realiza duas publicações em
diretório temporário, troca `current` de volta e verifica integridade. Testes
adicionais injetam falha na transferência e na troca do link. Nada disso usa a VPS.

## Infraestrutura

Se for necessário desfazer host/montagem:

1. Confirmar os backups timestampados aprovados e seus hashes.
2. Restaurar apenas Caddyfile.domains e docker-compose.prod.yml a partir desses
   backups, preservando as configurações dos hosts existentes.
3. Validar Caddyfile completo e Compose antes de recarregar/recriar.
4. Se a montagem foi removida, recriar **somente Caddy**, com `--no-deps`, usando
   os mesmos arquivos Compose do provisionamento. Se só mudou configuração,
   recarregar Caddy após validar e conferir que o bind mount reflete o arquivo novo.
5. Repetir HTTPS dos cinco domínios TraceEdu, estados e StartedAt dos containers.
   Nenhum backend, frontend ou banco deve ter reiniciado.

Não remover `/var/www/MicroARCA-libs` nem releases no primeiro rollback.
Não executar `docker compose down`, apagar volumes/imagens ou usar prune.
