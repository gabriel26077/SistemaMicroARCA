Você está dentro de um novo repositório Git privado destinado ao catálogo oficial de bibliotecas do MicroARCA.

ATUALIZAÇÃO DO USUÁRIO (22/09/2026): o endpoint passa a ser
`libs-microarca.traceedu.com.br`, com CNAME para `traceedu.com.br` e proxy Cloudflare.
No modo explícito Cloudflare, a verificação DNS deve validar a cadeia aprovada e
as redes do proxy; os IPs públicos serão da Cloudflare. A origem será confirmada
pela verificação HTTPS e dos bytes publicados após ativação. As demais restrições
de preservação do TraceEdu, backups e confirmação antes de editar Caddy/Compose
continuam aplicáveis.

Quero que você implemente o sistema completo de catálogo e distribuição de bibliotecas MicroPython descrito abaixo. Trabalhe com autonomia, mas preserve rigorosamente a VPS e o sistema TraceEdu existente.

IMPORTANTE:
- Leia completamente estas instruções antes de alterar qualquer coisa.
- Comece inspecionando o repositório atual.
- Não edite o projeto principal ProjetoARCA nesta tarefa.
- Não envie nada ao GitHub remoto sem minha autorização explícita.
- Commits locais são permitidos e desejáveis.
- Não altere banco de dados, backend, frontend ou containers do TraceEdu.
- Não reinicie os containers de backend, frontend ou PostgreSQL.
- Não faça nenhuma alteração na VPS antes de concluir e testar localmente o catálogo.
- Antes de modificar Caddy ou Docker Compose na VPS, mostre o diff exato, faça backup dos arquivos envolvidos e peça uma única confirmação.
- Se o DNS ainda não existir, finalize o sistema local e a documentação, mas não force emissão de certificado nem publicação incompleta.

## Objetivo

Criar um repositório que funcione como fonte oficial e auditável das bibliotecas MicroPython do MicroARCA.

O aplicativo Android futuramente consultará:

https://libs-microarca.traceedu.com.br/v1/catalog.json

O catálogo e os arquivos serão estáticos. Não crie backend, banco de dados, painel administrativo, autenticação ou API dinâmica nesta primeira versão.

O repositório Git será privado, mas os arquivos publicados na VPS serão públicos. Documente claramente essa diferença.

## Arquitetura

Fluxo esperado:

1. Bibliotecas e manifests ficam versionados neste repositório.
2. Um script valida nomes, versões, dependências, tamanhos e código Python.
3. Um script gera deterministicamente a pasta `dist/`.
4. `dist/` contém o catálogo público e os arquivos para download.
5. Um processo de implantação envia `dist/` para a VPS.
6. O Caddy existente entrega os arquivos por HTTPS.
7. O aplicativo baixa o catálogo, verifica SHA-256 e instala os arquivos no ESP32.

As URLs dos arquivos dentro do catálogo devem ser relativas ao próprio catálogo. Não grave `traceedu.com.br` em cada item. Isso permitirá migrar posteriormente para outra VPS sem regenerar todos os pacotes.

## Estrutura esperada

Crie uma estrutura semelhante a:

.
├── README.md
├── LICENSE
├── packages/
│   ├── oled-pintor/
│   │   └── 1.0.0/
│   │       ├── manifest.json
│   │       ├── lib_oled_pintor.py
│   │       └── LICENSE
│   └── ssd1306/
│       └── 1.0.0/
│           ├── manifest.json
│           ├── ssd1306.py
│           └── LICENSE
├── schemas/
│   ├── package.schema.json
│   └── catalog.schema.json
├── scripts/
│   ├── build_catalog.py
│   ├── validate_catalog.py
│   └── deploy.sh
├── tests/
│   ├── test_build_catalog.py
│   └── test_validate_catalog.py
├── deploy/
│   ├── Caddyfile.microarca
│   ├── README.md
│   └── rollback.md
├── docs/
│   ├── client-contract.md
│   ├── publishing.md
│   └── security.md
├── dist/
│   └── v1/
│       ├── catalog.json
│       └── packages/
└── .github/
    └── workflows/
        └── validate.yml

