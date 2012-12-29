.. _{{ label }}:

{{ title }}
{{ '=' * (title|count) }}

.. container:: pkg-toc
{% for srcpkg in pkgs|sort %}
  {{ srcpkg }}
{%- for binpkg in srcdb[srcpkg].binary|sort %}
    * :ref:`{{ binpkg }} <binary_pkg_{{ binpkg }}>` ({{ bindb[binpkg].short_description }})
{%- endfor %}
{% endfor -%}

