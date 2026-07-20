================
Base report xlsx
================

.. |badge1| image:: https://img.shields.io/badge/maturity-Mature-brightgreen.png
    :target: https://odoo-community.org/page/development-status
    :alt: Mature
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Freporting--engine-lightgray.png?logo=github
    :target: https://github.com/OCA/reporting-engine/tree/17.0/report_xlsx
    :alt: OCA/reporting-engine

|badge1| |badge2| |badge3|

This module provides a basic report class to generate xlsx report.

**Table of contents**

.. contents::
   :local:

Installation
============

Make sure you have ``xlsxwriter`` Python module installed::

$ pip3 install xlsxwriter

For testing it is also necessary ``xlrd`` Python module installed::

$ pip3 install xlrd

Usage
=====

An example of XLSX report for partners on a module called `module_name`:

A python class ::

    from odoo import models

    class PartnerXlsx(models.AbstractModel):
        _name = 'report.module_name.report_name'
        _inherit = 'report.report_xlsx.abstract'

        def generate_xlsx_report(self, workbook, data, partners):
            for obj in partners:
                report_name = obj.name
                sheet = workbook.add_worksheet(report_name[:31])
                bold = workbook.add_format({'bold': True})
                sheet.write(0, 0, obj.name, bold)

To manipulate the ``workbook`` and ``sheet`` objects, refer to the
`documentation <http://xlsxwriter.readthedocs.org/>`_ of ``xlsxwriter``.

A report XML record ::

    <report
        id="partner_xlsx"
        model="res.partner"
        string="Print to XLSX"
        report_type="xlsx"
        name="module_name.report_name"
        file="res_partner"
        attachment_use="False"
    />

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/reporting-engine/issues>`_.
In case of trouble, please check there if your issue has already been reported.

Credits
=======

Authors
~~~~~~~

* ACSONE SA/NV
* Creu Blanca

Contributors
~~~~~~~~~~~~

* Adrien Peiffer <adrien.peiffer@acsone.eu>
* Sébastien Alix <sebastien.alix@osiell.com>
* Stéphane Bidoul <stephane.bidoul@acsone.eu>
* Enric Tobella <etobella@creublanca.es>
* Graeme Gellatly <gdgellatly@gmail.com>
* Cristian Salamea <cs@prisehub.com>
* Rod Schouteden <rod.schouteden@dynapps.be>
* Eugene Molotov <molotov@it-projects.info>
* Christopher Ormaza <chris.ormaza@forgeflow.com>

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

This module is part of the `OCA/reporting-engine <https://github.com/OCA/reporting-engine/tree/17.0/report_xlsx>`_ project on GitHub.

You are welcome to contribute.