Adapte apenas se houver uma razão técnica concreta e documentada.

## Formato dos pacotes

Cada versão deve possuir seu próprio `manifest.json`.

Exemplo conceitual:

{
  "schema": 1,
  "id": "oled-pintor",
  "name": "Pintor OLED",
  "version": "1.0.0",
  "description": "Funções educacionais para desenhar em displays OLED.",
  "author": "Projeto ARCA",
  "license": "MIT",
  "homepage": "",
  "compatibility": {
    "micropython": ">=1.24",
    "boards": ["ESP32_GENERIC"]
  },
  "dependencies": [
    {
      "id": "ssd1306",
      "version": "1.0.0"
    }
  ],
  "files": [
    {
      "source": "lib_oled_pintor.py",
      "install_as": "lib_oled_pintor.py"
    }
  ]
}

Nesta primeira versão:

- Dependências usam versões exatas.
- Cada arquivo é instalado diretamente em `/lib` no ESP32.
- Não aceite subdiretórios em `install_as`.
- Não implemente intervalos complexos de SemVer.
- Não implemente código executável no servidor.
- Não permita hooks de instalação.

## Regras obrigatórias de validação

Implemente validações para:

- IDs de pacote em lowercase, usando apenas `a-z`, `0-9` e hífen.
- Versões no formato SemVer `X.Y.Z`.
- Cada versão é imutável.
- Cada arquivo precisa terminar em `.py`.
- O nome do módulo deve ser um identificador Python ASCII válido.
- Cada arquivo deve ter no máximo 65.536 bytes.
- O arquivo deve ser UTF-8 válido.
- O arquivo deve passar por `ast.parse`.
- O caminho não pode conter `/`, `\`, `..` ou caracteres de controle.
- Rejeitar os nomes reservados:
  - `boot.py`
  - `main.py`
  - `user.py`
  - `arca_ble.py`
  - `arca_runtime.py`
  - `arca_files.py`
- Todas as dependências precisam existir no catálogo.
- Detectar ciclos de dependência.
- Detectar dois pacotes diferentes tentando possuir o mesmo arquivo.
- Detectar manifests duplicados.
- Detectar IDs ou versões duplicadas.
- Detectar arquivos declarados que não existem.
- Detectar arquivos não declarados dentro da versão, exceto `LICENSE`, README e metadados permitidos.
- Exigir licença e origem para dependências de terceiros.

Use apenas a biblioteca padrão do Python sempre que possível. Não adicione frameworks desnecessários.

## Catálogo gerado

O `build_catalog.py` deve:

- Validar tudo antes de gerar.
- Produzir resultado determinístico.
- Ordenar pacotes, versões, dependências e arquivos.
- Calcular SHA-256 a partir dos bytes exatos.
- Calcular o tamanho em bytes.
- Copiar os arquivos em modo binário, sem alterar finais de linha.
- Gerar URLs relativas.
- Gravar JSON UTF-8 legível e estável.
- Usar escrita temporária e substituição atômica.
- Nunca deixar um `dist/` parcialmente atualizado.

Formato aproximado da saída:

{
  "schema": 1,
  "generated_at": "...",
  "packages": [
    {
      "id": "oled-pintor",
      "name": "Pintor OLED",
      "version": "1.0.0",
      "description": "...",
      "author": "Projeto ARCA",
      "license": "MIT",
      "compatibility": {
        "micropython": ">=1.24",
        "boards": ["ESP32_GENERIC"]
      },
      "dependencies": [
        {
          "id": "ssd1306",
          "version": "1.0.0"
        }
      ],
      "files": [
        {
          "name": "lib_oled_pintor.py",
          "url": "packages/oled-pintor/1.0.0/lib_oled_pintor.py",
          "size": 1234,
          "sha256": "..."
        }
      ]
    }
  ]
}

O campo `generated_at` não pode tornar builds idênticos diferentes desnecessariamente. Escolha uma estratégia reprodutível, como `SOURCE_DATE_EPOCH`, data do commit ou omissão desse campo, e documente a decisão.

Implemente também um modo `--check` que confirme que `dist/` corresponde exatamente às fontes sem modificá-lo.

## Bibliotecas iniciais

A biblioteca criada pelo projeto está disponível, provavelmente, em:

/mnt/c/Users/GSNN/Documents/ProjetoARCA/embedded/lib_oled_pintor.py

Localize e copie esse arquivo para o pacote `oled-pintor` sem modificar silenciosamente seu comportamento.

Ela importa `ssd1306`. Portanto, o pacote não pode ser publicado como funcional sem essa dependência.

Para `ssd1306`:

- Procure a implementação oficial ou mantida pelo projeto MicroPython/micropython-lib.
- Use apenas fonte primária e confiável.
- Registre URL de origem, versão e commit exato.
- Preserve a licença.
- Inclua o texto da licença exigido pela origem.
- Não copie código de blogs, snippets ou repositórios aleatórios.
- Se não for possível confirmar origem e licença, pare essa inclusão, documente o bloqueio e não publique um pacote quebrado.

Revise `lib_oled_pintor.py` somente quanto a sintaxe e compatibilidade de importação. Não faça uma refatoração ampla nesta tarefa.

## Testes

Use `unittest` da biblioteca padrão.

Cubra pelo menos:

- Catálogo válido.
- Build determinístico.
- Cálculo correto de SHA-256.
- Tamanho correto.
- Arquivo maior que 64 KiB.
- Nome inválido.
- Nome reservado.
- Traversal com `../`.
- UTF-8 inválido.
- Python com erro de sintaxe.
- Dependência inexistente.
- Ciclo de dependência.
- Versão inválida.
- Arquivo duplicado entre pacotes.
- Arquivo declarado inexistente.
- Build atômico.
- `--check` detectando catálogo desatualizado.

Crie um GitHub Actions simples que rode os testes e confirme que `dist/` está sincronizado.

Não configure secrets nem implantação automática no GitHub nesta fase.

## Contrato para o aplicativo

Crie `docs/client-contract.md` explicando como o aplicativo deve consumir o catálogo:

- Timeout de conexão e leitura.
- Tamanho máximo do catálogo, por exemplo 1 MiB.
- HTTPS obrigatório.
- Nunca aceitar redirecionamento para HTTP.
- Cache local do último catálogo válido.
- Suporte a ETag/If-None-Match quando disponível.
- Verificação do tamanho antes e depois do download.
- Verificação obrigatória do SHA-256.
- Resolução das dependências antes da instalação.
- Instalação das dependências em ordem topológica.
- Não instalar parcialmente um pacote se uma dependência falhar.
- Registrar localmente pacote, versão e arquivos instalados.
- Não remover arquivo compartilhado ainda usado por outro pacote.
- Pedir confirmação antes de atualizar ou remover.
- Tratar código MicroPython como código executável e potencialmente perigoso.
- Não permitir pacotes enviados livremente por terceiros nesta primeira versão.

O catálogo SHA-256 protege contra corrupção e inconsistência, mas não contra comprometimento simultâneo do servidor e do catálogo. Documente como evolução futura a assinatura digital do catálogo com Ed25519, mantendo a chave privada fora da VPS e a chave pública embutida no aplicativo. Não simule assinatura sem gerenciamento real de chaves.

## Publicação local

Implemente `scripts/deploy.sh` de maneira defensiva.

Ele deve:

- Executar os testes.
- Executar todas as validações.
- Gerar `dist/`.
- Confirmar que o working tree está no estado esperado.
- Usar `rsync` por SSH.
- Publicar em um diretório de release identificado pelo commit Git.
- Nunca sobrescrever diretamente o release atual durante a transferência.
- Após transferência completa, atualizar atomicamente um link `current`.
- Manter pelo menos o release anterior para rollback.
- Ter modo `--dry-run`.
- Ter mensagens claras.
- Usar `set -Eeuo pipefail`.
- Não armazenar senha ou chave SSH no repositório.

Estrutura remota desejada:

/var/www/MicroARCA-libs/
├── releases/
│   ├── <commit-1>/
│   └── <commit-2>/
└── current -> releases/<commit-atual>

O diretório pai deve ser montado no Caddy como somente leitura:

/var/www/MicroARCA-libs:/srv/microarca-libs:ro

Assim o Caddy serve:

/srv/microarca-libs/current/v1/catalog.json

## Situação atual da VPS

O acesso é feito por:

ssh vps

A VPS foi inspecionada anteriormente e possui:

- Ubuntu 24.04.
- 1 vCPU.
- 3,8 GiB de RAM.
- Aproximadamente 2,5 GiB disponíveis.
- Aproximadamente 37 GB livres.
- Carga muito baixa.
- Sem swap.
- Docker e Docker Compose.
- Caddy em container.
- Produção e staging do TraceEdu em containers separados.
- Nenhum serviço com falha.
- Nenhum OOM recente.

Containers atuais:

- traceedu-frontend
- traceedu-backend
- traceedu-db
- traceedu-dev-frontend
- traceedu-dev-backend
- traceedu-dev-db
- traceedu-caddy

O Caddy atual ocupa as portas 80 e 443.

Projetos Compose:

- Produção:
  - `/var/www/TraceEdu/docker-compose.yml`
  - `/var/www/TraceEdu/docker-compose.prod.yml`
- Staging:
  - `/var/www/TraceEdu-dev/docker-compose.staging.yml`

Configuração Caddy:

- Host: `/var/www/TraceEdu/Caddyfile.domains`
- Container: `/etc/caddy/Caddyfile`
- Montagem atual: somente leitura.

O Caddy já atende:

- traceedu.cloud
- traceedu.com.br
- www.traceedu.com.br
- app.traceedu.com.br
- staging.traceedu.com.br

Produção e staging compartilham atualmente a rede Docker `traceedu-net`.

Não corrija swap, redes, limites de container ou arquitetura do TraceEdu nesta tarefa. Apenas documente essas observações se forem relevantes.

## Configuração desejada do Caddy

Prepare um snippet semelhante a:

libs-microarca.traceedu.com.br {
    root * /srv/microarca-libs/current

    @catalog path /v1/catalog.json
    header @catalog Cache-Control "no-cache"

    @packages path /v1/packages/*
    header @packages Cache-Control "public, max-age=31536000, immutable"

    header {
        X-Content-Type-Options nosniff
        Access-Control-Allow-Origin *
    }

    file_server
}

Não habilite `file_server browse`.

O catálogo deve poder ser atualizado, por isso não deve receber cache imutável. Arquivos versionados de pacotes podem ter cache longo e imutável.

O domínio exato permite que o Caddy obtenha certificado automaticamente depois que o DNS apontar para a VPS.

## DNS

Antes de publicar, verifique:

dig +short libs-microarca.traceedu.com.br

O registro deve apontar para a VPS.

Se não existir ou apontar para outro IP:

- Não force a publicação HTTPS.
- Não mexa no provedor DNS.
- Informe exatamente qual registro precisa ser criado.
- Continue com toda a implementação local e documentação.

## Mudanças na VPS

Antes de qualquer alteração:

1. Verifique novamente recursos e containers.
2. Faça uma requisição de saúde aos domínios existentes.
3. Leia os Compose e o Caddyfile atuais.
4. Identifique o menor diff possível.
5. Faça backups com timestamp dos arquivos que serão alterados.
6. Mostre o diff e peça confirmação.

Se autorizado:

- Crie apenas `/var/www/MicroARCA-libs`.
- Acrescente a montagem somente leitura ao serviço Caddy.
- Acrescente o host do MicroARCA ao Caddyfile.
- Valide a configuração antes de recarregar.
- Se uma recriação do container Caddy for necessária por causa da nova montagem, recrie apenas o Caddy.
- Não execute `docker compose down`.
- Não recrie backend, frontend ou bancos.
- Não remova imagens, volumes, caches ou arquivos do TraceEdu.
- Não execute `docker system prune`.
- Não altere firewall fora do necessário — 80 e 443 já estão publicados.
- Não instale outro proxy reverso.

Valide o Caddy com o mecanismo apropriado antes do reload/recreate.

Após a publicação, confirme:

- `catalog.json` retorna HTTP 200.
- O JSON é válido.
- Os headers de cache estão corretos.
- Cada URL do catálogo responde.
- Tamanho e SHA-256 dos downloads correspondem ao catálogo.
- HTTPS está válido.
- Os domínios existentes do TraceEdu continuam respondendo.
- Todos os containers anteriores continuam saudáveis.
- Logs recentes do Caddy não apresentam erros.
- Nenhum backend ou banco foi reiniciado.

## Rollback

Documente e teste conceitualmente o rollback:

- Retornar o link `current` ao release anterior.
- Restaurar Caddyfile e Compose a partir dos backups.
- Validar novamente o Caddy.
- Recriar somente o container Caddy se a montagem tiver sido removida.
- Confirmar os domínios TraceEdu.

Não apague automaticamente releases antigos no primeiro deploy.

## Documentação

O README principal deve explicar:

- Propósito do repositório.
- Como adicionar uma biblioteca.
- Como publicar nova versão.
- Como validar.
- Como gerar o catálogo.
- Como executar testes.
- Como fazer deploy em dry-run.
- Como fazer deploy real.
- Como migrar para outra VPS.
- Que versões publicadas são imutáveis.
- Que o repositório ser privado não torna os arquivos publicados privados.
- Que bibliotecas MicroPython executam código dentro do ESP32.
- Política inicial: somente bibliotecas revisadas pelo mantenedor.

Crie documentação suficiente para que uma pessoa consiga migrar futuramente de `libs-microarca.traceedu.com.br` para outro domínio mudando apenas o endpoint raiz do aplicativo e a infraestrutura de hospedagem.

## Git

Faça commits locais pequenos e coerentes, por exemplo:

1. `feat: define library registry schema`
2. `feat: add deterministic catalog builder`
3. `test: validate catalog and package safety`
4. `docs: document publishing and client contract`
5. `ops: add safe static deployment workflow`

Não faça push.

## Critérios de conclusão

Considere concluído somente quando:

- Todos os testes passam.
- O catálogo é reproduzível.
- `--check` funciona.
- SHA-256 e tamanhos são verificados.
- Dependências são validadas.
- Pacotes inválidos são rejeitados.
- A documentação está completa.
- Existe deploy com dry-run.
- Não há segredos no Git.
- `git diff --check` passa.
- O status Git está compreendido.
- Nenhuma alteração não autorizada foi feita no TraceEdu.
- Se o DNS e a autorização permitirem, o catálogo estiver publicado e verificado.
- Caso a publicação esteja bloqueada, o bloqueio e os próximos comandos estejam claramente documentados.

Ao final, entregue um relatório objetivo contendo:

- O que foi implementado.
- Estrutura final.
- Testes executados.
- Pacotes publicados.
- Proveniência e licença de código de terceiros.
- Estado do DNS.
- Estado da VPS.
- Alterações feitas ou não feitas no Caddy.
- URL final ou motivo pelo qual ainda não está disponível.
- Commits locais criados.
- Riscos e próximos passos.
