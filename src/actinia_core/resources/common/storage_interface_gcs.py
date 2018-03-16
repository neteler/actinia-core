# -*- coding: utf-8 -*-
"""
Storage base class
"""
import os
import datetime
from google.cloud import storage
from google.cloud import bigquery
from actinia_core.resources.common.storage_interface_base import ResourceStorageBase

__license__ = "GPLv3"
__author__     = "Sören Gebbert"
__copyright__  = "Copyright 2016, Sören Gebbert"
__maintainer__ = "Sören Gebbert"
__email__      = "soerengebbert@googlemail.com"

SCENE_SUFFIXES={
"LT04":["_B1.TIF", "_B2.TIF", "_B3.TIF", "_B4.TIF", "_B5.TIF", "_B6.TIF", "_B7.TIF","_MTL.txt"],
"LT05":["_B1.TIF", "_B2.TIF", "_B3.TIF", "_B4.TIF", "_B5.TIF", "_B6.TIF", "_B7.TIF","_MTL.txt"],
"LE07":["_B1.TIF", "_B2.TIF", "_B3.TIF", "_B4.TIF", "_B5.TIF", "_B6_VCID_2.TIF", "_B6_VCID_1.TIF",
        "_B7.TIF", "_B8.TIF","_MTL.txt"],
"LC08":["_B1.TIF", "_B2.TIF", "_B3.TIF", "_B4.TIF", "_B5.TIF", "_B6.TIF", "_B7.TIF",
        "_B8.TIF", "_B9.TIF", "_B10.TIF", "_B11.TIF","_MTL.txt"]}

RASTER_SUFFIXES={
"LT04":[".1", ".2", ".3", ".4", ".5", ".6", ".7"],
"LT05":[".1", ".2", ".3", ".4", ".5", ".6", ".7"],
"LE07":[".1", ".2", ".3", ".4", ".5", ".61", ".62", ".7", ".8"],
"LC08":[".1", ".2", ".3", ".4", ".5", ".6", ".7", ".8", ".9", ".10", ".11"]}


class ResourceStorageGCS(ResourceStorageBase):
    """Storage class of generated resources to be put in a Google Cloud Storage bucket
    """

    def __init__(self, user_id, resource_id, config):
        """Storage class of generated resources to be put in a Google Cloud Storage bucket

        Args:
            user_id: The user id
            resource_id: The resource id
            config: The configuration of Actinia Core
        """
        ResourceStorageBase.__init__(self, user_id, resource_id, config)

        self.storage_client = None
        self.bucket_name = self.config.GCS_RESOURCE_BUCKET

    def setup(self):
        """Setup the Google Cloud Storage (GCS) client and the GCS credentials
        """
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config.GOOGLE_APPLICATION_CREDENTIALS
        self.storage_client = storage.Client()

    def get_resource_urls(self):
        """Return all resource urls that were generated

        Returns:
            (list): A list of urls

        """
        return self.resource_url_list

    def store_resource(self, file_path):
        """Store a resource (file) at the user resource storage and return an URL to the resource accessible via HTTP(S)

        Args:
            file_path:

        Returns:
            (str): the resource url that points to the stored resource
        """

        file_name = os.path.basename(file_path)
        object_path = os.path.join(self.user_id, self.resource_id, file_name)

        bucket = self.storage_client.get_bucket(self.bucket_name)
        blob = bucket.blob(object_path)
        blob.upload_from_filename(file_path)

        # Generate a persistent URL from the Bucket
        url = blob.generate_signed_url(
            # This URL is valid for 10 days
            expiration=datetime.timedelta(days=10),
            # Allow GET requests using this URL.
            method='GET')

        self.resource_file_list.append(object_path)
        self.resource_url_list.append(url)
        return url

    def remove_resources(self):
        """Remove the resource export path and everything inside
        """
        for blob_name in self.resource_file_list:
            bucket = self.storage_client.get_bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()