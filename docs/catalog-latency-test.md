# Teste de publicação: microarca-teste 1.0.0

Publicado em 23/09/2026, release `4f7454ef3afa48f0414d0184379d8a442703af1f`.

Biblioteca sem dependências/hardware, com `ola`, `somar`, `dobrar`, `eh_par` e
`contar_ate`. Instala `lib_microarca_teste.py` em `/lib`.

- [Catálogo](https://libs-microarca.traceedu.com.br/v1/catalog.json)
- [Módulo](https://libs-microarca.traceedu.com.br/v1/packages/microarca-teste/1.0.0/lib_microarca_teste.py)
- [Exemplos](../packages/microarca-teste/1.0.0/README.md)

## Resultado observado

| Marco | Segundos desde o início do deploy |
| --- | --- |
| Confirmação de ativação recebida via SSH | 7,091 |
| Primeira resposta pública contendo o novo pacote | **8,307** |
| Deploy concluído, incluindo verificação dos downloads | 10,367 |

A nova versão foi detectada cerca de 1,2 segundo depois da confirmação de
ativação. O intervalo de polling foi de 1 segundo entre requisições; isso mede
quando a atualização foi observada por este cliente, não o instante exato de
propagação global. O tempo de criação, commit, push e aprovações não entra nesses
números; o cronômetro começou ao executar o deploy.

O monitor enviou `If-None-Match` com o ETag do catálogo anterior, sem query de
cache-busting ou purge. Recebeu 304 até 7,013 s, depois HTTP 200 com novo ETag e
`Cache-Control: no-cache`. O novo pacote estava ausente antes da publicação.

**62 testes passaram**, as cinco funções foram exercitadas localmente e o CI
do commit passou. HTTPS, catálogo, licenças, tamanhos e SHA-256 dos três módulos
foram verificados após o deploy. Os sete containers mantiveram IDs e StartedAt.
O release anterior permanece disponível para rollback.

[Medições brutas](catalog-latency-test.json). A publicação é manual pelo script;
commit/push isolados continuam sem atualizar a VPS automaticamente.
