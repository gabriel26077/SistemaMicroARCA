"""Funcoes simples para testar download e instalacao pelo catalogo MicroARCA."""


def ola(nome="MicroARCA"):
    """Retorna uma saudacao, sem imprimir nem acessar hardware."""
    return "Ola, " + str(nome) + "!"


def somar(a, b):
    """Retorna a soma de dois numeros."""
    return a + b


def dobrar(numero):
    """Retorna o dobro de um numero."""
    return numero * 2


def eh_par(numero):
    """Retorna True quando o inteiro e par."""
    return numero % 2 == 0


def contar_ate(limite=5):
    """Retorna os inteiros de 1 ate limite; limite menor que 1 gera lista vazia."""
    return list(range(1, limite + 1))
