# Pintor OLED

Cópia exata de `ProjetoARCA/embedded/lib_oled_pintor.py` do workspace indicado.
SHA-256: `82623d73823719c5fa7a2afcc956eacc44de9aaefb2b8896d64d4c3d1dcb1d90`.
O repositório de origem estava em `9b86d17f0205e1f95d46cfb1fdf24803eda0e9d5`,
mas o arquivo tinha alterações locais. O hash acima identifica a cópia efetiva;
não se afirma que o arquivo corresponde ao commit. Nenhum arquivo do ProjetoARCA
foi alterado. Finais de linha mistos foram preservados.

Licença MIT do Projeto ARCA adotada para esta distribuição.
Importa `math`, `machine.Pin`, `machine.I2C` do firmware e `ssd1306` do catálogo.
O método `segreta` foi preservado como está. A revisão cobre sintaxe e importações;
funcionamento elétrico e desenho precisam de ensaio em ESP32 e OLED reais.

Esta versão adiciona `blocks.json` com blocos declarativos para criar, limpar e
atualizar a tela, escrever texto e desenhar linha, retângulo, círculo e coração.
O manifesto é interpretado pela IDE e não contém JavaScript executável.
