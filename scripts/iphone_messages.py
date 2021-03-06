# This script is tested to have identical output and be compatible with Python 2.7 and 3.6.
# (It really should be compatible with any version of Python 3.)
from __future__ import print_function

import base64
import csv
import hashlib
import sys
from datetime import datetime
from os.path import sep as SYSTEM_FOLDER_SEPARATOR
from sys import argv

# This script has 1 dependancy: pytz.
# pytz is effectively part of the python std library, but it needs to be updated more frequently
# than python itself is updated, and having it as a non-std library allows these changes to be
# centralized.
try:
    import pytz
except ImportError:
    print("This script requires the 'pytz' library be installed, it is required to handle timezone coversions correctly.")
    print("Installing pytz should be as simple as running 'pip install pytz'.")
    exit(1)

IS_PYTHON_2 = True if sys.version[0] == '2' else False

OUTPUT_COLUMNS = [
    "timestamp",
    "UTC time",
    "hashed phone number",
    "sent vs received",
    "message length",
    "time sent",
]

NECESSARY_COLUMNS = [
    "Message Date",         # timestamp
    "Type",                 # "Incoming" or "Outgoing"
    "Text",                 # message content
    "Sender ID",            # Usually a phone number, might be a different value, gets hashed
]

TZ_HELP_STRING = "--tz-help"
INPUT_CSV_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
OUTPUT_CSV_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"
PYTHON_FILE_NAME = __file__.split(SYSTEM_FOLDER_SEPARATOR)[-1] if SYSTEM_FOLDER_SEPARATOR in __file__ else __file__

HASH_CACHE = {}

#############################
### Arg Parsing and Setup ###
#############################
# argv[0] = name of this file
# argv[1] = path of csv file to operate on
# argv[2] = timezone to assume when extracting data

# if the user has provided the timezone help argument anywhere print all timezones
if TZ_HELP_STRING in argv:
    print("All timezone options (%s):" % len(pytz.all_timezones))
    for t in pytz.all_timezones:
        print("\t", t)
    exit(0)

if len(argv) in [1, 2]:
    print("Usage: %s csv_file_to_parse timezone" % PYTHON_FILE_NAME)
    print()
    print("First parameter: a csv file.")
    print("Second parameter: a string indicating the timezone to use.")
    print()
    print("(Try '%s %s' for a listing of available timezones)." % (PYTHON_FILE_NAME, TZ_HELP_STRING))
    exit(1)

tz = argv[2]
try:
    tz = pytz.timezone(tz)
except pytz.UnknownTimeZoneError:
    print("Unregognized timezone:", tz)
    print("(Try '%s %s' for a listing of available timezones)." % (PYTHON_FILE_NAME, TZ_HELP_STRING))
    exit(1)

INPUT_FILE_NAME = argv[1]

# attempt to get a nice-ish output file name right next to the input file.
if INPUT_FILE_NAME.endswith(".csv"):
    OUTPUT_FILE_NAME = INPUT_FILE_NAME[:-4] + ".out.csv"
else:
    OUTPUT_FILE_NAME = INPUT_FILE_NAME + ".out.csv"

# This method of consuming the input file should handle all newline cases correctly.
with open(INPUT_FILE_NAME) as f:
    csv_reader = csv.DictReader(f.read().splitlines())

# throw any errors about missing, necessary
for fieldname in NECESSARY_COLUMNS:
    assert fieldname in csv_reader.fieldnames, "This file is missing the '%s' column."

###############
### Helpers ###
###############

def add_tz_to_naive_datetime(dt):
    # is_dst=False is the default, sticking it here for complexity
    return tz.localize(dt, is_dst=False)


def input_csv_datetime_string_to_tz_aware_datetime(dt_string):
    dt = datetime.strptime(dt_string, INPUT_CSV_DATE_FORMAT)
    return add_tz_to_naive_datetime(dt)


def dt_to_utc_timestamp(dt):
    # this appears to be the most compatible way to get the unix timestamp.
    return dt.strftime("%s")


def dt_to_output_format(dt):
    # convert to the datetime string format from beiwe backend
    return dt.strftime(OUTPUT_CSV_DATE_FORMAT)


def hash_contact_id(contact_id):
    """ The Android app mechanism for hashng contacts is to use pbkdf2 on the last 10 digits of
    the contact's phone number.  To imitate this exactly requires more information than is
    available in the script (we would need an iteration count and a salt).
    Instead all we do here is a single, standard SHA256 round.
    (contact_id in a csv is usually the digits of a phone number, but this is not always the case.
    """
    # Python 2 vs 3, encode/decode issues. Normalize encoding of the base64 output string to a
    # string in all cases (unicode object in python 2, str in python 3).

    # hashing is slow, but we can cache to get a huge speedup.
    if contact_id in HASH_CACHE:
        return HASH_CACHE[contact_id]

    sha256 = hashlib.sha256()

    # iteration count of 512
    def update_many_times():
        for _ in range(10000):
            sha256.update(sha256.digest())

    # the python 2 and 3 code has been tested, they result in the same output.
    if IS_PYTHON_2:
        sha256.update(contact_id)
        update_many_times()
        digest = sha256.digest()
        ret = base64.urlsafe_b64encode(digest)
    else:
        sha256.update(contact_id.encode())    # unicode -> bytes
        update_many_times()
        digest = sha256.digest()
        ret = base64.urlsafe_b64encode(digest)
        ret = ret.decode()                    # bytes -> unicode

    # clear any new lines, cache result
    ret = ret.replace("\n", "")
    HASH_CACHE[contact_id] = ret
    return ret


def consisent_character_length(text):
    # python 2 and 3 have different string formats, we want to use unicode encoding because
    # the length should be the number of characters, not the number of 7-bit ascii bytes.
    if IS_PYTHON_2:
        return len(text.decode("utf-8"))
    else:
        return len(text)


############
### Main ###
############

def extract_data():
    output_rows = []
    for input_row in csv_reader:
        output_row = {}

        # First get the datetime objects we will need
        dt = input_csv_datetime_string_to_tz_aware_datetime(input_row["Message Date"])
        unix_timestamp = dt_to_utc_timestamp(dt)

        # text csv has 3 timestamps, but they all are from the same source
        output_row["timestamp"] = unix_timestamp
        output_row["time sent"] = unix_timestamp
        output_row["UTC time"] = dt_to_output_format(dt)

        # get a hashed id of the message sender (always the same for any given user)
        output_row["hashed phone number"] = hash_contact_id(input_row["Sender ID"])

        # length row is very simple.
        output_row["message length"] = consisent_character_length(input_row["Text"])

        # populate sent vs received with the expected string.
        # (doing a case insensitive compare for paranoid safety.)
        message_type = input_row["Type"].lower()
        output_row["sent vs received"] = "received SMS" if message_type == "incoming" else "sent SMS"

        # assemble the data into a correctly ordered list
        output_rows.append([output_row[column] for column in OUTPUT_COLUMNS])

    # sort by time (integer value of first column, which is the unix timestamp)
    output_rows.sort(key=lambda x: int(x[0]))
    return output_rows


def write_data(output_rows):
    # write the extracted data to a csv file (default csv dialect is excel) next to the input file
    with open(OUTPUT_FILE_NAME, "w") as out_file:
        csv_writer = csv.writer(out_file)
        csv_writer.writerow(OUTPUT_COLUMNS)
        for output_row in output_rows:
            csv_writer.writerow(output_row)
    print("Data conversion finished, output file is", OUTPUT_FILE_NAME)


write_data(extract_data())
