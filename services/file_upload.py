import time
from datetime import datetime

import cloudinary
import cloudinary.uploader
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from crm.models import Upload
from services.util import CustomAPIRequestUtil


class FileUploader(CustomAPIRequestUtil):
    DEFAULT_IMAGE_EXTENSIONS = ["jpg", "jpeg", "png"]

    def __init__(self, request, upload_to):
        super().__init__(request)
        self.request = request
        self.upload_to = upload_to.strip("/")

    def upload(self, file):
        original_file_name = file.name.lower()
        file_extension = original_file_name.split('.')[-1].lower()
        file_size = self.get_file_size(file)

        if file_size > (settings.MAX_FILE_SIZE):
            return None, self.make_error("File too large")

        date = datetime.strftime(timezone.now(), "%Y/%m/%d")
        file_path = f"{self.upload_to}/{date}/"

        full_url, error = self.save_to_cloudinary(file, file_path)

        if error:
            return None, error

        uploaded_file = Upload.objects.create(
            file_url=full_url,
            file_name=original_file_name.strip(f".{file_extension}"),
            file_size=file_size,
            file_type=self.get_content_type_from_extension(file_extension),
            created_by=self.auth_user
        )

        return uploaded_file, None

    def save_to_cloudinary(self, file, folder):
        try:
            result = cloudinary.uploader.upload(file, folder=f"{folder}", resource_type='auto')
            return result.get("secure_url"), None
        except Exception as e:
            return None, self.make_500(e)

    def generate_file_name(self, ext):
        return str(time.time()).replace('.', '') + f".{ext}"

    def delete(self, file_path):
        storage = default_storage
        return storage.delete(file_path)

    def get_file_size(self, file):
        original_position = file.tell()  # Store the original position
        file.seek(0, 2)  # Move the file pointer to the end of the file
        file_size = file.tell()  # Get the current position (file size)
        file.seek(original_position)  # Return to the original position
        return file_size

    def get_content_type_from_extension(self, file_extension):
        extension_mapping = {
            'txt': 'text/plain',
            'jpg': 'image/jpeg',
            'png': 'image/png',
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'mp4': 'video/mp4',
            'mp3': 'audio/mp3',
            'html': 'text/html',
            'css': 'text/css',
        }

        return extension_mapping.get(file_extension, 'application/octet-stream')
