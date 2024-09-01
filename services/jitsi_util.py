# !/usr/bin/python

import os
import time
import uuid

from authlib.jose import jwt
from django.conf import settings

from services.log import AppLogger


class JaaSJwtBuilder:
    """
        The JaaSJwtBuilder class helps with the generation of the JaaS JWT.
    """

    EXP_TIME_DELAY_SEC = 7200
    # Used as a delay for the exp claim value.

    NBF_TIME_DELAY_SEC = 10

    # Used as a delay for the nbf claim value.

    def __init__(self) -> None:
        self.header = {'alg': 'RS256'}
        self.user_claims = {}
        self.feature_claims = {}
        self.payload_claims = {}

    def with_defaults(self):
        """Returns the JaaSJwtBuilder with default valued claims."""
        return self.with_exp_time(int(time.time() + JaaSJwtBuilder.EXP_TIME_DELAY_SEC)) \
            .with_nbf_time(int(time.time() - JaaSJwtBuilder.NBF_TIME_DELAY_SEC)) \
            .with_live_streaming_enabled(True) \
            .with_recording_enabled(True) \
            .with_outbound_call_enabled(True) \
            .with_sip_outbound_call_enabled(True) \
            .with_transcription_enabled(True) \
            .with_moderator(True) \
            .with_room_name('*') \
            .with_user_id(str(uuid.uuid4()))

    def with_api_key(self, api_key):
        """
        Returns the JaaSJwtBuilder with the kid claim(api_key) set.

        :param api_key A string as the API Key https://jaas.8x8.vc/#/apikeys
        """
        self.header['kid'] = api_key
        return self

    def with_user_avatar(self, avatar_url):
        """
        Returns the JaaSJwtBuilder with the avatar claim set.

        :param avatar_url A string representing the url to get the user avatar.
        """
        self.user_claims['avatar'] = avatar_url
        return self

    def with_moderator(self, is_moderator):
        """
        Returns the JaaSJwtBuilder with the moderator claim set.

        :param is_moderator A boolean if set to True, user is moderator and False otherwise.
        """
        self.user_claims['moderator'] = 'true' if is_moderator == True else 'false'
        return self

    def with_username(self, username):
        """
        Returns the JaaSJwtBuilder with the name claim set.

        :param username A string representing the user's name.
        """
        self.user_claims['name'] = username
        return self

    def with_user_email(self, user_email):
        """
        Returns the JaaSJwtBuilder with the email claim set.

        :param user_email A string representing the user's email address.
        """
        self.user_claims['email'] = user_email
        return self

    def with_live_streaming_enabled(self, is_enabled):
        """
        Returns the JaaSJwtBuilder with the livestreaming claim set.

        :param is_enabled A boolean if set to True, live streaming is enabled and False otherwise.
        """
        self.feature_claims['livestreaming'] = 'true' if is_enabled == True else 'false'
        return self

    def with_recording_enabled(self, is_enabled):
        """
        Returns the JaaSJwtBuilder with the recording claim set.

        :param is_enabled A boolean if set to True, recording is enabled and False otherwise.
        """
        self.feature_claims['recording'] = 'true' if is_enabled == True else 'false'
        return self

    def with_transcription_enabled(self, is_enabled):
        """
        Returns the JaaSJwtBuilder with the transcription claim set.

        :param is_enabled A boolean if set to True, transcription is enabled and False otherwise.
        """
        self.feature_claims['transcription'] = 'true' if is_enabled == True else 'false'
        return self

    def with_sip_outbound_call_enabled(self, is_enabled):
        """
        Returns the JaaSJwtBuilder with the transcription claim set.

        :param is_enabled A boolean if set to True, transcription is enabled and False otherwise.
        """
        self.feature_claims['sip-outbound-call'] = 'true' if is_enabled == True else 'false'
        return self

    def with_outbound_call_enabled(self, is_enabled):
        """
        Returns the JaaSJwtBuilder with the outbound-call claim set.

        :param is_enabled A boolean if set to True, outbound calls are enabled and False otherwise.
        """
        self.feature_claims['outbound-call'] = 'true' if is_enabled == True else 'false'
        return self

    def with_exp_time(self, exp_time):
        """
        Returns the JaaSJwtBuilder with exp claim set. Use the defaults, you won't have to change this value too much.

        :param exp_time Unix time in seconds since epochs plus a delay. Expiration time of the JWT.
        """
        self.payload_claims['exp'] = exp_time
        return self

    def with_nbf_time(self, nbf_time):
        """
        Returns the JaaSJwtBuilder with nbf claim set. Use the defaults, you won't have to change this value too much.

        :param nbf_time Unix time in seconds since epochs.
        """
        self.payload_claims['nbfTime'] = nbf_time
        return self

    def with_room_name(self, room_name):
        """
        Returns the JaaSJwtBuilder with room claim set.

        :param room_name A string representing the room to join.
        """
        self.payload_claims['room'] = room_name
        return self

    def with_app_id(self, app_id):
        """
        Returns the JaaSJwtBuilder with the sub claim set.

        :param app_id A string representing the unique AppID (previously tenant).
        """
        self.payload_claims['sub'] = app_id
        return self

    def with_user_id(self, user_id):
        """
        Returns the JaaSJwtBuilder with the id claim set.

        :param user_id string representing the user, should be unique from your side.
        """
        self.user_claims['id'] = user_id
        return self

    def sign_with(self, key):
        """
        Returns a signed JWT.

        :param key A string representing the private key in PEM format.
        """
        context = {'user': self.user_claims, 'features': self.feature_claims}
        self.payload_claims['context'] = context
        self.payload_claims['iss'] = 'chat'
        self.payload_claims['aud'] = 'jitsi'
        return jwt.encode(self.header, self.payload_claims, key)


class JitsiUtil:

    @classmethod
    def __generate_token(cls):
        try:
            script_dir = os.path.dirname(__file__)
            AppLogger.print("script dir: {}".format(script_dir))
            fp = os.path.join(script_dir, 'jitsi-rsa-private.pk')

            with open(fp, 'r') as reader:
                jaas_jwt = JaaSJwtBuilder()
                token = jaas_jwt.with_defaults().with_api_key(settings.JITSI_API_KEY) \
                    .with_username(settings.JITSI_USERNAME).with_user_email(settings.JITSI_EMAIL) \
                    .with_moderator(True).with_app_id(settings.JITSI_APP_ID) \
                    .with_user_avatar("https://asda.com/avatar").sign_with(reader.read())

                return token
        except Exception as e:
            AppLogger.report(e)

        return None

    @classmethod
    def generate_meeting_payload(cls, room_name: str, is_admin: bool):
        data = {
            "app_id": settings.JITSI_APP_ID,
            "room": "{}/{}".format(settings.JITSI_APP_ID, room_name),
            "token": None
        }

        if is_admin:
            data["token"] = cls.__generate_token()

        return data
