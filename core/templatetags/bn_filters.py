from django import template

register = template.Library()

_EN_TO_BN = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')


@register.filter(name='bn_num')
def bn_num(value):
    """Convert ASCII digits in value to Bengali digits."""
    return str(value).translate(_EN_TO_BN)


@register.simple_tag(takes_context=True)
def notif_title(context, notif):
    """Return Bengali title if LANG==bn and title_bn exists, else English title."""
    if context.get('LANG') == 'bn' and notif.title_bn:
        return notif.title_bn
    return notif.title


@register.simple_tag(takes_context=True)
def notif_message(context, notif):
    """Return Bengali message if LANG==bn and message_bn exists, else English message."""
    if context.get('LANG') == 'bn' and notif.message_bn:
        return notif.message_bn
    return notif.message
