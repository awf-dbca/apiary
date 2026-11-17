import xml.etree.ElementTree as ET

import requests
from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from disturbance.components.main.models import FileExtensionWhitelist, MapColumn, MapLayer


def check_kb_server_status():
    """
    Fetch GetCapabilities and return a tuple: (status_code, layer_names_set)
    status_code: 200 if server is reachable, None/error code if connection failed.
    Caches the result to prevent frequent network requests.
    """
    cache_key_status = "kb_geoserver_status_info"
    cached_info = cache.get(cache_key_status)
    if cached_info:
        return cached_info

    try:
        base_url = (getattr(settings, "KB_SERVER_URL", "") or "").rstrip("/")
        url = f"{base_url}/geoserver/wms?request=GetCapabilities&service=WMS"

        auth = None
        if getattr(settings, "KB_USER", None) and getattr(settings, "KB_PASSWORD", None):
            auth = (settings.KB_USER, settings.KB_PASSWORD)

        response = requests.get(url, auth=auth, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            layer_names = set()
            for elem in root.iter():
                if elem.tag.endswith("Layer"):
                    name_elem = elem.find("{*}Name")
                    if name_elem is not None and name_elem.text:
                        layer_names.add(name_elem.text.strip())

            result = (200, layer_names)
            cache.set(cache_key_status, result, 86400)
            return result
        else:
            result = (response.status_code, set())
            cache.set(cache_key_status, result, 60)
            return result
    except Exception:
        result = (None, set())
        cache.set(cache_key_status, result, 60)
        return result


class SearchableSelectWidget(forms.Select):
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        attrs["style"] = "width: 100%; box-sizing: border-box;"
        select_html = super().render(name, value, attrs, renderer)

        select_id = attrs.get("id", f"id_{name}")
        current_value = str(value) if value is not None else ""

        container_html = mark_safe(f"""
        <div style="display: flex; flex-direction: column; gap: 6px; width: 600px; max-width: 100%; clear: both;">
            <div style="display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <input type="text" id="{select_id}_search" placeholder="🔍 Type or paste to filter layers..." 
                           style="width: 280px; max-width: 100%; padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 13px;">
                    <span id="{select_id}_count" style="font-size: 12px; font-weight: bold;"></span>
                </div>
                <button type="button" id="{select_id}_toggle_btn" 
                        style="background: #f8f9fa; border: 1px solid #ccc; border-radius: 4px; padding: 5px 10px; font-size: 12px; cursor: pointer;">
                    ✏️ Enter Manually
                </button>
            </div>
            <div id="{select_id}_select_wrapper">
                {select_html}
            </div>
            <input type="text" id="{select_id}_manual_input" 
                   placeholder="Enter layer name manually (e.g. workspace:layer_name)..." 
                   value="{current_value}"
                   style="display: none; width: 100%; padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 13px;" disabled>
        </div>
        <script type="text/javascript">
        (function() {{
            // Converts "kaartdijin-boodja-public:todays_burns" -> "Todays Burns"
            function formatLayerTitle(rawName) {{
                if (!rawName) return '';
                var clean = rawName.indexOf(':') > -1 ? rawName.split(':').pop() : rawName;
                clean = clean.replace(/[-_]+/g, ' ').trim();
                return clean.replace(/\\w\\S*/g, function(txt) {{
                    return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();
                }});
            }}

            // Directly populates the display_name input
            function updateDisplayName(rawName) {{
                var displayField = document.getElementById('id_display_name');
                if (displayField) {{
                    var formatted = formatLayerTitle(rawName);
                    if (formatted) {{
                        displayField.value = formatted;
                    }}
                }}
            }}

            function setupWidget() {{
                var searchInput = document.getElementById('{select_id}_search');
                var selectElem = document.getElementById('{select_id}');
                var selectWrapper = document.getElementById('{select_id}_select_wrapper');
                var countElem = document.getElementById('{select_id}_count');
                var toggleBtn = document.getElementById('{select_id}_toggle_btn');
                var manualInput = document.getElementById('{select_id}_manual_input');
                if (!selectElem) return;

                // 1. Search input paste & filter
                if (searchInput) {{
                    searchInput.addEventListener('paste', function(e) {{
                        setTimeout(function() {{
                            updateDisplayName(searchInput.value.trim());
                        }}, 50);
                    }});

                    searchInput.addEventListener('input', function() {{
                        var filter = this.value.toLowerCase().trim();
                        var options = selectElem.options;
                        var matchCount = 0;
                        var firstMatch = null;

                        for (var i = 0; i < options.length; i++) {{
                            var text = options[i].text.toLowerCase();
                            if (filter === '' || text.indexOf(filter) > -1) {{
                                options[i].style.display = '';
                                matchCount++;
                                if (!firstMatch && filter !== '' && options[i].value !== '') {{
                                    firstMatch = options[i];
                                }}
                            }} else {{
                                options[i].style.display = 'none';
                            }}
                        }}

                        if (filter !== '') {{
                            selectElem.size = Math.min(Math.max(matchCount, 2), 6);
                            selectElem.style.height = '140px';
                            if (firstMatch) firstMatch.selected = true;
                        }} else {{
                            selectElem.size = 1;
                            selectElem.style.height = 'auto';
                        }}

                        if (countElem) {{
                            if (filter === '') {{
                                countElem.textContent = '';
                            }} else if (matchCount > 0) {{
                                countElem.textContent = '✓ ' + matchCount + ' layer(s) found';
                                countElem.style.color = '#28a745';
                            }} else {{
                                countElem.textContent = '✕ No layer found';
                                countElem.style.color = '#dc3545';
                            }}
                        }}
                    }});

                    selectElem.addEventListener('change', function() {{
                        selectElem.size = 1;
                        selectElem.style.height = 'auto';
                        updateDisplayName(selectElem.value);
                    }});
                }}

                // 2. Manual input paste & blur
                if (manualInput) {{
                    manualInput.addEventListener('paste', function(e) {{
                        setTimeout(function() {{
                            updateDisplayName(manualInput.value.trim());
                        }}, 50);
                    }});
                    manualInput.addEventListener('change', function() {{
                        updateDisplayName(manualInput.value.trim());
                    }});
                }}

                // 3. Toggle Dropdown vs Manual Input
                if (toggleBtn && manualInput) {{
                    toggleBtn.addEventListener('click', function() {{
                        var isManual = manualInput.style.display !== 'none';
                        if (isManual) {{
                            manualInput.style.display = 'none';
                            manualInput.disabled = true;
                            manualInput.removeAttribute('name');

                            selectWrapper.style.display = 'block';
                            selectElem.disabled = false;
                            selectElem.setAttribute('name', '{name}');

                            if (searchInput) searchInput.style.display = '';
                            toggleBtn.textContent = '✏️ Enter Manually';
                        }} else {{
                            selectWrapper.style.display = 'none';
                            selectElem.disabled = true;
                            selectElem.removeAttribute('name');

                            manualInput.style.display = 'block';
                            manualInput.disabled = false;
                            manualInput.setAttribute('name', '{name}');
                            if (selectElem.value) {{
                                manualInput.value = selectElem.value;
                            }}

                            if (searchInput) searchInput.style.display = 'none';
                            if (countElem) countElem.textContent = '';
                            toggleBtn.textContent = '📋 Select from List';
                            manualInput.focus();
                        }}
                    }});
                }}
            }}

            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', setupWidget);
            }} else {{
                setupWidget();
            }}
        }})();
        </script>
        """)
        return container_html


class MyForm(forms.ModelForm):
    layer_name = forms.CharField(
        required=True,
        help_text="Select a layer from KB GeoServer GetCapabilities or enter manually",
    )

    display_name = forms.CharField(
        required=True,
        help_text="This will be the display name for the layer in the UI. It can be auto-generated from the layer name or entered manually.",
    )

    class Meta:
        model = MapLayer
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        status_code, layer_names = check_kb_server_status()

        if status_code == 200:
            layer_choices = [("", "-- Select a Layer --")]
            for name in sorted(layer_names):
                layer_choices.append((name, name))

            current_layer = self.instance.layer_name if self.instance and self.instance.layer_name else None
            existing_keys = {c[0] for c in layer_choices}
            if current_layer and current_layer not in existing_keys:
                layer_choices.append((current_layer, f"{current_layer} (Current / Unlisted)"))

            self.fields["layer_name"].widget = SearchableSelectWidget(choices=layer_choices)
            self.fields[
                "layer_name"
            ].help_text = "Select a layer from KB GeoServer GetCapabilities or click 'Enter Manually'."
        else:
            # Fallback when GeoServer is unreachable:
            # TextInput directly updates 'id_display_name' on paste or blur
            self.fields["layer_name"].widget = forms.TextInput(
                attrs={
                    "class": "vTextField",
                    "placeholder": "e.g. workspace:layer_name",
                    "style": "width: 500px; max-width: 100%; padding: 6px 10px; border: 1px solid #ccc; border-radius: 4px;",
                    "onpaste": (
                        "setTimeout(function() {"
                        "  var val = this.value || '';"
                        "  var clean = val.indexOf(':') > -1 ? val.split(':').pop() : val;"
                        "  clean = clean.replace(/[-_]+/g, ' ').trim();"
                        "  var title = clean.replace(/\\w\\S*/g, function(t) { return t.charAt(0).toUpperCase() + t.substr(1).toLowerCase(); });"
                        "  var target = document.getElementById('id_display_name');"
                        "  if (target && title) target.value = title;"
                        "}.bind(this), 50);"
                    ),
                    "onchange": (
                        "var val = this.value || '';"
                        "var clean = val.indexOf(':') > -1 ? val.split(':').pop() : val;"
                        "clean = clean.replace(/[-_]+/g, ' ').trim();"
                        "var title = clean.replace(/\\w\\S*/g, function(t) { return t.charAt(0).toUpperCase() + t.substr(1).toLowerCase(); });"
                        "var target = document.getElementById('id_display_name');"
                        "if (target && title && !target.value) target.value = title;"
                    ),
                }
            )
            err_detail = f"HTTP {status_code}" if status_code else "Connection failed"
            self.fields["layer_name"].help_text = mark_safe(
                f'<span style="color: #dc3545; font-weight: bold;">⚠️ GeoServer GetCapabilities is currently unavailable ({err_detail}).</span> '
                "You can enter the layer name manually."
            )

        # Restore original help texts
        if "display_all_columns" in self.fields:
            self.fields[
                "display_all_columns"
            ].help_text = (
                "When checked, display all the attributes(columns) in the table regardless of the configurations below"
            )
        if "option_for_internal" in self.fields:
            self.fields[
                "option_for_internal"
            ].help_text = "When checked, a checkbox for this layer is displayed for the internal user"
        if "option_for_external" in self.fields:
            self.fields[
                "option_for_external"
            ].help_text = "When checked, a checkbox for this layer is displayed for the external user"


class MapColumnInline(admin.TabularInline):
    model = MapColumn
    extra = 0


@admin.register(MapLayer)
class MapLayerAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "layer_name",
        "server_status",
        "option_for_internal",
        "option_for_external",
        "display_all_columns",
        "column_names",
    ]
    # Ensures layer_name appears first at the top of the form
    fields = [
        "layer_name",
        "display_name",
        "option_for_internal",
        "option_for_external",
        "display_all_columns",
        "cache_expiry",
    ]
    list_filter = ["option_for_internal", "option_for_external", "display_all_columns"]
    search_fields = ["display_name", "layer_name", "columns__name"]
    form = MyForm
    inlines = [MapColumnInline]

    actions = ["refresh_server_status"]

    @admin.action(description="Force refresh KB GeoServer status cache")
    def refresh_server_status(self, request, queryset):
        """
        Action to clear the cached GetCapabilities and force re-fetching from KB GeoServer.
        """
        cache.delete("kb_geoserver_status_info")
        check_kb_server_status()  # Immediately re-fetch from KB GeoServer
        self.message_user(request, "KB GeoServer status cache refreshed successfully.")

    kb_url = getattr(settings, "KB_SERVER_URL", "").rstrip("/")

    @admin.display(
        description=mark_safe(
            f"<span style='display: block !important; margin: 0 !important; padding: 0 !important; line-height: 1.0 !important; text-transform: none !important; text-align: left !important;'>"
            f"<span style='display: block !important; margin: 0 !important; padding: 0 !important; line-height: 1.0 !important; text-transform: uppercase;'>KB Server Status</span>"
            f"<span style='display: block !important; margin: 2px 0 0 0 !important; padding: 0 !important; line-height: 1.0 !important; font-weight: normal; font-size: 0.85em; opacity: 0.8;'>({kb_url})</span>"
            f"</span>"
        )
    )
    def server_status(self, obj):
        if not obj.layer_name:
            return format_html('<span style="color: gray;">⚪ Empty</span>')

        base_url = (getattr(settings, "KB_SERVER_URL", "") or "").rstrip("/")
        status_code, layer_names = check_kb_server_status()

        # Connection failed or server error
        if status_code != 200:
            return format_html(
                '<span style="color: orange; font-weight: bold;" title="Failed connecting to {} (Status: {})">🟡 Server Error ({})</span>',
                base_url,
                status_code if status_code else "Offline",
                status_code if status_code else "Offline",
            )

        # Server connected, check if layer exists
        if obj.layer_name in layer_names:
            return format_html(
                '<span style="color: green; font-weight: bold;" title="Connected to {}">🟢 Found</span>', base_url
            )
        else:
            return format_html(
                '<span style="color: red; font-weight: bold;" title="Connected to {} but layer is missing">🔴 Not Found</span>',
                base_url,
            )


@admin.register(FileExtensionWhitelist)
class FileExtensionWhitelistAdmin(admin.ModelAdmin):
    fields = (
        "name",
        "model",
    )
    list_display = (
        "name",
        "model",
    )
    form = forms.ModelForm
