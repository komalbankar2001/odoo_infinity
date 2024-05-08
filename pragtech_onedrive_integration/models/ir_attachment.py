# -*- coding: utf-8 -*-
import logging
import base64
import requests
from odoo import api, models, fields
import os

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'
    _description = "OneDrive Customization"

    onedrive_id = fields.Char("OneDrive ID")
    onedrive_download_url = fields.Char("OneDrive Download URL")

    @api.model
    def _file_write(self, bin_value, checksum,  mimetype=False):
        print('-----------------_file_write-------------------------------')
        skip_upload = self._context.get('skip_upload')
        print('skip_upload---------------------------------------',skip_upload)
        # Check Store Attachment
        store_attachment_at = self.env['ir.config_parameter'].sudo().get_param(
            'onedrive.store_attachment_at')
        print('store_attachment_at--------------------------------------',store_attachment_at)
        if store_attachment_at == 'onedrive' and mimetype and mimetype not in ['text/scss','text/css','application/javascript','application/octet-stream'] and not skip_upload:
            return None
        else:
            fname, full_path = self._get_path(bin_value, checksum)
            print('fname--------------------------------',fname, full_path)
            if not os.path.exists(full_path):
                print('os.path.exists-------------------------------------')
                try:
                    with open(full_path, 'wb') as fp:
                        fp.write(bin_value)
                    # add fname to checklist, in case the transaction aborts
                    self._mark_for_gc(fname)
                except IOError:
                    _logger.info("_file_write writing %s", full_path, exc_info=True)
            return fname

    @api.depends('store_fname', 'db_datas')
    def _compute_raw(self):
        print('-----------------_compute_raw-----------------------')
        # If onedrive_id is set then fetch file from OneDrive
        store_attachment_at = self.env['ir.config_parameter'].sudo().get_param(
            'onedrive.store_attachment_at')
        print('store_attachment_at----------------------111----------------',store_attachment_at)
        for attach in self:
            if attach.onedrive_id and store_attachment_at == 'onedrive' and attach.mimetype not in ['text/scss','text/css','application/javascript','application/octet-stream'] and attach.res_model != 'payment.method':
                content = attach.company_id.fetch_file_from_onedrive(attach.onedrive_id)
                if content:
                    attach.raw = content
            elif attach.store_fname:
                attach.raw = attach._file_read(attach.store_fname)
            else:
                attach.raw = attach.db_datas

    @api.model
    def create(self, values):
        print('-----------------create-----------------------')
        # First Execute super then upload attachment to OneDrive and update OneDrive ID (file will not store in FileStore
        if values.get('res_model') in ['payment.method']:
            self = self.with_context(skip_upload=True)
            print('self-------------------------',self)
            res = super(IrAttachment, self).create(values)
            print('res-------if--------------------',res)
        else:
            res = super(IrAttachment, self).create(values)
            print('res--------else--------------------',res)

        record_name = ''
        file_name = values.get('name')
        print('file_name---------------------------',file_name)
        res_id = values.get('res_id')
        print('res_id---------------------------',res_id)
        res_model = values.get('res_model')
        print('res_model--------------------------',res_model)
        if res_model and res_id:
            record = self.env[res_model].sudo().browse(res_id)
            print('record-----------------------',record)
            record_name = record.name
            print('record_name----------------------',record_name)

        if not values.get('res_field'):
            # Creating Attachment at OneDrive based on User's Company- OneDrive Configuration
            user_ids = self.env['res.users'].search([('id', '=', self._context.get('uid'))])
            print('user_ids----------------------',user_ids)
            company_id = user_ids.company_id
            odoo_folder_id = company_id._get_create_root_directory()
            print('odoo_folder_id--------------------',odoo_folder_id)
            if res_model and record_name:
                print('---------record_name------res_model------------')
                # Create Model Name Folder in OneDrive
                model_folder_id = company_id.create_model_folder_in_onedrive(odoo_folder_id, res_model)
                print('model_folder_id--------------------',model_folder_id)
                if model_folder_id:
                    # Create Record Name Folder in OneDrive
                    record_folder_id = company_id.create_record_folder_in_onedrive(model_folder_id, record_name)
                    print('record_folder_id--------------------',record_folder_id)
                    if record_folder_id:
                        content = base64.b64encode(values.get('raw', None) or b'')
                        # Create Attachment in OneDrive
                        onedrive_id, download_url = company_id.create_attachment_in_onedrive(record_folder_id, file_name, content)
                        print('onedrive_id--------------------',onedrive_id)
                        if not onedrive_id:
                            # Possibility of record_folder_id(record Directry deleted from One drive) is not available so will recreate by Force=True
                            record_folder_id = company_id.create_record_folder_in_onedrive(model_folder_id, res_model, force_create=True)
                            onedrive_id, download_url = company_id.create_attachment_in_onedrive(record_folder_id, file_name[0], content)

                        res.write({'onedrive_id': onedrive_id, 'onedrive_download_url': download_url})
        return res

    def unlink(self):
        # Deleting Attachment From
        print('-----------------unlink-----------------------')
        company_id = self.env.company
        onedrive_api_url, headers = company_id.get_onedrive_info_headers()
        print('onedrive_api_url--------------------',onedrive_api_url)
        for attachment_id in self.filtered(lambda a: a.onedrive_id):
            url = onedrive_api_url + "/me/drive/items/" + attachment_id.onedrive_id
            print('url-----------------------',url)
            request_url = requests.request('DELETE', url=url, headers=headers)
            print('request_url--------------------',request_url)
            if request_url.status_code == 204:
                _logger.info('Attachment Successfully Deleted from OneDrive')
        return super(IrAttachment, self).unlink()

    def _get_datas_related_values(self, data, mimetype):
        checksum = self._compute_checksum(data)
        print('checksum---------------------',checksum)
        try:
            index_content = self._index(data, mimetype, checksum=checksum)
            print('index_content------try-------------',index_content)
        except TypeError:
            index_content = self._index(data, mimetype)
            print('index_content------------except-------------',index_content)
        values = {
            'file_size': len(data),
            'checksum': checksum,
            'index_content': index_content,
            'store_fname': False,
            'db_datas': data,
        }
        print('values---------------------------------------',values)
        if data and self._storage() != 'db':
            values['store_fname'] = self._file_write(data, values['checksum'],mimetype)
            values['db_datas'] = False
        return values
