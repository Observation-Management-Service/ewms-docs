Event Workflow Management System — EWMS
===============
The Event Workflow Management System improves task scheduling and management by integrating fine-grained event handling with large-scale scientific computing.

EWMS is a workflow management system built on `HTCondor <https://htcondor.readthedocs.io/en/latest/>`__ designed to process billions of fine-grained events. By optimizing scheduling and fitting work units into smaller resource envelopes, it increases throughput, reduces costs, and ensures efficient data transfer pipelines.

Getting Started
----------

The best place to start is the :doc:`Workflow Management Service <services/wms>` page.
This details the public-facing interface for EWMS, and covers the full workflow lifetime,
key concepts, and example requests.

For API endpoints and object schemas, see:

- :doc:`API Endpoints <apis/wms>`
- :doc:`Object Glossary <apis/_generated/wms-objects>`



.. toctree::
   :hidden:
   :caption: APIs

   apis/wms
   apis/_generated/wms-objects
   apis/mqs
   apis/_generated/mqs-objects

.. toctree::
   :hidden:
   :caption: Services

   services/wms
   services/mqs

.. toctree::
   :hidden:
   :caption: Client Libraries

   libraries/mqclient

.. toctree::
   :hidden:
   :caption: Internal Components

   internal/tms
   internal/pilot

.. toctree::
   :hidden:
   :caption: Publications

   Event Workflow Management System (2025) <https://dl.acm.org/doi/10.1145/3708035.3736051>
   IceCube SkyDriver (2024) <https://www.epj-conferences.org/articles/epjconf/abs/2024/05/epjconf_chep2024_04023/epjconf_chep2024_04023.html>
