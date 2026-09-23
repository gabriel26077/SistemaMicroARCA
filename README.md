# Catálogo de bibliotecas MicroARCA

Fonte auditável de bibliotecas MicroPython para ESP32. A distribuição é estática:
sem backend, banco, autenticação ou execução de Python no servidor web.
Endpoint publicado: [catalog.json](https://libs-microarca.traceedu.com.br/v1/catalog.json).
Consulte [o estado da implantação](docs/implementation-status.md) antes de usá-lo.

**O repositório é privado; os arquivos publicados são públicos.** Bibliotecas
executam código no ESP32. Nesta fase, somente bibliotecas revisadas pelo mantenedor
são aceitas. Não há upload de terceiros nem hooks de instalação.

## Uso local

Requisitos: Linux/glibc com `renameat2(RENAME_EXCHANGE)`, Python >=3.10 e Git.
Publicação requer também Bash, SSH e rsync. Sem dependências Python externas.

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_catalog.py
python3 scripts/build_catalog.py
python3 scripts/build_catalog.py --check
git diff --check
```

O build ordena pacotes, versões numericamente, dependências, placas e arquivos.
Omite `generated_at`: fontes iguais geram bytes iguais, independentemente da hora.
Hashes/tamanhos usam bytes originais, sem normalizar finais de linha; `.gitattributes`
protege os arquivos distribuídos. O código MicroPython não é importado/executado.

Um diretório temporário é preparado no mesmo filesystem. O primeiro build usa
rename; os seguintes usam troca atômica de diretórios do Linux. Falhas anteriores
à troca preservam `dist/`; não há fallback para apagar e recriar. Lock serializa
builds locais. `--check` compara arquivos, bytes e diretórios sem escrever nada.
Uma interrupção abrupta pode deixar temporários ignorados pelo Git. A garantia é
de visibilidade atômica, não de recuperação após falha física de disco.

## Adicionar biblioteca ou nova versão

1. Crie `packages/<id>/<X.Y.Z>/` com manifest, arquivos `.py` e licença completa.
   Siga os exemplos e [package.schema.json](schemas/package.schema.json).
2. IDs usam ASCII minúsculo, números e hífens internos. Cada `install_as` é um
   identificador Python ASCII com `.py`, instalado diretamente em `/lib`.
3. Declare dependências exatas. Terceiros exigem `origin: "third-party"`, homepage
   HTTPS e `UPSTREAM.json` com repositório, commit completo, versão upstream,
   URLs de fonte/licença e identificador da licença. Revise origem e código.
4. Registre **somente novas versões**, valide e gere a distribuição:

   ```bash
   python3 scripts/validate_catalog.py --update-lock
   python3 scripts/build_catalog.py
   python3 -m unittest discover -s tests -v
   python3 scripts/build_catalog.py --check
   git diff --check
   ```

5. Revise e faça commit de fontes, `packages.lock.json` e `dist/`. Não faça push
   sem autorização explícita do proprietário.

Versões registradas são imutáveis, incluindo manifest, código, licença e metadados.
Correções exigem nova versão; nunca remova versões anteriores. O lock guarda hashes
de todos os arquivos de cada versão e é comparado com `HEAD`. CI compara também
com o commit anterior/base do PR, detectando reescrita coordenada de fonte e lock.

Metadados permitidos: `manifest.json`, `LICENSE`, `README`, `README.md`, `README.txt`,
`UPSTREAM.json`. Symlinks, subdiretórios, arquivos extras, campos desconhecidos e
chaves JSON repetidas são rejeitados. O validador implementa os recursos de JSON
Schema usados neste projeto e verificações semânticas adicionais.

## Pacotes

| Pacote | Versão do catálogo | Origem | Licença |
| --- | --- | --- | --- |
| oled-pintor | 1.0.0 | Cópia local exata do ProjetoARCA | MIT |
| ssd1306 | 1.0.0 | MicroPython/micropython-lib, upstream 0.1.0 | MIT |
| microarca-teste | 1.0.0 | Funções simples do Projeto ARCA para testar a IDE | MIT |

`microarca-teste` não tem dependências nem acesso a hardware. Instala
`lib_microarca_teste.py`, com `ola`, `somar`, `dobrar`, `eh_par` e `contar_ate`.
[Exemplos de uso](packages/microarca-teste/1.0.0/README.md).

`oled-pintor` depende de `ssd1306==1.0.0`. `math`, `machine`, `micropython`,
`framebuf` e `time` vêm do firmware. A compatibilidade declarada visa MicroPython >=1.24 e
ESP32_GENERIC; ensaio físico com ESP32/OLED ainda é necessário.
Proveniência: [OLED](packages/oled-pintor/1.0.0/README.md) e
[SSD1306](packages/ssd1306/1.0.0/README.md). Licenças também acompanham `dist/`.

## Publicação

Com working tree limpo e tudo commitado:

```bash
bash scripts/deploy.sh --dry-run --cloudflare
```

O dry-run roda testes, validação e build local; não abre SSH nem escreve na VPS.
Prepare a infraestrutura conforme [deploy/README.md](deploy/README.md), mostrando
diff exato e backups e obtendo a confirmação única exigida antes de alterar
Compose/Caddy. Depois de DNS, infraestrutura e autorização:

```bash
bash scripts/deploy.sh --cloudflare
python3 scripts/verify_public.py
```

O script transfere via rsync/SSH para diretório temporário, verifica integridade
e imutabilidade, promove para `releases/<commit>` e troca `current` atomicamente.
Releases antigos são mantidos. Não configura DNS, Caddy, Compose ou containers.
Se HTTPS final falhar, o release permanece para diagnóstico;
use o [rollback](deploy/rollback.md).

O usuário configurou `libs-microarca` como CNAME para `traceedu.com.br`, com proxy
Cloudflare. `--cloudflare` valida os IPs públicos contra o destino aprovado e as
redes oficiais Cloudflare; sem essa opção, exige IP direto da VPS. Em ambos os
casos a verificação pública de HTTPS/conteúdo é obrigatória após a ativação.

## Estrutura

```text
packages/                 manifests, bibliotecas, licenças, proveniência
packages.lock.json        hashes das versões imutáveis
schemas/                  contratos JSON
scripts/                  validação, build, deploy, verificação HTTPS
tests/                    unittest e falhas de build/deploy/rollback
dist/v1/                  catálogo e arquivos públicos
deploy/                   snippet Caddy e procedimentos operacionais
docs/                     contrato Android, segurança, publicação
.github/workflows/        CI sem secrets ou deploy automático
IA_SPEC.md                especificação original
```

## Migração

Copie releases e `current`, mantendo bytes e caminhos. Configure DNS/TLS/Caddy na
nova VPS. Altere o endpoint raiz no app, o alias SSH em `deploy.sh` e os nomes
`DOMAIN`/`CNAME_TARGET` em `scripts/check_dns.py`; execute
`verify_public.py --url https://novo-dominio/v1/catalog.json`.
Nenhum pacote ou catálogo precisa ser regenerado: URLs são relativas ao catálogo.
Mantenha uma janela de coexistência e valide o destino antes de desligar a origem.

Detalhes: [contrato do cliente](docs/client-contract.md),
[publicação](docs/publishing.md) e [segurança](docs/security.md).
