import requests
import ffmpeg
import os

from crm.models import Upload
from crm.services.uploads_service import UploadsService
from services.log import AppLogger


class VideoAudioUtil:

    @staticmethod
    def clean_up(temp_filename):
        try:
            os.remove(temp_filename)
        except Exception as e:
            AppLogger.report(e)

    @staticmethod
    def probe_media_duration(upload: Upload):
        url = upload.file_url
        original_file_name = url.lower()

        service = UploadsService()
        upload, _ = service.fetch_url_duration(url)
        if upload:
            return upload.duration

        file_extension = original_file_name.split('.')[-1].lower()
        temp_filename = "{}.{}".format("tempfile", file_extension)
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with open(temp_filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            probe = ffmpeg.probe(temp_filename)
            duration = float(probe['format']['duration'])

            service.update_url_duration(url, duration)
            return duration
        except requests.RequestException as e:
            AppLogger.report(e)
        except ffmpeg.Error as e:
            AppLogger.report(e)
        except Exception as e:
            AppLogger.report(e)
        finally:
            VideoAudioUtil.clean_up(temp_filename)

        return None
