import urllib2
import urllib
from Crypto.Cipher import DES
import base64
import googleapiclient.discovery

METADATA_REQUEST_URL = 'http://metadata/computeMetadata/v1/instance/attributes/%s'

class MissingParameterException(Exception):
        pass

def get_metadata_param(param_key):
        '''
        Calls the metadata service to get the parameters passed to the current instance
        '''
        request_url = METADATA_REQUEST_URL % param_key
        request = urllib2.Request(request_url)
        request.add_header('X-Google-Metadata-Request', 'True')
        try: 
                response = urllib2.urlopen(request) 
                data = response.read()
                return data
        except urllib2.HTTPError as ex:
                raise MissingParameterException('The parameter %s was not found on the metadata server' % param_key)


def kill_instance(params):

    # get the instance name.  returns a name like 'test-upload-instance.c.cccb-data-delivery.internal'
    url = 'http://metadata/computeMetadata/v1/instance/hostname'
    request = urllib2.Request(url)
    request.add_header('X-Google-Metadata-Request', 'True')
    response = urllib2.urlopen(request)
    result = response.read()
    instance_name = result.split('.')[0]
    compute = googleapiclient.discovery.build('compute', 'v1')
    compute.instances().delete(project=params['google_project'], zone=params['google_zone'], instance=instance_name).execute()

def notify_master(params):
    d = {}
    token = params['token']
    obj=DES.new(params['enc_key'], DES.MODE_ECB)
    enc_token = obj.encrypt(token)
    b64_str = base64.encodestring(enc_token)
    d['token'] = b64_str
    d['projectPK'] = params['project_pk']
    base_url = params['callback_url']
    data = urllib.urlencode(d)
    request = urllib2.Request(base_url, {'Content-Type': 'application/json'})
    response = urllib2.urlopen(request, data=data)


if __name__ == '__main__':
    EXPECTED_PARAMS = ['token','enc_key','callback_url', 'google_project', 'google_zone', 'project_pk']
    params = dict(zip(EXPECTED_PARAMS, map(get_metadata_param, EXPECTED_PARAMS)))
    notify_master(params)
    kill_instance(params)
