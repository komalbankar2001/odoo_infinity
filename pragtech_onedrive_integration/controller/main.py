# -*- coding: utf-8 -*-
import json
import logging

import requests
from odoo import http, _
from odoo.http import Controller, route, request, Response

_logger = logging.getLogger(__name__)


class oneDriveController(http.Controller):

    @http.route('/get_onedrive_token', type="http", auth="public", website=True)
    def get_onedrive_token(self, **kwargs):
        if kwargs.get('code'):
            """
                Get Access Token and store in object
            """
            param = request.env['ir.config_parameter'].sudo()
            param.set_param('onedrive.onedrive_auth_code', kwargs.get('code'))
            client_id = request.env['ir.config_parameter'].sudo().get_param('onedrive.onedrive_client_id')
            client_secret = request.env['ir.config_parameter'].sudo().get_param(
                'onedrive.onedrive_client_secret')
            redirect_uri = request.env['ir.config_parameter'].sudo().get_param(
                'onedrive.onedrive_redirect_url')
            onedrive_auth_token_url = request.env['ir.config_parameter'].sudo().get_param(
                'onedrive.onedrive_auth_token_url')

            headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            data_token = {
                'client_id': client_id,
                'client_secret': client_secret,
                'code': kwargs.get('code'),
                'redirect_uri': redirect_uri,
                'grant_type': 'authorization_code'
            }
            access_token = requests.post(onedrive_auth_token_url, data=data_token, headers=headers)
            _logger.info("authorization_response %s " % access_token.text)

            if access_token:
                parsed_token_response = json.loads(access_token.text)
                _logger.info("nparsed_token_response %s" % parsed_token_response)
                if parsed_token_response:
                    param.set_param('onedrive.onedrive_access_token', parsed_token_response.get('access_token'))
                    param.set_param('onedrive.onedrive_refresh_token', parsed_token_response.get('refresh_token'))
                    param.set_param('onedrive.state_onedrive', 'confirmed')
                    _logger.info(_("Authorization successfully!"))

        return "Authenticated Successfully..!! \n You can close this window now"
