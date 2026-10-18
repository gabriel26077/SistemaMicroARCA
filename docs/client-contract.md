# Contrato do cliente Android — schema 1

Endpoint: `https://libs-microarca.traceedu.com.br/v1/catalog.json`. Resolver URLs
em relação ao catálogo: `packages/ssd1306/1.0.0/ssd1306.py` fica em `/v1/packages/...`.

## Rede e cache

- HTTPS obrigatório, validação de certificado e hostname com a trust store do
  sistema. Nesta versão rejeitar redirecionamentos e URLs de outra origem; nunca
  aceitar downgrade para HTTP.
- Identificar o cliente com `User-Agent: MicroARCA/<versão>`. O proxy Cloudflare
  rejeitou o User-Agent genérico do urllib com HTTP 403/erro 1010; o identificador
  explícito do MicroARCA foi aceito. Não fingir ser navegador nem tratar User-Agent
  como autenticação. Respostas de bloqueio/desafio não são catálogos válidos.
- Timeout de conexão: 10 s; leitura: 15 s por operação; prazo total: 60 s por
  requisição. Cancelamento do usuário interrompe a transferência.
- Catálogo limitado a 1 MiB descomprimido: conferir Content-Length quando presente
  e limitar durante a leitura. Rejeitar UTF-8/JSON inválido, chaves duplicadas e
  schema desconhecido. Limites se aplicam sem Content-Length também.
- Gravar atomicamente último catálogo válido com ETag e endpoint de origem.
  Usar `If-None-Match`; resposta 304 só é aproveitada com cache validado. Sem
  ETag, buscar novamente. Separar caches de endpoints diferentes.
- Offline: mostrar último catálogo válido com aviso. Instalar apenas se todos
  os arquivos estiverem em cache e passarem novamente por tamanho e SHA-256.

## Validação e resolução

Validar `schemas/catalog.schema.json` e regras semânticas: IDs/versões únicos,
SemVer X.Y.Z, nomes ASCII Python e lista reservada em `docs/security.md`.
Rejeitar `/`, `\\`, `..` e controles em nomes. Nas URLs rejeitar caminhos absolutos,
esquema/host, query, fragment e escapes percentuais. Exigir caminho exato
`packages/<id>/<version>/<name>`. Não confiar apenas nas verificações do servidor.

Arquivos têm tamanho 0..65.536 e SHA-256 hexadecimal de 64 caracteres. São instalados
diretamente em `/lib`. `license_url` obrigatório e `provenance_url` opcional são
metadados para exibição, não código instalado. `generated_at` é omitido.

`blocks` é opcional e contém URL, tamanho e SHA-256 de `blocks.json`. Exigir
HTTPS, mesma origem e o caminho exato
`packages/<id>/<version>/blocks.json`, com limite de 65.536 bytes. Validar o
manifesto contra `schemas/blocks.schema.json` e conferir que ID/versão coincidem
com o pacote. O arquivo fica no celular e nunca é transferido ao ESP32.

O manifesto de blocos é somente declarativo: rótulos, campos limitados e templates
de uma linha para gerar MicroPython. Não aceitar JavaScript, HTML, URLs adicionais,
callbacks ou hooks. A IDE interpreta os dados com código próprio empacotado no APK;
nunca usa `eval` nem executa conteúdo do catálogo na WebView.

Campos `value` aceitam somente os tipos básicos exibíveis `String`, `Number` e
`Boolean`; não significam um valor arbitrário nem removem a tipagem das demais
entradas. A IDE deve usar o tipo do valor padrão para criar o bloco sombra inicial.

Verificar placa e versão MicroPython. A versão mínima aceita apenas `>=1.N` ou
`>=1.N.P`; não há resolvedor geral de ranges. Dependências são exatas. Resolver
todo o fecho transitivo antes de baixar; rejeitar ausentes, ciclos, duas versões
do mesmo ID e colisões entre pacotes (inclusive comparação sem distinguir caixa).
O catálogo pode conter várias versões de um ID; apenas uma fica instalada.

## Download e instalação

1. Mostrar plano com versões, dependências, arquivos e licença. Pedir confirmação
   antes de atualizar/remover, inclusive mudanças de dependências já instaladas.
2. Baixar tudo para área temporária do app. Conferir tamanho declarado e
   Content-Length antes de ler, limitar bytes durante a leitura e conferir tamanho
   exato e SHA-256 ao terminar. Não normalizar código/finais de linha antes do hash.
3. Se qualquer dependência/arquivo falhar, cancelar tudo antes de escrever no ESP32.
   Nunca instalar parcialmente um pacote por falha de dependência.
4. Instalar dependências em ordem topológica antes do dependente. Conferir espaço,
   guardar arquivos anteriores, usar temporários/rename quando suportado e impedir
   execução dos módulos durante a troca.
5. Manter journal persistente e validar bytes no dispositivo. Falha de escrita
   exige restauração; desconexão exige recuperação ao reconectar antes de executar.
   Não assumir transação multi-arquivo nativa do filesystem do ESP32.
6. Só confirmar instalação depois de todos os arquivos. Registrar por dispositivo
   ID, versão, hashes, arquivos, dependências e origem. Contar referências de uso:
   não remover arquivo/dependência ainda usado por outro pacote; bloquear remoção
   ou apresentar plano incluindo dependentes.

Blocos de biblioteca aparecem depois que o pacote completo, incluindo
`blocks.json`, foi baixado e validado. O workspace registra os pares
`id@versão` usados. Antes de executar, conferir o registro do ESP32 conectado e
pedir a instalação das versões ausentes.

## Confiança

MicroPython é código executável potencialmente perigoso, capaz de alterar periféricos
e dados. Somente bibliotecas revisadas pelo mantenedor nesta fase; AST válido não
prova segurança ou funcionamento.

SHA-256 detecta corrupção/inconsistência, não comprometimento simultâneo de servidor
e catálogo. Evolução futura: assinatura Ed25519 com chave privada fora da VPS e
chave pública embutida no app, incluindo rotação, revogação e proteção anti-replay.
Esta versão não implementa nem simula assinaturas. HTTPS não impede replay sozinho.

## Seletores declarativos de bibliotecas

Um campo de bloco pode usar type dropdown, default string e options com
1 a 32 pares [rótulo, valor]. Cada string tem 1 a 64 caracteres; os valores
são únicos e o padrão precisa estar nas opções. min/max não são permitidos.
O app deve gerar o valor selecionado como literal string Python escapado,
nunca como código. Tipos de campo anteriores não aceitam options.
Apps sem esse suporte rejeitam o manifesto; atualizar o app antes de usar
os blocos do pacote buzzer-passivo.
