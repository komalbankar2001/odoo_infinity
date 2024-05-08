# -*- coding: utf-8 -*-
from odoo import fields, models


class OneDrive(models.Model):
    _name = "onedrive.onedrive"
    _description = "OneDrive Folder Details Master"

    onedrive_name = fields.Char("OneDrive Folder Name")
    onedrive_id = fields.Char("OneDrive ID")
