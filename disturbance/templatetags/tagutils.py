from django.template import Library
from disturbance import settings
import json
import os
from django.utils.html import format_html, format_html_join

register = Library()

@register.simple_tag(takes_context=False)
def get_instance_type():
    return settings.EMAIL_INSTANCE

@register.simple_tag()
def RAND_HASH():
    return settings.RAND_HASH

@register.simple_tag
def vite_asset_sri(entry):

    manifest_path = os.path.join(settings.BASE_DIR, "staticfiles_ds", "manifest.json")    
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    asset = manifest[entry]
    base_url = settings.STATIC_URL + "disturbance_vue/"

    parts = []

    for css in asset.get("css", []):
        parts.append(
            format_html(
                '<link rel="stylesheet" href="{}">',
                base_url + css,
            )
        )

    parts.append(
        format_html(
            '<script type="module" src="{}" integrity="{}" crossorigin="anonymous"></script>',
            base_url + asset["file"],
            asset["integrity"],
        )
    )

    return format_html_join("", "{}", ((p,) for p in parts))

