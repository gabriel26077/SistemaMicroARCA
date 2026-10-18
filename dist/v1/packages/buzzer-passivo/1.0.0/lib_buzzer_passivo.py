"""Buzzer passivo: notas e frequencias usando PWM do MicroPython."""
from machine import Pin, PWM
import time

_buzzers = {}
_NOTAS = {
    "C": 0, "DO": 0, "C#": 1, "DO#": 1,
    "D": 2, "RE": 2, "D#": 3, "RE#": 3,
    "E": 4, "MI": 4, "F": 5, "FA": 5,
    "F#": 6, "FA#": 6, "G": 7, "SOL": 7,
    "G#": 8, "SOL#": 8, "A": 9, "LA": 9,
    "A#": 10, "LA#": 10, "B": 11, "SI": 11,
}


def _inteiro(valor, minimo, maximo, nome):
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        raise ValueError(nome + " deve ser inteiro")
    if not minimo <= valor <= maximo or int(valor) != valor:
        raise ValueError(nome + " fora do intervalo permitido")
    return int(valor)


def frequencia_nota(nota, oitava=4):
    """Dó central = C4; Lá4 = 440 Hz. Aceita C/C#... ou Do/Do#..."""
    if not isinstance(nota, str):
        raise ValueError("Nota deve ser texto")
    nome = nota.strip().upper()
    for acento, simples in (("Ó", "O"), ("É", "E"), ("Á", "A")):
        nome = nome.replace(acento, simples)
    if nome not in _NOTAS:
        raise ValueError("Nota desconhecida: " + nota)
    oitava = _inteiro(oitava, 0, 8, "Oitava")
    midi = 12 * (oitava + 1) + _NOTAS[nome]
    return int(440 * 2 ** ((midi - 69) / 12) + 0.5)


class Buzzer:
    def __init__(self, pino):
        pino = _inteiro(pino, 0, 33, "Pino")
        if pino not in (0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33):
            raise ValueError("Pino indisponivel para saida no ESP32 classico")
        anterior = _buzzers.get(pino)
        if anterior is not None:
            anterior.fechar()
        self.pino = pino
        self._pwm = None
        self._fechado = False
        self._pin = Pin(pino, Pin.OUT, value=0)
        _buzzers[pino] = self

    def iniciar(self, frequencia=440):
        """Inicia som continuo sem aguardar. Frequencia inteira de 1 a 20000 Hz."""
        if self._fechado:
            raise ValueError("Buzzer fechado; crie um novo buzzer")
        frequencia = _inteiro(frequencia, 1, 20000, "Frequencia")
        try:
            if self._pwm is None:
                self._pwm = PWM(self._pin, freq=frequencia, duty_u16=0)
            else:
                self._pwm.duty_u16(0)
                self._pwm.freq(frequencia)
            self._pwm.duty_u16(32768)
        except BaseException:
            self.parar()
            raise

    def parar(self):
        """Silencia e libera o canal PWM; o objeto pode tocar novamente."""
        pwm = self._pwm
        self._pwm = None
        if pwm is not None:
            try:
                pwm.duty_u16(0)
            finally:
                try:
                    pwm.deinit()
                finally:
                    self._pin.init(Pin.OUT, value=0)

    def tocar(self, frequencia=440, duracao_ms=500):
        """Toca e aguarda a duracao; silencia mesmo quando interrompido."""
        duracao_ms = _inteiro(duracao_ms, 0, 60000, "Duracao")
        try:
            self.iniciar(frequencia)
            time.sleep_ms(duracao_ms)
        finally:
            self.parar()

    def tocar_nota(self, nota="A", oitava=4, duracao_ms=500):
        self.tocar(frequencia_nota(nota, oitava), duracao_ms)

    def fechar(self):
        try:
            self.parar()
        finally:
            self._fechado = True
            if _buzzers.get(self.pino) is self:
                del _buzzers[self.pino]

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.fechar()


def criar_buzzer(pino=25):
    return Buzzer(pino)


def parar_todos():
    """Encerra todos os buzzers criados por esta biblioteca."""
    erro = None
    for buzzer in list(_buzzers.values()):
        try:
            buzzer.fechar()
        except Exception as atual:
            erro = atual
    if erro is not None:
        raise erro


def __arca_cleanup__():
    parar_todos()
