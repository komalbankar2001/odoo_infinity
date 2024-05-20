# -*- coding: utf-8 -*-
{
    'name': 'Odoo OneDrive Integration',
    'version': '14.0.2',
    'category': 'Services',
    'author': 'Pragmatic TechSoft Pvt Ltd.',
    'website': 'http://www.pragtech.co.in',
    'summary': 'Odoo OneDrive Integration odoo app odoo onedrive integration odoo onedrive connector odoo onedrive app',
    'description': """
Odoo OneDrive Integration
=========================
Current Features of Odoo OneDrive Integration
---------------------------------------------
    * Automatic Synchronization: Files synchronized automatically between Onedrive and Odoo. No manual intervention is required.
    * Two-ways Synchronization: In this module synchronization is bilateral. Files which are placed over Onedrive can be easily accessible through Odoo. Similarly once the attachment is placed over Odoo, it will sync the data and data is available over Onedrive.
    * File Support: Synced attachment in Odoo opens via URL to OneDrive file. Preview of these documents depends on OneDrive configurations. For instance, if user is using Office 365, the files will be opened immediately using Word or Excel.
    * Systematic Folder: OneDrive is used for business and sharepoint purpose. The files are kept systematically and create a convenient system in the cloud. Path over Onedrive would be: Files -> Odoo -> App name -> Object's name -> Document. For example, "Files/Odoo/Sales Order/SO0001 /orders.xlsx".
    * Availability: This feature is available for Sales Orders and Purchase Order of Odoo.
    * Scheduled Actions: User can define the time interval for this scheduler to run to sync the data between the Onedrive and Odoo.
    * Delete Action: If user removes the attachment from Odoo, it will automatically delete the same attachment from Onedrive.
    * Update Attachment: If user updates attachment in OneDrive, the same attachment will be automatically updated in Odoo.
    * Store Attachments: User can select where to store attachments, either in OneDrive or both Odoo and OneDrive. Storing attachments in OneDrive will be a better practice as it will make Odoo faster because Odoo database storage will be not be used for storing attachments.

<keywords>
odoo onedrive
onedrive app
odoo onedrive integration
odoo onedrive connector
odoo onedrive app
    """,
    'depends': ['base', 'sale', 'product', 'sale_management', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/ir_attachment_view.xml',
        'views/res_config_settings_views.xml',
        'data/onedrive_cron.xml',
    ],
    'images': ['images/Animated-onedrive-integration.gif'],
    'live_test_url': 'http://www.pragtech.co.in/company/proposal-form.html?id=103&name=odoo-onedrive-integration',
    'license': 'OPL-1',
    'price': 49,
    'currency': 'EUR',
    'active': False,
    'installable': True,
}
