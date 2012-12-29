.. _{{ label }}:

{{ title }}
{{ '=' * (title|count) }}

.. container:: pkg-toc
{% for p in pkgs|sort %}
  * :ref:`{{ p }} <binary_pkg_{{ p }}>` ({{ db[p].short_description }})
{%- endfor %}

