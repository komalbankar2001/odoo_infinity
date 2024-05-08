from odoo.http import Stream, root

import base64
import cgi
import collections
import collections.abc
import contextlib
import functools
import glob
import hashlib
import hmac
import inspect
import json
import logging
import mimetypes
import os
import re
import threading
import time
import traceback
import warnings
import zlib
from abc import ABC, abstractmethod
from datetime import datetime
from io import BytesIO
from os.path import join as opj
from pathlib import Path
from urllib.parse import urlparse
from zlib import adler32

import babel.core
import psycopg2
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.security
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import URL, url_parse, url_encode, url_quote
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix

from odoo.tools import (config, consteq, date_utils, file_path, parse_version,
                    profiler, submap, unique, ustr,)
from odoo.http import request



_logger = logging.getLogger(__name__)

@classmethod
def from_attachment_custom(cls, attachment):
        """ Create a :class:`~Stream`: from an ir.attachment record. """
        attachment.ensure_one()

        self = cls(
            mimetype=attachment.mimetype,
            download_name=attachment.name,
            conditional=True,
            etag=attachment.checksum,
        )

        if attachment.store_fname:
            self.type = 'path'
            self.path = werkzeug.security.safe_join(
                os.path.abspath(config.filestore(request.db)),
                attachment.store_fname
            )
            stat = os.stat(self.path)
            self.last_modified = stat.st_mtime
            self.size = stat.st_size

        elif attachment.db_datas:
            self.type = 'data'
            self.data = attachment.raw
            self.last_modified = attachment['__last_update']
            self.size = len(self.data)

        elif attachment.raw:
            self.type = 'data'
            self.data = attachment.raw
            self.last_modified = attachment['__last_update']
            self.size = len(self.data)

        elif attachment.url:
            # When the URL targets a file located in an addon, assume it
            # is a path to the resource. It saves an indirection and
            # stream the file right away.
            static_path = root.get_static_file(
                attachment.url,
                host=request.httprequest.environ.get('HTTP_HOST', '')
            )
            if static_path:
                self = cls.from_path(static_path)
            else:
                self.type = 'url'
                self.url = attachment.url

        else:
            self.type = 'data'
            self.data = b''
            self.size = 0

        return self

Stream.from_attachment = from_attachment_custom
