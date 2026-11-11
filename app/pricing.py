"""Price normalization shared by API ingestion and video captions."""
from math import isfinite


def positive_price(value):
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return price if isfinite(price) and price > 0 else None


def card_price(card):
    for key in ('marketPrice', 'midPrice'):
        price = positive_price(card.get(key))
        if price is not None:
            return price
    return None


def format_card_price(card):
    price = card_price(card)
    if price is None:
        return 'Price unavailable'
    currency = card.get('currency') or 'USD'
    symbol = {'EUR': '€', 'USD': '$', 'GBP': '£'}.get(currency)
    return f'{symbol}{price:.2f}' if symbol else f'{price:.2f} {currency}'
