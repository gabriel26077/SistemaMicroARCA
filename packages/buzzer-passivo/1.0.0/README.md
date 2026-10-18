# Buzzer passivo

Biblioteca do Projeto ARCA para ESP32 clássico e MicroPython >=1.24.
Usa PWM de 50% para produzir notas ou frequências inteiras de 1 a 20000 Hz.
A resposta sonora depende do buzzer; a faixa aceita não garante som audível em toda frequência.

## Python

~~~python
from lib_buzzer_passivo import criar_buzzer

with criar_buzzer(25) as buzzer:
    buzzer.tocar_nota("Dó", 4, 300)
    buzzer.tocar_nota("E", 4, 300)
    buzzer.tocar(440, 500)
    buzzer.iniciar(880)
    # Outras ações podem acontecer enquanto o som continua.
    buzzer.parar()
~~~

tocar e tocar_nota aguardam a duração em milissegundos (0 a 60000).
iniciar continua imediatamente; parar silencia e libera o canal.
fechar encerra o objeto; use criar_buzzer para criar outro.
As notas aceitam C, C#, D, D#, E, F, F#, G, G#, A, A#, B ou
Do, Re, Mi, Fa, Sol, La, Si (também acentuadas), com sustenidos.
A oitava vai de 0 a 8: C4 é o Dó central; A4 é 440 Hz.

## Blocos e encerramento

Cinco blocos: criar, tocar nota com seletor, tocar frequência, iniciar som e parar.
Requer app com suporte ao campo declarativo dropdown.
O app atualizado chama __arca_cleanup__ ao terminar ou interromper projetos Python.
Nos blocos, o Python gerado também usa finally para desligar o som.
Para projetos Python gravados executarem essa limpeza ao ligar, atualize arca_files.py
com o suporte a hooks de limpeza. Fora do MicroARCA, use with ou try/finally.

## Uso dos pinos

Escolha um GPIO de saída adequado ao circuito. Pinos 34 a 39 não são saídas;
pinos reservados à memória são rejeitados. Confira a pinagem da sua placa.
Use circuito de acionamento compatível com a corrente e tensão do buzzer.
Não controle o mesmo pino simultaneamente pelos blocos Pinos e pela biblioteca.
Canais PWM podem compartilhar recursos de frequência; valide a combinação com
outros dispositivos PWM no kit. Não há controle de volume nesta versão.

Testes automatizados usam hardware simulado; validar som e interrupção na placa.
