"""Filtros de plantilla propios del proyecto (JO4)."""
from django import template

register = template.Library()


def formato_clp(valor):
    """15000 -> '$15.000' (pesos chilenos, punto como separador de miles)."""
    try:
        numero = int(round(float(valor or 0)))
    except (TypeError, ValueError):
        return '$0'
    signo = '-' if numero < 0 else ''
    return f'{signo}${abs(numero):,}'.replace(',', '.')


register.filter('clp', formato_clp)
