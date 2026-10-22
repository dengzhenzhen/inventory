from decimal import Decimal, ROUND_HALF_UP


def cents(value):
    return int(
        (Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def micro(value):
    return int(
        (Decimal(str(value)) * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def rounded_div(value, divisor):
    return int(
        (Decimal(value) / Decimal(divisor)).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def amount(cost_micro, quantity):
    return rounded_div(cost_micro * quantity, 10_000)
