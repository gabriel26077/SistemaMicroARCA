# Publicação e imutabilidade

Git privado guarda fontes e revisão; `dist/` contém material público. Não incluir
senhas, chaves, `.env`, dumps ou dados pessoais. Não há push/publicação automática.
GitHub Actions apenas valida após push autorizado; não exige secrets nem acesso SSH.

## Nova versão

Copiar a versão anterior para novo diretório X.Y.Z e alterar somente a nova versão.
IDs seguem `[a-z0-9]+(-[a-z0-9]+)*`: hífens iniciais/finais/repetidos são rejeitados
por convenção canônica. Versões sem zeros à esquerda, prerelease ou ranges.
Dependências exatas precisam existir; imports de firmware não são pacotes.

Terceiros exigem `UPSTREAM.json`, fonte primária, commit de 40 caracteres, versão
upstream e texto da licença com copyright. Versão interna pode diferir do upstream;
registre ambas, como no SSD1306. O mantenedor verifica correspondência entre URL,
bytes e licença; o validador não consulta rede nem determina autoria sozinho.

```bash
python3 scripts/validate_catalog.py --update-lock
python3 scripts/build_catalog.py
python3 -m unittest discover -s tests -v
python3 scripts/build_catalog.py --check
git diff --check
git diff --stat
```

Revisar e commitar fontes, lock e dist. Até mudanças de README numa versão congelada
são proibidas: notas devem ficar fora da versão ou em nova versão.
`--baseline-ref <commit>` compara contra referência revisada; CI usa o commit
anterior ao push/base do PR. Na primeira importação sem lock anterior, o lock torna-se
a referência dos próximos commits. Proteção de branch/revisão devem impedir remoção
maliciosa dos próprios validadores ou reescrita de histórico.

## Implantação

Execute `bash scripts/deploy.sh --dry-run --cloudflare` com árvore limpa: valida antes/depois
do build, sem conexão remota. Na implantação real:

1. No modo direto, exige IPs da VPS. Com `--cloudflare`, exige que os IPs do domínio
   sejam iguais aos de `traceedu.com.br` e pertençam às redes oficiais Cloudflare.
   O proxy não revela sua origem por DNS: comprovar HTTPS e conteúdo após ativação.
2. Reserva `.deploy-lock` exclusivo e `.incoming-<commit>-<token>`.
3. Transfere via rsync/SSH sem tocar no release servido.
4. Confere digest de todos os arquivos e SHA-256/tamanho de cada módulo.
5. Compara arquivos versionados com todos os releases, inclusive após rollback.
   Mudança/remoção bloqueia publicação, protegendo URLs com cache imutável.
6. Promove para `releases/<commit>` e troca `current` atomicamente. Reimplantar
   o mesmo commit só é permitido com conteúdo idêntico.
7. Verifica HTTPS, headers, catálogo, licenças e todos os downloads públicos.

Falha anterior à troca preserva `current`; falha posterior pode exigir rollback.
O trap limpa apenas incoming/link temporário e lock da própria execução. Queda de
conexão/processo pode deixar lock: conferir token e ausência de deploy ativo antes
de remover manualmente. Não automatizar limpeza de releases nesta fase.

`/var/www/MicroARCA-libs/releases` deve existir previamente. Deploy não provisiona
nem reinicia serviços; primeiro provisionamento exige aprovação em `deploy/README.md`.
No primeiro provisionamento, `--bootstrap --cloudflare` permite preparar/ativar o release completo
antes de habilitar o host Caddy, adiando apenas a checagem pública HTTPS. DNS continua
obrigatório e a verificação pública deve ser executada após configurar o host.
