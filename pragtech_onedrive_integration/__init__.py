from . import controller

# -*- coding: utf-8 -*-
{
    'name': 'Odoo OneDrive Integration',
    'version': '11.0',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'category': 'Sales',
    'description': """Odoo OneDrive Integration""",
    'depends': ['base', 'document'],
    'data': [
        'views/res_company_view.xml',
        'views/ir_attachment_view.xml',
        'data/onedrive_cron.xml',
    ],
    'images': ['images/odoo-onedrivemain.png'],
    'license': 'OPL-1',
    'price': 99,
    'currency': 'EUR',
    'active': False,
    'installable': True,
}


from . import models