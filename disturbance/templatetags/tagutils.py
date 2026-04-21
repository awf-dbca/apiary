from django.template import Library
from disturbance import settings

from disturbance.sri_utils import lookup_hash

register = Library()


@register.simple_tag(takes_context=False)
def get_instance_type():
    return settings.EMAIL_INSTANCE

@register.simple_tag()
def RAND_HASH():
    return settings.RAND_HASH

@register.simple_tag()
def SRI_HASH(file):
    return lookup_hash(file)