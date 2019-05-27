import calendar
import time

from database.data_access_models import FileToProcess
from database.study_models import Study
from database.user_models import Participant
from libs.s3 import s3_upload, create_client_key_pair

from collections import namedtuple

_DeviceInfoRaw = namedtuple("DeviceInfo", [
    "bluetooth_mac_address",
    "phone_number",
    "device_id",
    "device_os",
    "os_version",
    "product",
    "brand",
    "hardware_id",
    "manufacturer",
    "model",
    "app_version"
])


class DeviceInfo(_DeviceInfoRaw):
    def build_header(self):
        return ",".join(self._fields)

    def build_values(self):
        return ",".join(["{0}".format(getattr(self, f)) for f in self._fields])


# Business Layer around database.user_models.Participant with some shared logic
class ParticipantBL:

    @classmethod
    def _upload_keys_to_s3(cls, patient_id, study_object_id):
        # Create an empty file on S3 indicating that this user exists
        s3_upload(patient_id, "", study_object_id)
        create_client_key_pair(patient_id, study_object_id)

    @classmethod
    def create_with_rnd_password(cls, study_id):
        """
        Creates a new participant with randomly generated patient_id and password.
        """
        patient_id, password = Participant.create_with_rnd_password(study_id=study_id)
        study_object_id = Study.objects.filter(pk=study_id).values_list('object_id', flat=True).get()
        cls._upload_keys_to_s3(patient_id, study_object_id)
        return patient_id, password

    @classmethod
    def register_created(cls, participant, password, OS_API, device_info, user_name=None):
        """
        Legacy API for registering pre-created user
        This is also re-used by the new "full" registration
        """
        patient_id = participant.patient_id
        study_id = participant.study.object_id
        # Upload the user's various identifiers.
        unix_time = str(calendar.timegm(time.gmtime()))
        file_name = patient_id + '/identifiers_' + unix_time + ".csv"

        # Construct a manual csv of the device attributes
        file_header = "patient_id"
        file_value = str(patient_id)
        file_header += "," + device_info.build_header()
        file_value += "," + device_info.build_values()
        # TODO SG: store user_name in the DB
        if user_name is not None:
            file_header += "," + "user_name"
            file_value += "," + user_name.replace(',', '_').replace(';', '_')
        file_contents = file_header + "\n" + file_value

        # print(file_contents)
        s3_upload(file_name, file_contents, study_id)
        print "FileToProcess participant='%s'" % participant
        # set up device.
        participant.set_password(password)  # this forces .save() call now
        participant.set_device(device_info.device_id)
        participant.set_os_type(OS_API)

        FileToProcess.append_file_for_processing(file_name, participant.study.object_id, participant=participant)

        return participant

    @classmethod
    def create_full(cls, study_object_id, user_name, password, OS_API, device_info):
        """
        Method to fully create a participant from the client side in one call
        """
        study_id = Study.objects.filter(object_id=study_object_id).values_list('pk', flat=True).get()
        participant = Participant.create_empty(study_id=study_id)
        cls._upload_keys_to_s3(participant.patient_id, study_object_id)
        cls.register_created(participant, password, OS_API, device_info, user_name)
        participant.save()
        return participant
