
.. _binary_pkg_{{ pname }}:

{{ title }}

.. container:: package_info_links

{% for bin in binary|sort if not bin == pname %}
{%- if loop.first %}
  Related packages
{%- endif %}
    * :ref:`{{ bin }} <binary_pkg_{{ bin }}>`
{%- endfor %}

{% if havemeta_copyright %}
  More information
    * `License <{{ cfg.get('metadata', 'source extracts baseurl') }}/{{ src_name }}/copyright>`_
{% if havemeta_README_Debian %}    * `Must know! <{{ cfg.get('metadata', 'source extracts baseurl') }}/{{ src_name }}/README.Debian>`_
{% endif -%}
{% endif %}
  External resources
{% if homepage %}    * `Project homepage <{{ homepage }}>`_
{% endif -%}
{% if 'Contact' in upstream %}    * `Project contact <{{ upstream.Contact }}>`_
{% endif -%}
{% if 'FAQ' in upstream %}    * `FAQ <{{ upstream.FAQ }}>`_
{% endif -%}
{% if 'Other-References' in upstream %}    * `More references <{{ upstream['Other-References'] }}>`_
{% endif -%}
{% if vcs_browser %}    * `Browse source code <{{ vcs_browser }}>`_
{% endif -%}
{% if upstream and 'Also-Known-As' in upstream %}
  Info on other portals
{% if upstream['Also-Known-As'].NeuroLex %}    * `NeuroLex <http://uri.neuinfo.org/nif/nifstd/{{ upstream['Also-Known-As'].NeuroLex }}>`_
{% endif -%}
{% if upstream['Also-Known-As'].NITRC %}    * `NITRC <http://www.nitrc.org/project?group_id={{ upstream['Also-Known-As'].NITRC }}>`_
{% endif -%}
{% endif %}

{% if component == 'non-free' -%}
.. container:: license-reminder

  [Note: non-standard licensing terms -- please verify license compliance]
{% endif %}

{{ description }}

{% if 'Registration' in upstream -%}
{%- if upstream.Registration.startswith('http') -%}
The software authors ask users to `register <{{ upstream.Registration }}>`_.
Available user statistics might be helpful to acquire funding for this project
and therefore foster continued development in the future.

{%- else -%}
.. raw:: html

  {{ upstream.Registration }}

{% endif %}
{% endif %}
{% if 'Donation' in upstream -%}
{%- if upstream.Donation.startswith('http') -%}
.. note::

  For information on how to donate to this project, please visit
  `this page <{{ upstream.Donation }}>`_.

{%- else -%}
.. raw:: html

  {{ upstream.Donation }}

{% endif %}
{% endif %}


.. container:: pkg_install_link

  `Install this package </install_pkg.html?p={{ pname }}>`_

.. container:: pkg_bugreport_link

  `Report a bug </reportbug.html?p={{ pname }}>`_

{% if 'Cite-As' in upstream -%}
.. raw:: html

  {{ upstream.Cite-As }}

{% elif 'Reference' in upstream -%}
{%- if upstream.Reference|count > 1 %}
References:
{%- else %}
Reference:
{%- endif %}
{%- for ref in upstream.Reference %}
  {{ ', '.join(ref.Author.split(' and ')) }} ({{ ref.Year }}).
  {{ ref.Title }}. *{{ ref.Journal }}, {{ ref.Volume }}*, {{ ref.Pages }}.
{%- if ref.URL %} [`Abstract <{{ ref.URL }}>`_]{% endif %}
{%- if ref.Eprint %} [`Eprint <{{ ref.Eprint }}>`_]{% endif %}
{%- if ref.DOI %} [`DOI <http://dx.doi.org/{{ ref.DOI }}>`_]{% endif %}
{%- if ref.PMID %} [`Pubmed <http://www.ncbi.nlm.nih.gov/pubmed/{{ ref.PMID }}>`_]{% endif %}

{% endfor -%}
{% endif -%}

.. container:: package_availability clear

  .. list-table:: Package availability chart
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
