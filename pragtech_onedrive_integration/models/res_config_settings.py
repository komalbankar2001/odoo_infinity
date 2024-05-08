# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from odoo import _, api, fields, models
import requests
import os

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.model
    def default_get(self, fields_list):
        defaults = super(ResConfigSettings, self).default_get(fields_list)
        defaults['onedrive_api_url'] = 'https://graph.microsoft.com/v1.0'
        defaults['onedrive_auth_base_url'] = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        defaults['onedrive_auth_token_url'] = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
        return defaults

    state_onedrive = fields.Selection([('draft', 'Draft'),
                                       ('confirmed', 'Confirmed')], "OneDrive Config State", default='draft')

    onedrive_client_id = fields.Char(help="The client ID you obtain from the developer dashboard.",
                                     string="App Client ID")
    onedrive_client_secret = fields.Char(help="The client secret you obtain from the developer dashboard.",
                                         string="App Client Secret")

    onedrive_api_url = fields.Char("OneDrive URL", default="https://graph.microsoft.com/v1.0")

    onedrive_auth_base_url = fields.Char('Authorization URL',
                                         default="https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
                                         help="User Authenticate URI")

    onedrive_auth_token_url = fields.Char('Authorization Token URL',
                                          default="https://login.microsoftonline.com/common/oauth2/v2.0/token",
                                          help="User Authenticate URI")

    onedrive_redirect_url = fields.Char('Redirect URL',
                                        help="One of the redirect URIs listed for this project in the developer dashboard.")

    store_attachment_at = fields.Selection([('onedrive', 'OneDrive'), ('odoo_onedrive', 'Both (Odoo and OneDrive)')],
                                           string="Store Attachment At",
                                           default='onedrive', help="Please select where to store attachments?")

    # Used for API calling, generated during authorization process.
    onedrive_auth_code = fields.Char('Authorization Code')
    onedrive_access_token = fields.Char('Access Token', help="The token that must be used to access the OneDrive API.")
    onedrive_refresh_token = fields.Char('Refresh Token')

    # OneDrive Login and Confirm Button
    def login_onedeive(self):
        # Get Values From Setting
        onedrive_client_id = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_id')
        onedrive_client_secret = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_secret')
        onedrive_redirect_url = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_redirect_url')
        onedrive_auth_base_url = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_auth_base_url')
        # Validations
        if not onedrive_client_id:
            warning = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'type': 'warning',
                    'message': 'Please Enter App Client ID',
                    'sticky': True,
                }
            }
            return warning
        elif not onedrive_client_secret:
            warning = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'type': 'warning',
                    'message': 'Please Enter App Client Secret',
                    'sticky': True,
                }
            }
            return warning
        elif not onedrive_redirect_url:
            warning = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Warning'),
                    'type': 'warning',
                    'message': 'Please Enter Redirect URL',
                    'sticky': True,
                }
            }
            return warning
        else :
            # API Call For Authentication
            url = onedrive_auth_base_url + '?client_id=' + onedrive_client_id + \
                  '&redirect_uri=' + onedrive_redirect_url + \
                  '&response_type=code&scope=files.readwrite offline_access'
            return {
                "type": "ir.actions.act_url",
                "url": url,
                "target": "new"
            }

    # OneDrive Refresh Token Button
    def onedrive_refresh_token_meth(self):
        """
            This method is used to refresh OneDrive Token
        """
        headers = {}
        headers['accept'] = 'application/json'
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        onedrive_redirect_url = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_redirect_url')
        onedrive_client_id = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_id')
        onedrive_client_secret = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_secret')
        onedrive_refresh_token = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_refresh_token')
        onedrive_auth_token_url = self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_auth_token_url')

        payload = {'redirect_uri': onedrive_redirect_url, 'client_id': onedrive_client_id, 'client_secret': onedrive_client_secret,
                   'grant_type': 'refresh_token', 'refresh_token': onedrive_refresh_token}
        refresh_token = requests.request("POST", onedrive_auth_token_url, data=payload, headers=headers)
        if refresh_token:
            parsed_token_response = json.loads(refresh_token.text)
            if parsed_token_response:
                param = self.env['ir.config_parameter'].sudo()
                param.set_param('onedrive.onedrive_access_token', parsed_token_response.get('access_token'))
                param.set_param('onedrive.onedrive_refresh_token', parsed_token_response.get('refresh_token'))

    # Upload To Onedrive Button
    def upload_to_onedrive(self):
        """
            This method is used to upload Attachments To OneDrive.
            @params: self
            @return: NA
        """
        # Get Company ID
        user_ids = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
        company_id = user_ids.company_id
        onedrive_api_url, headers = company_id.get_onedrive_info_headers()
        # Creating Parent Folder i.e Odoo in OneDrive
        data = {
            "name": "Odoo",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "replace",
        }
        # print('data0--------upload---------------',data)
        url = onedrive_api_url + "/me/drive/root/children"
        request_url = requests.post(url=url, headers=headers, json=data)
        # print('request_url upload to onedrive----------------------------',request_url)
        if request_url.status_code == 201 or request_url.status_code == 200:
            parsed_data = json.loads(str(request_url.text))
            print('parsed_data-------------------------------', parsed_data)
            if parsed_data:
                onedrive_dict = {}
                existing_onedrive_id = self.env['onedrive.onedrive'].search(
                    [('onedrive_id', '=', parsed_data.get('id')), ('onedrive_name', '=', parsed_data.get('name'))])
                # Prepare onedrive_dict
                if parsed_data.get('id'):
                    onedrive_dict.update({'onedrive_id': parsed_data.get('id')})
                    odoo_folder_id = parsed_data.get('id')
                if parsed_data.get('name'):
                    onedrive_dict.update({'onedrive_name': parsed_data.get('name')})
                # Create Record in Odoo OneDrive Folder Master
                if not existing_onedrive_id and onedrive_dict:
                    onedrive_id = self.env['onedrive.onedrive'].create(onedrive_dict)

                # Getting Only Sale Order and Purchase Order Attachments where OneDrive is is not present
                attachment_ids = self.env['ir.attachment'].search(
                    [('onedrive_id', '=', False or None),
                     ('res_model', '!=', False),('res_model', '!=', 'payment.method'),
                     ('res_field', '=', False),('mimetype','not in',['text/scss','text/css','application/javascript','application/octet-stream']) ])
                # Iterating through attachments
                for attachment_id in attachment_ids:
                    if odoo_folder_id and attachment_id.res_model and attachment_id.res_name:
                        # Create Model Name Folder in OneDrive
                        onedrive_model_folder_id = company_id.create_model_folder_in_onedrive(odoo_folder_id,
                                                                                              attachment_id.res_model)
                        if onedrive_model_folder_id:
                            # Create Record Name Folder in OneDrive
                            onedrive_record_folder_id = company_id.create_record_folder_in_onedrive(
                                onedrive_model_folder_id, attachment_id.res_name)

                            if not onedrive_record_folder_id:
                                onedrive_model_folder_id = company_id.create_model_folder_in_onedrive(odoo_folder_id,
                                                                                                      attachment_id.res_model,
                                                                                                      force_create=True)
                                onedrive_record_folder_id = company_id.create_record_folder_in_onedrive(
                                    onedrive_model_folder_id, attachment_id.res_name)

                            if onedrive_record_folder_id:
                                file_name = attachment_id.name
                                content = attachment_id.datas
                                # Create Attachment in OneDrive
                                onedrive_id, download_url = company_id.create_attachment_in_onedrive(
                                    onedrive_record_folder_id, file_name, content)

                                if not onedrive_id:
                                    onedrive_record_folder_id = company_id.create_record_folder_in_onedrive(
                                        onedrive_model_folder_id, attachment_id.res_model, force_create=True)
                                    onedrive_id, download_url = company_id.create_attachment_in_onedrive(
                                        onedrive_record_folder_id, file_name, content)

                                store_attachment_at = self.env['ir.config_parameter'].sudo().get_param(
                                    'onedrive.store_attachment_at')
                                # Update OneDrive ID & Download URL in IR Attachment
                                if store_attachment_at == 'onedrive':
                                    # Delete Attachment From File Store
                                    if not isinstance(attachment_id.raw, bool) and not isinstance(
                                            attachment_id.checksum, bool):
                                        fname, full_path = attachment_id._get_path(attachment_id.raw,
                                                                                   attachment_id.checksum)
                                        if full_path and os.path.exists(full_path):
                                            os.remove(full_path)
                                    attachment_id.write({
                                        'type': 'url',
                                        'url': download_url,
                                        'datas': False,
                                        'onedrive_id': onedrive_id,
                                        'onedrive_download_url': download_url,
                                        'store_fname': False
                                    })
                                    self._cr.commit()
                                elif store_attachment_at == 'odoo_onedrive':
                                    attachment_id.write({
                                        'onedrive_id': onedrive_id,
                                        'onedrive_download_url': download_url,
                                    })
    # Download From OneDrive Button
    def download_from_onedrive(self):
        """
            This method is used to download Attachments from OneDrive
        """
        # Get API URL and Headers
        user_ids = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
        company_id = user_ids.company_id
        onedrive_api_url, headers = company_id.get_onedrive_info_headers()
        # GET Request to OneDrive
        url = onedrive_api_url + "/me/drive/root:/Odoo:/children?select=*"
        request_url = requests.request('GET', url, headers=headers)
        if request_url.status_code == 200:
            parsed_data = json.loads(str(request_url.text))
            if parsed_data:
                for val in parsed_data.get('value'):
                    if val.get('name'):
                        model_folder_name = val.get('name')
                        res_model = self.env['ir.model'].with_context(lang=self.env.user.lang).search([('name', '=', val.get('name'))]).model
                        if res_model:
                            # Get Model's Child Folders
                            company_id.get_model_folders(model_folder_name)

    # Get Values From Config Params
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
            state_onedrive=self.env['ir.config_parameter'].sudo().get_param('onedrive.state_onedrive') or 'draft',
            store_attachment_at=self.env['ir.config_parameter'].sudo().get_param('onedrive.store_attachment_at') or 'onedrive',
            onedrive_api_url=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_api_url') or 'https://graph.microsoft.com/v1.0',
            onedrive_client_id=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_id') or False,
            onedrive_client_secret=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_secret') or False,
            onedrive_redirect_url=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_redirect_url') or False,
            onedrive_auth_code=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_auth_code') or False,
            onedrive_access_token=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_access_token') or False,
            onedrive_refresh_token=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_refresh_token') or False,
            onedrive_auth_base_url=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_auth_base_url') or 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize',
            onedrive_auth_token_url=self.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_auth_token_url') or 'https://login.microsoftonline.com/common/oauth2/v2.0/token',
        )
        return res

    # Set Values From Config Params
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        param = self.env['ir.config_parameter'].sudo()

        state_onedrive = self.state_onedrive or 'draft'
        store_attachment_at = self.store_attachment_at or 'onedrive'
        onedrive_api_url = self.onedrive_api_url or 'https://graph.microsoft.com/v1.0'
        onedrive_client_id = self.onedrive_client_id or False
        onedrive_client_secret = self.onedrive_client_secret or False
        onedrive_redirect_url = self.onedrive_redirect_url or False
        onedrive_auth_code = self.onedrive_auth_code or False
        onedrive_access_token = self.onedrive_access_token or False
        onedrive_refresh_token = self.onedrive_refresh_token or False
        onedrive_auth_base_url = self.onedrive_auth_base_url or 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
        onedrive_auth_token_url = self.onedrive_auth_token_url or 'https://login.microsoftonline.com/common/oauth2/v2.0/token'

        param.set_param('onedrive.state_onedrive', state_onedrive)
        param.set_param('onedrive.onedrive_api_url', onedrive_api_url)
        param.set_param('onedrive.onedrive_client_id', onedrive_client_id)
        param.set_param('onedrive.onedrive_auth_base_url', onedrive_auth_base_url)
        param.set_param('onedrive.onedrive_auth_token_url', onedrive_auth_token_url)
        param.set_param('onedrive.onedrive_client_secret', onedrive_client_secret)
        param.set_param('onedrive.onedrive_redirect_url', onedrive_redirect_url)
        param.set_param('onedrive.onedrive_auth_code', onedrive_auth_code)
        param.set_param('onedrive.onedrive_access_token', onedrive_access_token)
        param.set_param('onedrive.onedrive_refresh_token', onedrive_refresh_token)
        param.set_param('onedrive.store_attachment_at', store_attachment_at)