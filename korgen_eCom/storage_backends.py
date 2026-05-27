from storages.backends.s3 import S3Storage


class StaticStorage(S3Storage):
    location = 'static'


class MediaStorage(S3Storage):
    location = 'media'
