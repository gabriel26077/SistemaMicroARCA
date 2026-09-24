import math
from machine import Pin, I2C
import ssd1306

class PintorOLED:
    def __init__(self, i2c, width=128, height=64, addr=0x3C):
        self.width = width
        self.height = height
        self.display = ssd1306.SSD1306_I2C(width, height, i2c, addr=addr)

    def limpa(self):
        self.display.fill(0)

    def atualiza(self):
        self.display.show()

    def escreve(self, texto, x, y, cor=1):
        self.display.text(str(texto), int(x), int(y), cor)

    def segreta(self, x1, y1, x2, y2, cor=1):
        self.display.line(int(x1), int(y1), int(x2), int(y2), cor)

    def retangulo(self, x1, y1, x2, y2, preenchido=False, cor=1):
        x = min(int(x1), int(x2))
        y = min(int(y1), int(y2))
        w = abs(int(x2) - int(x1))
        h = abs(int(y2) - int(y1))
        if preenchido:
            self.display.fill_rect(x, y, w, h, cor)
        else:
            self.display.rect(x, y, w, h, cor)

    def circulo(self, x, y, r, cor=1):
        x0, y0, r = int(x), int(y), int(r)
        f = 1 - r
        ddF_x = 1
        ddF_y = -2 * r
        cx, cy = 0, r

        self.display.pixel(x0, y0 + r, cor)
        self.display.pixel(x0, y0 - r, cor)
        self.display.pixel(x0 + r, y0, cor)
        self.display.pixel(x0 - r, y0, cor)

        while cx < cy:
            if f >= 0:
                cy -= 1
                ddF_y += 2
                f += ddF_y
            cx += 1
            ddF_x += 2
            f += ddF_x

            self.display.pixel(x0 + cx, y0 + cy, cor)
            self.display.pixel(x0 - cx, y0 + cy, cor)
            self.display.pixel(x0 + cx, y0 - cy, cor)
            self.display.pixel(x0 - cx, y0 - cy, cor)
            self.display.pixel(x0 + cy, y0 + cx, cor)
            self.display.pixel(x0 - cy, y0 + cx, cor)
            self.display.pixel(x0 + cy, y0 - cx, cor)
            self.display.pixel(x0 - cy, y0 - cx, cor)

    def triangulo(self, x1, y1, x2, y2, x3, y3, cor=1):
        self.segreta(x1, y1, x2, y2, cor)
        self.segreta(x2, y2, x3, y3, cor)
        self.segreta(x3, y3, x1, y1, cor)

    def coracao(self, x, y, r, cor=1):
        pontos = 100
        escala = r / 16.0
        ultimo_x = None
        ultimo_y = None

        for i in range(pontos + 1):
            t = (i / pontos) * 2 * math.pi
            px = int(x + (16 * (math.sin(t) ** 3)) * escala)
            py = int(y - (13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)) * escala)

            if ultimo_x is not None:
                self.segreta(ultimo_x, ultimo_y, px, py, cor)
            ultimo_x = px
            ultimo_y = py


def criar_tela(scl=22, sda=21, largura=128, altura=64, endereco=0x3C, canal_i2c=0):
    i2c = I2C(canal_i2c, scl=Pin(scl), sda=Pin(sda))
    return PintorOLED(i2c, width=largura, height=altura, addr=endereco)
