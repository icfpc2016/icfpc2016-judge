# Copyright 2016 ICFP Programming Contest 2016 Organizers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import base64
import cStringIO
import gzip
import os
import urllib

import apiclient.discovery
import apiclient.errors
import apiclient.http
import oauth2client.client
import oauth2client.service_account
import httplib2shim

from hibiki import misc_util


_SIGNER_CREDENTIALS_PATH = os.path.join(
    os.path.dirname(__file__), 'hibiki-gcs-signer.json')
_signer_credentials = None
_service = None
_bucket_name = None


def connect(bucket_name):
    global _signer_credentials
    global _service
    global _bucket_name
    _signer_credentials = (
        oauth2client.service_account.ServiceAccountCredentials.from_json_keyfile_name(
            _SIGNER_CREDENTIALS_PATH))
    service_credentials = (
        oauth2client.client.GoogleCredentials.get_application_default())
    _service = apiclient.discovery.build(
        'storage', 'v1', credentials=service_credentials, http=httplib2shim.Http())
    _bucket_name = bucket_name


def save(name, binary, mimetype):
    try:
        request = _service.objects().get(bucket=_bucket_name, object=name)
        request.execute()
    except apiclient.errors.HttpError:
        pass
    else:
        # The blob already exists.
        return
    buf = cStringIO.StringIO()
    with gzip.GzipFile(fileobj=buf, mode='wb') as gzip_stream:
        gzip_stream.write(binary)
    buf.seek(0)
    request = _service.objects().insert(
        bucket=_bucket_name,
        name=name,
        media_body=apiclient.http.MediaIoBaseUpload(buf, mimetype=mimetype),
        contentEncoding='gzip')
    request.execute(num_retries=3)


def load(name):
    request = _service.objects().get_media(bucket=_bucket_name, object=name)
    buf = cStringIO.StringIO()
    download = apiclient.http.MediaIoBaseDownload(buf, request)
    while True:
        _, done = download.next_chunk(num_retries=3)
        if done:
            break
    return buf.getvalue()


def get_signed_url(name):
    expires = int(misc_util.time() + 300)
    request = 'GET\n\n\n%d\n/%s/%s' % (expires, _bucket_name, name)
    params = {
        'GoogleAccessId': _signer_credentials.service_account_email,
        'Expires': expires,
        'Signature': base64.b64encode(_signer_credentials.sign_blob(request)[1]),
    }
    return 'http://storage.googleapis.com/%s/%s?%s' % (
        _bucket_name, name, urllib.urlencode(params))
