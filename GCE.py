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
