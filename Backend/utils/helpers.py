import hashlib
import secrets
import time
import string
import pytz
import random
from .custom_pagination import CustomPagination
from django.utils import timezone
from datetime import datetime


def paginate_data(data, request):
    limit = request.query_params.get('limit', None)
    offset = request.query_params.get('offset', None)

    if limit and offset:
        pagination = CustomPagination()
        data, count = pagination.paginate_queryset(data, request)
        return data, count
    else:
        return data, data.count()


def generate_token(str_):
    secret_salt = "un_breakable"
    str_ = f"{secrets.token_hex(32)}_{str_}_{timezone.now()}"
    combined = str_ + secret_salt
    token = hashlib.sha256(combined.encode('utf-8')).hexdigest()
    return token


def base36_encode(number):
    chars = string.digits + string.ascii_uppercase
    result = ''
    while number > 0:
        number, i = divmod(number, 36)
        result = chars[i] + result
    return result or '0'


def generate_otp(user_id):
    secret_salt = "tar*get_"
    timestamp = int(time.time())
    data = f"{user_id}_{timestamp}_{secret_salt}"
    hash_digest = hashlib.sha256(data.encode('utf-8')).hexdigest()
    hash_int = int(hash_digest, 16)
    base36_token = base36_encode(hash_int)
    otp = base36_token[:6].upper()
    return otp


def parse_datetime_string(dt_string: str):
    try:
        dt = datetime.fromisoformat(dt_string)
        if timezone.is_naive(dt):
            dt = pytz.UTC.localize(dt)
        return timezone.localtime(dt)

    except ValueError as e:
        raise ValueError(f"Invalid datetime format: {e}")


class UniqueSixDigitGenerator:
    def __init__(self):
        self.generated = set()

    def generate(self):
        if len(self.generated) >= 900000:
            raise Exception("All 6-digit numbers exhausted!")

        while True:
            num = random.randint(100000, 999999)
            if num not in self.generated:
                self.generated.add(num)
                return num

def generate_numeric_otp():
    obj = UniqueSixDigitGenerator()
    return obj.generate()