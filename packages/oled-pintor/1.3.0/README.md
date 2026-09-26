# Pintor OLED

Derivada de `oled-pintor` 1.2.0. O código MicroPython permanece equivalente;
o manifesto visual agora permite ligar texto, número ou valor lógico à entrada
do bloco "Escrever texto". O método `escreve` já converte o valor recebido com
`str`, portanto a mudança não altera a API Python nem o comportamento elétrico.

Licença MIT do Projeto ARCA adotada para esta distribuição.
Importa `math`, `machine.Pin`, `machine.I2C` do firmware e `ssd1306` do catálogo.
A revisão cobre sintaxe e importações; funcionamento elétrico e desenho precisam
de ensaio em ESP32 e OLED reais.

