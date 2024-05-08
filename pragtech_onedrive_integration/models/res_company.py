# -*- coding: utf-8 -*-
import base64
import json
import logging
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ResCompany(models.Model):
    _inherit = "res.company"
    _description = "Res Company OneDrive Configuration Customization"

    # Get Model Name
    def get_model_description(self, model_name):
        model = self.env['ir.model'].sudo().search([('model', '=', model_name)])
        print('model---------------------',model)
        return model.name or model.model

    # Refresh Token Method
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

    # Get OneDrive Creadentials
    def get_onedrive_info_headers(self):
        """
            This method will return OneDrive API URL & headers
            @params: self
            @return: onedrive_api_url, headers
        """
        onedrive_api_url = "https://graph.microsoft.com/v1.0"
        headers = {}
        onedrive_access_token = self.env['ir.config_parameter'].sudo().get_param(
            'onedrive.onedrive_access_token')
        if onedrive_access_token:
            headers['Authorization'] = 'bearer ' + str(onedrive_access_token)
            headers['Content-Type'] = 'application/json'
            headers['scope'] = 'Files.Read.All, Files.ReadWrite.All, Sites.Read.All, Sites.ReadWrite.All'
        return onedrive_api_url, headers

    # Fetch Data From OneDrive
    def fetch_file_from_onedrive(self, file_id):
        """
            This method will fetch file from OneDrive
            @params: self, file_id
            @return: file_content
        """
        onedrive_api_url, headers = self.get_onedrive_info_headers()
        url = onedrive_api_url + "/me/drive/items/" + file_id + "/content"
        file_content = requests.get(url=url, headers=headers)
        if file_content.status_code == 200:
            return file_content.content
        else:
            return False

    # Create Root Odoo Folder
    def _get_create_root_directory(self):
        # This method will create root directory in OneDrive With name "Odoo"
        existing_onedrive_id = self.env['onedrive.onedrive'].search([('onedrive_name', '=', 'Odoo')])
        if not existing_onedrive_id:
            return existing_onedrive_id.onedrive_id
        else:
            onedrive_api_url, headers = self.get_onedrive_info_headers()
            data = {"name": "Odoo", "folder": {}, "@microsoft.graph.conflictBehavior": "replace"}
            url = onedrive_api_url + "/me/drive/root/children"
            request_url = requests.post(url=url, headers=headers, json=data)
            if request_url.status_code == 201 or request_url.status_code == 200:
                parsed_data = json.loads(str(request_url.text))
                if parsed_data:
                    onedrive_id = self.env['onedrive.onedrive'].create({'onedrive_id': parsed_data.get('id'),
                                                                        'onedrive_name': parsed_data.get('name')})
                    return onedrive_id.onedrive_id
            else:
                raise UserError(_('Not Able to Create Root Directory(Odoo).'))

    # Create Folder in OneDrive
    def create_attachment_in_onedrive(self, onedrive_record_folder_id, file_name, content):
        """
            This method will upload attachments to OneDrive
            @params: onedrive_record_folder_id, file_name, content
            @return: onedrive_id, download_url
        """
        if onedrive_record_folder_id and file_name and content:
            # Decode Content
            content = base64.b64decode(content)
            # Get API URL and headers
            onedrive_api_url, headers = self.get_onedrive_info_headers()
            url = onedrive_api_url + "/me/drive/items/" + onedrive_record_folder_id + ":/" + file_name + ":/content"
            request_url = requests.put(url=url, headers=headers, data=content)
            if request_url.status_code == 201 or request_url.status_code == 200:
                parsed_data = json.loads(str(request_url.text))
                if parsed_data:
                    onedrive_id, download_url = '', ''
                    if parsed_data.get('id'):
                        onedrive_id = parsed_data.get('id')
                    _logger.info("Attachment Successfully Created in OneDrive!!!")
                    return onedrive_id, download_url
        return None, None

    def create_record_folder_in_onedrive(self, model_folder_id, folder_name, force_create=True):
        folder_name = folder_name.replace('/', '_')
        print('folder_name--------------------------,folder_name')
        # Used to create folder in onedrive for Record under model_folder_id
        existing_onedrive_id = self.env['onedrive.onedrive'].search([('onedrive_name', '=', folder_name)], limit=1)
        print('existing_onedrive_id--------------------------',existing_onedrive_id)
        if existing_onedrive_id:
            return existing_onedrive_id.onedrive_id
        else:
            onedrive_api_url, headers = self.get_onedrive_info_headers()
            # Create New Folder in OneDrive
            data = {"name": folder_name, "folder": {}, "@microsoft.graph.conflictBehavior": "replace"}
            print('data-------------folder-------------------',data)
            url = onedrive_api_url + "/me/drive/items/" + model_folder_id + "/children"
            request_url = requests.post(url=url, headers=headers, json=data)
            print('request_url------------------------folder---------',request_url)
            if request_url.status_code == 201 or request_url.status_code == 200:
                parsed_data = json.loads(request_url.text)
                if parsed_data:
                    self.env['onedrive.onedrive'].create(
                        {'onedrive_id': parsed_data.get('id'), 'onedrive_name': parsed_data.get('name')})
                    return parsed_data.get('id')
        return None

    def create_model_folder_in_onedrive(self, odoo_folder_id, model_name, force_create=False):
        print('self---------------------------------', self)
        print('odoo_folder_id-------------------------', odoo_folder_id)
        print('create_model_folder_in_onedrive---------------------------')
        model_desc = self.get_model_description(model_name)
        if '/' in model_desc:
            model_desc1 = model_desc.replace('/', '_')
            print('model_desc1--------------------------------', model_desc1)
        else:
            model_desc1 = model_desc
            print('model_desc1-------else-----------------------', model_desc1)

        print('model_desc--------------------------------', model_desc)
        existing_onedrive_id = self.env['onedrive.onedrive'].search([('onedrive_name', '=', model_desc)])
        # print('existing_onedrive_id---------------------------',existing_onedrive_id)
        if existing_onedrive_id:
            print('existing_onedrive_id-----if----------------------', existing_onedrive_id)
            return existing_onedrive_id.onedrive_id
        else:
            # Create New Folder in OneDrive
            user_ids = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
            company_id = user_ids.company_id
            onedrive_api_url, headers = company_id.get_onedrive_info_headers()

            # Specify the parent folder ID here
            parent_folder_id = odoo_folder_id

            data = {
                "name": model_desc1,
                "folder": {},
                "@microsoft.graph.conflictBehavior": "replace",
            }
            print('data0-----------------------', data)

            # URL for creating a folder inside another folder
            url = f"{onedrive_api_url}/me/drive/items/{parent_folder_id}/children"

            request_url = requests.post(url=url, headers=headers, json=data)
            # print('request_url-------------------------------', request_url)
            if request_url.status_code == 201 or request_url.status_code == 200:
                parsed_data = json.loads(str(request_url.text))
                if parsed_data:
                    self.env['onedrive.onedrive'].create(
                        {'onedrive_id': parsed_data.get('id'), 'onedrive_name': parsed_data.get('name')})
                    return parsed_data.get('id')
                else:
                    raise UserError(_('Not Able to Create Model Directory.(%s)' % model_desc))
    # Get Attachment Function
    @api.model
    def url_to_ir_attachment(self, download_url, onedrive_id, onedrive_ids, file_name, model_name, res_name):
        """
            This method is used to get download url and it's content
            @params : download_url, onedrive_id, file_name, model_name, res_name
            @returns : NA
        """
        encoded_response = ''
        # Search Model and Res ID
        if model_name == 'Sales Order':
            model_name = 'Sales Order'
        res_model = self.env['ir.model'].with_context(lang=self.env.user.lang).search([('name', '=', model_name)]).model
        res_id = None
        if self.env[res_model].search([('name', '=', res_name)]):
            res_id = self.env[res_model].search([('name', '=', res_name)])[0].id
        # Get Request to get content
        request_url = requests.get(download_url)
        if request_url.status_code == 200:
            # If response is 200(success) then save the contents of URL(base64) into ir.attachment
            encoded_response = base64.b64encode(request_url.content)
        #  If you deleted a files from OneDrive . Thus, Odoo would remove related attachments.
        if res_model and res_id:
            attachment_ids = self.env['ir.attachment'].search([('res_model', '=', res_model),('res_model', '!=', 'payment.method'),
                                                               ('res_id', '=', res_id), ('onedrive_id', '!=', False),('mimetype','not in',['text/scss','text/css','application/javascript','application/octet-stream'])])
            attachments_set = set(attachment_ids.mapped('onedrive_id'))
            to_delete = attachments_set - set(onedrive_ids)
            to_delete = attachment_ids.filtered(
                lambda a: a.onedrive_id in to_delete
            )
            _logger.debug(
                "Deleted: {}".format(', '.join(to_delete.mapped('name'))),
            )
            to_delete.unlink()

        if res_model and res_id and file_name and download_url:
            attachment_id = self.env['ir.attachment'].search([('res_model', '=', res_model),
                                                              ('res_id', '=', res_id), ('onedrive_id', '=', onedrive_id)])
            ir_attachment_dict = {}
            data_dict = {}
            store_attachment_at = self.env['ir.config_parameter'].sudo().get_param(
                'onedrive.store_attachment_at')
            # Preparing Attachment Dict
            if store_attachment_at == 'onedrive':
                ir_attachment_dict = {
                    'name': file_name,
                    'res_name': res_model,
                    'res_model': res_model,
                    'res_id': res_id,
                    'type': 'url',
                    'url': download_url,
                    'name': file_name,
                    'onedrive_id': onedrive_id,
                    'onedrive_download_url': download_url,
                }
                attachment_id.write({'name': file_name})
            elif store_attachment_at == 'odoo_onedrive':
                ir_attachment_dict = {
                    'name': file_name,
                    'res_name': res_model,
                    'res_model': res_model,
                    'res_id': res_id,
                    'type': 'binary',
                    'datas': encoded_response,
                    'name': file_name,
                    'onedrive_id': onedrive_id,
                    'onedrive_download_url': download_url,
                }
                data_dict = {'datas': encoded_response, }
            if not attachment_id and ir_attachment_dict:
                # Creating Attachment
                self.env['ir.attachment'].create(ir_attachment_dict)
                _logger.info("Attachment Successfully Created In Odoo!")
            elif attachment_id and data_dict:
                # Updating Attachment
                attachment_id.write(data_dict)
                _logger.info("Attachment Successfully Updated In Odoo!")

    # Get Folder Sub Function
    @api.model
    def get_object_attachments(self, model_folder_name, rec_folder_name):
        """
            This method is used to get attachments from model_name and rec_folder_name
            @params : model_folder_name, rec_folder_name
            @returns : NA
        """
        # Get API URL and Headers
        onedrive_api_url, headers = self.get_onedrive_info_headers()
        # GET Request to OneDrive
        url = onedrive_api_url + "/me/drive/root:/Odoo/" + model_folder_name + "/" + rec_folder_name + ":/children?select=*"
        request_url = requests.get(url, headers=headers)
        if request_url.status_code == 200:
            parsed_data = json.loads(str(request_url.text))
            onedrive_ids = []
            if parsed_data:
                for val in parsed_data.get('value'):
                    if val.get('id'):
                        onedrive_ids.append(val.get('id'))
            if parsed_data:
                for val in parsed_data.get('value'):
                    if val.get('name'):
                        file_name = val.get('name')
                    if val.get('@microsoft.graph.downloadUrl'):
                        download_url = val.get('@microsoft.graph.downloadUrl')
                    if val.get('id'):
                        onedrive_id = val.get('id')
                    # Call url_to_ir_attachment for creation of ir.attachment from URL
                    self.url_to_ir_attachment(download_url, onedrive_id, onedrive_ids, file_name, model_folder_name, rec_folder_name)

    # Download From OneDrive SubFunction
    @api.model
    def get_model_folders(self, model_folder_name):
        """
            This method is used to get child folders from Model Folder Name
            @params : model_folder_name
            @returns : NA
        """
        # Get API URL and Headers
        onedrive_api_url, headers = self.get_onedrive_info_headers()
        # GET Request to OneDrive
        url = onedrive_api_url + "/me/drive/root:/Odoo/" + model_folder_name + ":/children?select=*"
        request_url = requests.get(url, headers=headers)
        if request_url.status_code == 200:
            parsed_data = json.loads(str(request_url.text))
            if parsed_data:
                for val in parsed_data.get('value'):
                    if val.get('name'):
                        rec_folder_name = val.get('name')
                        # Get Attachments

                        self.get_object_attachments(model_folder_name, rec_folder_name)

    # Cron Sync Sub Function 1
    def upload_to_onedrive(self):
        """
            This method is used to upload Attachments To OneDrive.
            @params: self
            @return: NA
        """
        onedrive_api_url, headers = self.get_onedrive_info_headers()
        # Creating Parent Folder i.e Odoo in OneDrive
        data = {
            "name": "Odoo",
            "folder": {},
            "@microsoft.graph.conflictBehavior": "replace",
        }
        url = onedrive_api_url + "/me/drive/root/children"
        request_url = requests.post(url=url, headers=headers, json=data)
        if request_url.status_code == 201 or request_url.status_code == 200:
            parsed_data = json.loads(str(request_url.text))
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
                # attachment_ids = self.env['ir.attachment'].search(
                #     [('onedrive_id', '=', False or None), ('res_model', 'in', ['sale.order', 'purchase.order', 'hr.employee', 'res.partner']),
                #      ('res_field', '=', False)])
                attachment_ids = self.env['ir.attachment'].search(
                    [('onedrive_id', '=', False or None),
                     ('res_model', '!=', False),
                     ('res_field', '=', False)])
                # Iterating through attachments
                for attachment_id in attachment_ids:
                    if odoo_folder_id and attachment_id.res_model and attachment_id.res_name:
                        # Create Model Name Folder in OneDrive
                        onedrive_model_folder_id = self.create_model_folder_in_onedrive(odoo_folder_id, attachment_id.res_model)
                        if onedrive_model_folder_id:
                            # Create Record Name Folder in OneDrive
                            onedrive_record_folder_id = self.create_record_folder_in_onedrive(onedrive_model_folder_id, attachment_id.res_name)

                            if not onedrive_record_folder_id:
                                onedrive_model_folder_id = self.create_model_folder_in_onedrive(odoo_folder_id, attachment_id.res_model,
                                                                                                force_create=True)
                                onedrive_record_folder_id = self.create_record_folder_in_onedrive(onedrive_model_folder_id,
                                                                                                  attachment_id.res_name)

                            if onedrive_record_folder_id:
                                file_name = attachment_id.name,
                                content = attachment_id.datas
                                # Create Attachment in OneDrive
                                onedrive_id, download_url = self.create_attachment_in_onedrive(onedrive_record_folder_id, file_name[0], content)

                                if not onedrive_id:
                                    onedrive_record_folder_id = self.create_record_folder_in_onedrive(onedrive_model_folder_id,
                                                                                                      attachment_id.res_model,
                                                                                                      force_create=True)
                                    onedrive_id, download_url = self.create_attachment_in_onedrive(onedrive_record_folder_id,
                                                                                                   file_name[0], content)
                                # Update OneDrive ID & Download URL in IR Attachment
                                store_attachment_at = self.env['ir.config_parameter'].sudo().get_param(
                                    'onedrive.store_attachment_at')
                                if store_attachment_at == 'onedrive':
                                    attachment_id.write({
                                        'type': 'url',
                                        'url': download_url,
                                        'datas': False,
                                        'onedrive_id': onedrive_id,
                                        'onedrive_download_url': download_url,
                                    })
                                elif store_attachment_at == 'odoo_onedrive':
                                    attachment_id.write({
                                        'onedrive_id': onedrive_id,
                                        'onedrive_download_url': download_url,
                                    })

    # Cron Sync Sub Function 2
    def download_from_onedrive(self):
        """
            This method is used to download Attachments from OneDrive
        """
        # Get API URL and Headers
        onedrive_api_url, headers = self.get_onedrive_info_headers()
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
                            self.get_model_folders(model_folder_name)

    # Cron For Refresh OneDrive Token
    def refresh_onedrive_token(self):
        """
            Scheduler for Refreshing OneDrive Token
        """
        _logger.info("Scheduler Started For Refresh Token!!")
        company_id = self.env.company
        company_id.onedrive_refresh_token_meth()
        return True

    # Cron For Sync With OneDrive
    def sync_with_onedrive(self):
        """
            Scheduler for Upload to OneDrive and Download from OneDrive
        """
        _logger.info("Scheduler Started For Upload and Download!!")
        company_id = self.env.company
        company_id.upload_to_onedrive()
        company_id.download_from_onedrive()
        return True
