from django import template

register = template.Library()


@register.filter(name='get_item')
def get_item(d, key):
    """Look up `key` in dict `d` from a template."""
    if d is None:
        return None
    try:
        return d.get(key)
    except AttributeError:
        try:
            return d[key]
        except (KeyError, TypeError, IndexError):
            return None


@register.filter(name='rarity_color')
def rarity_color(rarity):
    return {
        'common':    '#6c757d',
        'rare':      '#0d6efd',
        'epic':      '#a855f7',
        'legendary': '#f59e0b',
    }.get(rarity, '#6c757d')


@register.filter(name='rarity_bg')
def rarity_bg(rarity):
    return {
        'common':    '#f3f4f6',
        'rare':      '#dbeafe',
        'epic':      '#ede9fe',
        'legendary': '#fef3c7',
    }.get(rarity, '#f3f4f6')


@register.filter(name='format_secs')
def format_secs(seconds):
    if seconds is None:
        return '—'
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return '—'
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f'{h}h {m:02d}m {s:02d}s'
    return f'{m}m {s:02d}s'


@register.filter(name='sign')
def sign(n):
    if n is None:
        return ''
    try:
        return '+' if n > 0 else ('' if n == 0 else '−')
    except TypeError:
        return ''
