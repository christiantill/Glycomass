import os


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')


    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_KEY = os.environ.get("S3_KEY")
    S3_SECRET = os.environ.get("S3_SECRET")
    S3_LOCATION = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)

    csp = {
        'default-src': [
            '\'self\'',
            '\'unsafe-inline\'',
            'stackpath.bootstrapcdn.com',
            'code.jquery.com',
            'cdn.jsdelivr.net'
        ]
    }

