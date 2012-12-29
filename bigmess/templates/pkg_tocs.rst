.. _pkg_tocs:

Repository content
==================

{% for kind, toc in toctoc|dictsort|reverse %}
By {{ kind }}
{{ '-' * (kind|count + 3) }}

{%- for label, title in toc|dictsort(by='value') %}
* :ref:`{{ label }}`
{%- endfor %}
{% endfor -%}
