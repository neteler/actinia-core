# -*- coding: utf-8 -*-
"""
Resource storage management

TODO: Tests required
"""

import os
from flask import jsonify, make_response

from flask_restful_swagger_2 import swagger

from actinia_core.resources.async_ephemeral_processing import AsyncEphemeralProcessing
from actinia_core.resources.async_persistent_processing import AsyncPersistentProcessing
from actinia_core.resources.async_resource_base import AsyncEphemeralResourceBase
from actinia_core.resources.common.redis_interface import enqueue_job
from actinia_core.resources.common.process_object import Process
from actinia_core.resources.common.exceptions import AsyncProcessError
from actinia_core.resources.common.response_models import StorageResponseModel, StorageModel, ProcessingResponseModel

from actinia_core.resources.common.app import auth
from actinia_core.resources.common.logging_interface import log_api_call
from actinia_core.resources.user_auth import very_admin_role
from actinia_core.resources.user_auth import check_user_permissions

__license__ = "GPLv3"
__author__     = "Sören Gebbert"
__copyright__  = "Copyright 2016, Sören Gebbert"
__maintainer__ = "Sören Gebbert"
__email__      = "soerengebbert@googlemail.com"


class SyncResourceStorageResource(AsyncEphemeralResourceBase):

    decorators = [log_api_call, check_user_permissions,
                  very_admin_role, auth.login_required]

    @swagger.doc({
        'tags': ['resource management'],
        'description': 'Returns the current size of the resource storage. Minimum required user role: admin.',
        'responses': {
            '200': {
                'description': 'The current state of the resource storage',
                'schema':StorageResponseModel
            },
            '400': {
                'description': 'The error message why resource storage information gathering did not succeeded',
                'schema':ProcessingResponseModel
            }
        }
     })
    def get(self):
        """Returns the current size of the resource storage"""
        rdc = self.preprocess(has_json=False, has_xml=False)

        enqueue_job(self.job_timeout, start_resource_storage_size, rdc)
        http_code, response_model = self.wait_until_finish()
        return make_response(jsonify(response_model), http_code)

    @swagger.doc({
        'tags': ['resource management'],
        'description': 'Clean the resource storage and remove all cached data. Minimum required user role: admin.',
        'responses': {
            '200': {
                'description': 'Processing status of resource storage deletion',
                'schema':ProcessingResponseModel
            },
            '400': {
                'description': 'The error message why resource storage cleaning did not succeeded',
                'schema':ProcessingResponseModel
            }
        }
     })
    def delete(self):
        """Clean the resource storage and remove all cached data"""
        rdc = self.preprocess(has_json=False, has_xml=False)

        enqueue_job(self.job_timeout, start_resource_storage_remove, rdc)
        http_code, response_model = self.wait_until_finish()
        return make_response(jsonify(response_model), http_code)


def start_resource_storage_size(*args):
    processing = ResourceStorageSize(*args)
    processing.run()


class ResourceStorageSize(AsyncEphemeralProcessing):
    """Compute the download cache size
    """

    def __init__(self, *args):
        AsyncEphemeralProcessing.__init__(self, *args)
        self.response_model_class = StorageResponseModel
        self.user_resource_storage_path = os.path.join(self.config.GRASS_RESOURCE_DIR, self.user_id)

    def _execute(self):

        self._setup()

        if os.path.exists(self.user_resource_storage_path) and os.path.isdir(self.user_resource_storage_path):

            executable = "/usr/bin/du"
            args = ["-sb", self.user_resource_storage_path]

            self._run_process(Process(exec_type="exec",
                                           executable=executable,
                                           executable_params=args))

            dc_size = int(self.module_output_log[0]["stdout"].split("\t")[0])
            quota_size = int(self.config.GRASS_RESOURCE_QUOTA * 1024*1024*1024)

            model = StorageModel(used=dc_size,
                                 free=quota_size - dc_size,
                                 quota=quota_size,
                                 free_percent=int(100 * (quota_size - dc_size)/quota_size))
            self.module_results = model

            self.finish_message = "Resource storage size successfully computed"
        else:
            raise AsyncProcessError("Resource storage directory <%s> does not exist."%self.user_resource_storage_path)


def start_resource_storage_remove(*args):
    processing = ResourceStorageDelete(*args)
    processing.run()


class ResourceStorageDelete(AsyncPersistentProcessing):
    """Delete the user specific resource directory
    """

    def __init__(self, *args):
        AsyncPersistentProcessing.__init__(self, *args)
        self.user_resource_storage_path = os.path.join(self.config.GRASS_RESOURCE_DIR, self.user_id)

    def _execute(self):

        self._setup()

        if os.path.exists(self.user_resource_storage_path) and os.path.isdir(self.user_resource_storage_path):
            executable = "/bin/rm"
            args = ["-rf", self.user_resource_storage_path]

            self._run_process(Process(exec_type="exec",
                                           executable=executable,
                                           executable_params=args))

            os.mkdir(self.user_resource_storage_path)
            self.finish_message = "Resource storage successfully removed."
        else:
            raise AsyncProcessError("Resource storage directory <%s> does not exist."%self.user_resource_storage_path)