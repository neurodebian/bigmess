
.. _chap_mirrors_stats:

Mirrors status and availability
===============================

.. container:: mirrors_stats_table clear

  .. list-table::
     :header-rows: 1
     :stub-columns: 1
     :widths: 10 40 30 20

     * - Mirror
       - Location
       - Age
       - Status
  {%- for mirror, i in info|dictsort %}
     * - `{{ mirror }} <{{ i[0] }}>`__
       - {{ i[1] }}
       - {{ i[3] }}
       - {{ i[4] }}
  {%- endfor %}

