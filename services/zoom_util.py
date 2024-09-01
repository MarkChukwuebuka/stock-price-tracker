import json
import time, base64
from datetime import timedelta

import jwt
import requests
from django.utils import timezone
from requests.auth import HTTPBasicAuth
from zoom.client import Client

from services.cache_util import CacheUtil
from services.log import AppLogger
from services.util import make_http_request, HTTPMethods, generate_password


class ZoomUtil(CacheUtil, Client):

    def __init__(self):
        self.account_id = 'T_smnnnqT7WAOc3AECy7Zg'
        self.client_id = 'HIpMRgUdR4qZYjNGG28Neg'
        self.client_secret = '3d3WioQaW4bLppfZKDdg4yFnpytsENyH'

        # Define your API credentials
        super().__init__(self.client_id, self.client_secret)

        self.cache_key = self.generate_cache_key("zm", "at", 't')

    def do_get_access_token(self):
        url = "https://zoom.us/oauth/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        payload = {
            "grant_type": "client_credentials",
        }
        response = requests.post(url, headers=headers, data=payload,  auth=HTTPBasicAuth(
            self.client_id, self.client_secret
        ))
        response_data = response.json()

        return response_data.get("access_token"), None

    def create_new_meeting(self, topic):
        meeting = self.create_meeting(
            topic,
            duration=2,
            start_time=f"{(timezone.now() + timedelta(minutes=30))}",
            type=2,
            agenda="",
            default_password=True,
            password=generate_password(),
            pre_schedule=False,
            schedule_for=None,
            timezone="West Africa/Lagos",
            recurrence=None,
            settings=None,
        )

        AppLogger.print(meeting)

    def start_meeting(self, topic):
        # bearer_token, _ = self.get_cache_value_or_default(self.cache_key, self.do_get_access_token)

        # AppLogger.print(bearer_token)
        #
        # self.set_token(bearer_token)

        self.create_new_meeting(topic)
