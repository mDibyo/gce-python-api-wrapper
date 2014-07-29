#!/usr/bin/env python

from apiclient.discovery import build
import httplib2
import logging
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow
import argparse
from oauth2client import tools


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

        parser = argparse.ArgumentParser(description=__doc__,
                                         formatter_class=argparse.RawDescriptionHelpFormatter,
                                         parents=[tools.argparser])
        flags = parser.parse_args([])

        flow = flow_from_clientsecrets(CLIENT_SECRETS, scope=GCE_SCOPE)
        storage = Storage(OAUTH2_STORAGE)
        credentials = storage.get()
        
        if credentials is None or credentials.invalid:
            credentials = run_flow(flow, storage, flags)
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

    # Instances
    def add_instance(self, instance_name, machine_type=DEFAULT_MACHINE_TYPE):
        """
        Add an instance to the project
        """
        machine_type_url = '%s/zones/%s/machineTypes/%s' % (
                self.project_url, DEFAULT_ZONE, machine_type)
        instance = {
            'kind': 'compute#instance',
            'name': instance_name,
            'machineType': machine_type_url,
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
        response = _blocking_call(self.gce_service, self.project_id, self.auth_http, response)


    # Firewalls
    def add_firewall(self, firewall_name, allowed):
        """
        Add a new firewall to the project
        """
        firewall = {
            'kind': 'compute#firewall',
            'name': firewall_name,
            'sourceRanges': ['0.0.0.0/0'],
            'allowed': [{
                'IPProtocol': allowed
            }],
            'network': self.network_url
        }
        request = self.gce_service.firewalls().insert(project=self.project_id,
                                                      body=firewall)
        response = request.execute(http=self.auth_http)
        print response

    def list_firewalls(self):
        """
        List all firewalls applied to project'
        """
        request = self.gce_service.firewalls().list(project=self.project_id,
                                                    filter=None)
        response = request.execute(http=self.auth_http)
        if response and 'items' in response:
            for firewall in response['items']:
                print firewall['name']
        else:
            print 'No firewalls in list. '

    def delete_firewall(self, firewall_name):
        """
        Delete a firewall with a given name from the project
        """
        request = self.gce_service.firewalls().delete(project=self.project_id,
                                                      firewall=firewall_name)
        response = request.execute(http=self.auth_http)

    
    # Disks
    def add_snapshot(self, snapshot_name, disk_name):
        """
        Create a snapshot from an existing persistent disk resource in the project.
        """
        snapshot = {
            'kind': 'compute#snapshot',
            'name': snapshot_name
        }
        request = self.gce_service.disks().createSnapshot(project=self.project_id,
                                                          body=snapshot,
                                                          zone=DEFAULT_ZONE,
                                                          disk=disk_name)
        response = request.execute(http=self.auth_http)
        response = _blocking_call(self.gce_service, self.project_id, self.auth_http, response)
    
    def list_snapshots(self):
        """
        List all snapshots associated with the project
        """
        request = self.gce_service.snapshots().list(project=self.project_id,
                                                    filter=None)
        response = request.execute(http=self.auth_http)
        if response and 'items' in response:
            for snapshot in response['items']:
                print snapshot['name']
        else:
            print 'No snapshots to list. '
    
    def delete_snapshot(self, snapshot_name):
        """
        Delete a snapshot resource from the project.
        """
        request = self.gce_service.snapshots().delete(project=self.project_id,
                                                      snapshot=snapshot_name)
        response = request.execute(http=self.auth_http)
    
    def add_disk(self, disk_name, disk_type='pd-standard', source_image=None, source_snapshot=None, size_gb=None):
        """
        Create a persistent disk from a given snapshot or image in the project
        """
        if source_image or source_snapshot or size_gb:
            disk_type_url = '%s/zones/%s/diskTypes/%s' % (
                    self.project_url, DEFAULT_ZONE, disk_type)
            disk = {
                'kind': 'compute#disks',
                'name': disk_name,
                'type': disk_type_url,
                'sizeGb': size_gb,        
            }
            if source_snapshot:
                snapshot_url = '%s/global/snapshots/%s' % (
                        self.project_url, source_snapshot)
                disk['sourceSnapshot'] = snapshot_url
            elif source_image:
                image_url = '%s/zone/%s/disks/%s' % (
                        self.project_url, DEFAULT_ZONE, source_image)
                disk['sourceImage'] = image_url 
            request = self.gce_service.disks().insert(project=self.project_id,
                                                      body=disk,
                                                      zone=DEFAULT_ZONE)
            response = request.execute(http=self.auth_http)
            response = _blocking_call(self.gce_service, self.project_id, self.auth_http, response)
        else:
            print 'At least one of source_image, source_snapshot and size_gb must be specified'
    
    def list_disks(self):
        """
        List all persistent disks in the project.
        """
        request = self.gce_service.disks().list(project=self.project_id,
                                                filter=None,
                                                zone=DEFAULT_ZONE)
        response = request.execute(http=self.auth_http)
        if response and 'items' in response:
            for disk in response['items']:
                print disk['name']
        else:
            print 'No disks to list. '


    # Images
    def add_image(self, image_name, gce_bucket, source_name):
        """
        Add an image to the project
        """
        raw_disk_url = 'http://storage.googleapis.com/%s/%s' % (
                gce_bucket, source_name)
        image = {
            'kind': 'compute#image',
            'name': image_name,
            'rawDisk': {
                'containerType': 'TAR',
                'source': raw_disk_url
            },
            'sourceType': 'RAW',
        }
        request = self.gce_service.images().insert(project=self.project_id,
                                                   body=image)
        response = request.execute(http=self.auth_http)

    def list_images(self):
        """
        List all images in project
        """
        request = self.gce_service.images().list(project=self.project_id,
                                                 filter=None)
        response = request.execute(http=self.auth_http)
        if response and 'items' in response:
            for firewall in response['items']:
                print firewall['name']
        else:
            print 'No images in list. '

    def delete_image(self, image_name):
        """
        Delete an image resource from the project
        """
        request = self.gce_service.images().delete(project=self.project_id,
                                                   image=image_name)
        response = request.execute(http=self.auth_http)


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
                    project=project_id, operation=operation_id, zone=zone_name)
        
        response = request.execute(http=auth_http)
        if response:
            status = response['status']
    return response


gce = GCE("nth-clone-620")

