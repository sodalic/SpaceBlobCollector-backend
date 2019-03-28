from django.conf import settings
from constants import DATA_THRESHOLD

import boto3


def check_gps_data(study_id, patient_id, start_date=None):
    _check_data_existence(study_id, patient_id, "gps", start_date)


def check_accelerometer_data(study_id, patient_id, start_date=None):
    _check_data_existence(study_id, patient_id, "accelerometer", start_date)


def check_power_state_data(study_id, patient_id, start_date=None):
    _check_data_existence(study_id, patient_id, "power_state", start_date)


def check_calls_data(study_id, patient_id, start_date=None):
    _check_data_existence(study_id, patient_id, "calls", start_date)


def check_texts_data(study_id, patient_id, start_date=None):
    _check_data_existence(study_id, patient_id, "texts", start_date)


def check_survey_timings_data(study_id, patient_id, start_date=None):
    _check_data_existence(study_id, patient_id, "survey_timings", start_date)


# Helper methods
def _check_data_existence(study_id, patient_id, data_type, start_date=None):
    """
    Checks existence of data (represented in data_type) for a patient in a study.

    :param study_id: (String) study id
    :param patient_id: (String) patient id
    :param data_type: (String) the kind of data we're checking for (e.g gps, accelerometer etc..)
    :param start_date: (Datetime - ** Must be in UTC **) used as the upper limit of the S3 query.

    :return: (Bool) whether the patient has enough data to pass the required threshold or not.
    """
    
    bucket = boto3.resource('s3',
                            aws_access_key_id=settings.BEIWE_SERVER_AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.BEIWE_SERVER_AWS_SECRET_ACCESS_KEY
                            ).Bucket(name=settings.S3_BUCKET)
    query_prefix = "CHUNKED_DATA/%s/%s/%s/" % (study_id, patient_id, data_type)
    if start_date:
        query_prefix += str(start_date.date())
    total_size = 0
    for s3_file in bucket.objects.filter(Prefix=query_prefix):
        total_size += s3_file.size

    return total_size >= DATA_THRESHOLD.get(data_type, 0)
