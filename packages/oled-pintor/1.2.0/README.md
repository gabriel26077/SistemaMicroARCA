# Pintor OLED

Derivada de `oled-pintor` 1.1.0. O único trecho novo em `lib_oled_pintor.py` é
o método `ponto(x, y, cor=1)`, que acende um único pixel com
`display.pixel`. O restante do arquivo é idêntico, byte a byte, ao da 1.1.0,
incluindo os finais de linha mistos; o método novo usa CRLF como o código ao
redor. Pontos fora da tela são ignorados pelo `framebuf`, como nas outras
funções de desenho.

`blocks.json` adiciona o bloco "Desenhar ponto", logo após "Escrever texto",
com os mesmos blocos da 1.1.0 nas demais posições.

Licença MIT do Projeto ARCA adotada para esta distribuição.
Importa `math`, `machine.Pin`, `machine.I2C` do firmware e `ssd1306` do catálogo.
A revisão cobre sintaxe e importações; funcionamento elétrico e desenho precisam
de ensaio em ESP32 e OLED reais.
