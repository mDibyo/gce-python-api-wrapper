#!/usr/bin/env python

from apiclient.discovery import build
import httplib2
import logging
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow

# import argparse
# from oauth2client import tools
# import sys
DEFAULT_ZONE = 'us-central1-a'
API_VERSION = 'v1'
GCE_URL = 'https://www.googleapis.com/compute/%s/projects/' % (API_VERSION)
CLIENT_SECRETS = 'client_secrets.json'
OAUTH2_STORAGE = 'oauth2.dat'
GCE_SCOPE = 'https://www.googleapis.com/auth/compute'

DEFAULT_IMAGES = {
    'ubuntu': 'ubuntu14-server-raaas-docker',
    'debian': 'debian-7-wheezy-v20140718',
    'centos': 'centos-6-v20140718'
}
DEFAULT_MACHINE_TYPE = 'n1-standard-1'
DEFAULT_NETWORK = 'default'
DEFAULT_ROOT_PD_NAME = 'my-root-pd'
DEFAULT_SEVICE_EMAIL = 'default'
DEFAULT_SCOPES = ['https://www.googleapis.com/auth/devstorage.full_control',
                  'https://www.googleapis.com/auth/compute']

class GCE:
    
    def __init__(self, project_id):
        """
        Perform OAuth 2 authorization and build the service
        """
        logging.basicConfig(level=logging.INFO)
        
        flow = flow_from_clientsecrets(CLIENT_SECRETS, scope=GCE_SCOPE)
        storage = Storage(OAUTH2_STORAGE)
        credentials = storage.get()
        
        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage)
        self.auth_http = credentials.authorize(httplib2.Http())
        
        # Build the service
        self.gce_service = build('compute', API_VERSION)
        self.project_url = '%s%s' % (GCE_URL, project_id)
        self.image_url = '%s%s/global/images/%s' % (
            GCE_URL, 'debian-cloud', DEFAULT_IMAGES['debian'])
        self.machine_type_url = '%s/zones/%s/machineTypes/%s' % (self.project_url,
                                                                 DEFAULT_ZONE,
                                                                 DEFAULT_MACHINE_TYPE)
        self.network_url = '%s/global/networks/%s' % (self.project_url,
                                                      DEFAULT_NETWORK)
        self.project_id = project_id

    def add_instance(self, instance_name, machine_type=DEFAULT_MACHINE_TYPE):
        """
        Add an instance to the project
        """
        instance = {
            'kind': 'compute#instance',
            'name': instance_name,
            'machineType': machine_type,
            'disks': [{
                'autoDelete': 'true',
                'boot': 'true',
                'type': 'PERSISTANT',
                'initializeParams': {
                    'diskName': DEFAULT_ROOT_PD_NAME,
                    'sourceImage': self.image_url
                }
            }],
            'networkInterfaces': [{
                'accessConfigs': [{
                    'type': 'ONE_TO_ONE_NAT',
                    'name': 'External NAT'
                }],
                'network': self.network_url
            }],
            'serviceAccounts': [{
                'email': DEFAULT_SEVICE_EMAIL,
                'scopes': DEFAULT_SCOPES
            }],
            
        }
        # Create the instance
        request = self.gce_service.instances().insert(project=self.project_id,
                                                      body=instance,
                                                      zone=DEFAULT_ZONE)
        response = request.execute(http=self.auth_http)
        response = _blocking_call(self.gce_service, self.project_id, self.auth_http, response)
        print response

    def list_instances(self):
        """
        List all instances running in the project
        """
        request = self.gce_service.instances().list(project=self.project_id,
                                                    filter=None,
                                                    zone=DEFAULT_ZONE)
        response = request.execute(http=self.auth_http)
        if response and 'items' in response:
            instances = response['items']
            for instance in instances:
                print instance['name']
        else:
            print 'No instances to list. '

    def delete_instance(self, instance_name):
        """
        Delete an instance with a given name from the project
        """
        request = self.gce_service.instances().delete(project=self.project_id,
                                                      instance=instance_name,
                                                      zone=DEFAULT_ZONE)
        response = request.execute(http=self.auth_http)
        response = _blocking_call(self.gce_service, self.auth_http, response)

def _blocking_call(gce_service, project_id, auth_http, response):
    """Blocks until the operation status is done for the given operation."""

    status = response['status']
    while status != 'DONE' and response:
        operation_id = response['name']
    
        # Identify if this is a per-zone resource
        if 'zone' in response:
            zone_name = response['zone'].split('/')[-1]
            request = gce_service.zoneOperations().get(
                    project=project_id, operation=operation_id, zone=zone_name)
        else:
            request = gce_service.zoneOperations().get(
                    project=project_id, operation=operation_id)
        
        response = request.execute(http=auth_http)
        if response:
            status = response['status']
    return response
