
.. _binary_pkg_{{ pname }}:

{{ title }}

.. container:: package_info_links

  Related packages
{%- for bin in binary|sort if not bin == pname %}
    * :ref:`binary_pkg_{{ bin }}`
{%- endfor %}

  External resources
{% if homepage %}    * `Project homepage <{{ homepage }}>`_
{% endif -%}
{% if vcs_browser %}    * `Browse source code <{{ vcs_browser }}>`_
{% endif -%}
{% if nitrc_id %}    * `NITRC listing <http://www.nitrc.org/project?group_id={{ nitrc_id }}>`_
{% endif -%}
{% if neurolex_id %}    * `NeuroLex entry <http://uri.neuinfo.org/nif/nifstd/{{ neurolex_id }}>`_
{% endif %}

{{ description }}


.. container:: pkg_install_link

  `Install this package <install.html?p={{ pname }}>`_

.. container:: pkg_bugreport_link

  `Report a bug for this package <reportbug.html?p={{ pname }}>`_

.. container:: package_availability clear

  .. list-table:: Package availability
     :header-rows: 1
     :stub-columns: 1

     * - Distribution
       - Version
       - Architectures
  {%- for release in availability|dictsort %}
  {%- for version in release[1]|dictsort %}
  {%- if loop.first %}
     * - {{ release[0] }}
  {%- else %}
     * -
  {%- endif %}
       - {{ version[0] }}
       - {{ ', '.join(version[1]) }}
  {%- endfor %}
  {%- endfor %}
