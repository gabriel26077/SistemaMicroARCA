# Segurança e limites

- Apenas `/lib`, sem subdiretórios, com identificadores ASCII e extensão `.py`.
- Máximo 65.536 bytes por arquivo, UTF-8 e `ast.parse` sem importar código.
  Isso não constitui sandbox nem auditoria completa.
- Nomes proibidos: `boot.py`, `main.py`, `user.py`, `arca_ble.py`, `arca_runtime.py`,
  `arca_files.py`, inclusive variantes de caixa. Rejeitar palavras-chave Python,
  traversal, controles, symlinks, arquivos especiais e não declarados.
- Bloquear campos desconhecidos/hooks, IDs/versões/manifests repetidos, ciclos,
  dependências ausentes, conflitos de versões e posse de arquivos.
- Manifestos de blocos são dados declarativos limitados a 64 KiB. JavaScript,
  callbacks, HTML e hooks remotos não fazem parte do contrato e são rejeitados.
  Templates geram MicroPython para o ESP32, mas nunca são executados na IDE.
- Manter versões antigas. Lock e histórico Git e comparação remota de releases
  protegem URLs imutáveis no fluxo normal de publicação.
- Somente mantenedor revisado. `origin` é declaração sujeita a revisão humana,
  não comprovação automática de autoria/licença.
- Licenças e proveniência são públicas também; a distribuição não contém segredos.
- CI somente leitura, sem secrets/deploy. Chave SSH fica fora do repositório.
  Alias `vps` deve estar configurado; não desabilitar verificação de host SSH.
- Caddy serve arquivos sem browse, com `nosniff`, CORS e HTTPS. Catálogo `no-cache`;
  pacotes versionados imutáveis por um ano.
- SHA-256 não autentica contra servidor+catálogo comprometidos. Evolução: Ed25519
  com chave privada fora da VPS, pública no app, rotação/revogação e anti-replay.
  Nenhuma assinatura simulada nesta versão.
- Não alterar bancos, backend, frontend, redes, swap ou volumes TraceEdu.
  Proibidos `docker compose down` e `docker system prune`. Montagem somente leitura;
  apenas Caddy pode ser recriado após aprovação específica.

Build atômico exige Linux/glibc e suporte RENAME_EXCHANGE no filesystem; sem isso
falha preservando dist. Deploy exige releases/symlinks no mesmo filesystem.
Operador e workspace são considerados confiáveis; quem controla o repositório
ou root na VPS pode alterar verificadores e infraestrutura.
