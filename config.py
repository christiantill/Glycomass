import os


class Config(object):
    SECRET_KEY = os.environ.get("SECRET_KEY")
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')


    S3_BUCKET = os.environ.get("S3_BUCKET")
    S3_KEY = os.environ.get("S3_KEY")
    S3_SECRET = os.environ.get("S3_SECRET")
    S3_LOCATION = 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)

    csp = {
        'font-src': [
            'themes.googleusercontent.com',
            '*.gstatic.com',
        ],
        'img-src': [
            '\'self\'',
            '*.bootstrapcdn.com',
            '*.googleapis.com',
            "www.google-analytics.com",
            "*.s3.amazonaws.com /",
        ],
        'style-src': [
            '\'self\'',
            'stackpath.bootstrapcdn.com',
            'fonts.googleapis.com',
            'ajax.googleapis.com',
            '*.gstatic.com',
        ],
        'script-src': [
            '\'self\'',
            'https://maxcdn.bootstrapcdn.com',
            'https://code.jquery.com',
            'https://www.google.com',
            'ajax.googleapis.com',
            'www.googletagmanager.com',
            '*.googleanalytics.com',
            '*.google-analytics.com',
            '*',
        ],
        'frame-src': [
            '\'self\'',
            'www.google.com',
            'www.youtube.com',
        ],
        'default-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'stackpath.bootstrapcdn.com',
        'code.jquery.com',
        'cdn.jsdelivr.net'
        ],
    }


