from django import template

register = template.Library()

_EN_TO_BN = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')


@register.filter(name='bn_num')
def bn_num(value):
    """Convert ASCII digits in value to Bengali digits."""
    return str(value).translate(_EN_TO_BN)
