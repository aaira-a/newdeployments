
import re

from mydeploy import (
    connect_to_bucket,
    get_aws_credentials,
    )

# all paths are relative to jenkins job's workspace (absolute path is fine too)
AWS_CONFIG_PATH = ''    # path to config file (ini format) containing aws credentials
AWS_PROFILE = ''        # name of aws profile from the config file to be used

# name of buckets for connection purposes
CSS_BUCKET = ''
IMAGE_BUCKET = ''
JS_BUCKET = ''

# prefix of base path in buckets (eg, base folder name)
# to narrow down selections during bucket.list() operations
CSS_PREFIX = ''
IMAGE_PREFIX = ''
JS_PREFIX = ''


def cleanup_main():

    cred = get_aws_credentials(AWS_CONFIG_PATH, AWS_PROFILE)

    css_bucket = connect_to_bucket(cred, CSS_BUCKET)
    js_bucket = connect_to_bucket(cred, JS_BUCKET)
    image_bucket = connect_to_bucket(cred, IMAGE_BUCKET)

    css = [css_bucket, CSS_PREFIX]
    js = [js_bucket, JS_PREFIX]
    image = [image_bucket, IMAGE_PREFIX]

    for bucket in [css, js, image]:
        keys_to_delete = get_all_matching_keys(bucket[0], bucket[1])
        for key_ in keys_to_delete:
            key_.delete()
            print('Deleted http://' + bucket[0].name + '.s3.amazonaws.com/' + key_.key + '\n')


def get_all_matching_keys(bucket, prefix_=None):
    return [item for item in bucket.list(prefix=prefix_) if is_matching_versioned_pattern(item.key) is True]


def is_matching_versioned_pattern(path):
    return bool(re.search('\/(.*-.*\..*$)', path))


if __name__ == '__main__':
    cleanup_main()
