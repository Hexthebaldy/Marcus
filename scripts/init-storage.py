"""Create the configured private S3 bucket and permit the editor's direct uploads."""
from botocore.exceptions import ClientError
from marcus.core.config import settings
from marcus.media.service import storage

client = storage()
try:
    client.head_bucket(Bucket=settings.s3_bucket)
except ClientError as exc:
    if str(exc.response['Error']['Code']) not in ('404', 'NoSuchBucket', 'NotFound'):
        raise
    args = {'Bucket': settings.s3_bucket}
    if settings.s3_region != 'us-east-1':
        args['CreateBucketConfiguration'] = {'LocationConstraint': settings.s3_region}
    client.create_bucket(**args)

client.put_bucket_cors(Bucket=settings.s3_bucket, CORSConfiguration={'CORSRules': [{
    'AllowedOrigins': settings.origins,
    'AllowedMethods': ['GET', 'HEAD', 'PUT'],
    'AllowedHeaders': ['*'],
    'ExposeHeaders': ['ETag'],
    'MaxAgeSeconds': 600,
}]})
print(f'Private media bucket ready: {settings.s3_bucket}')
