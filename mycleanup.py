
import re

from mydeploy import (
    get_file_objects,
    S3Util,
    )

from environment_config import (
    AWS_CONFIG_PATH,
    AWS_PROFILE,
    CSS_BUCKET,
    IMAGE_BUCKET,
    JS_BUCKET,
    CSS_PREFIX,
    IMAGE_PREFIX,
    JS_PREFIX,
    XML_PATH
    )


def cleanup_main():

    c = S3Util.create_connection_pools(AWS_CONFIG_PATH, AWS_PROFILE,
                                       CSS_BUCKET, JS_BUCKET, IMAGE_BUCKET)

    existing_versioned_files_in_xml = get_file_objects(c, XML_PATH)

    keys_in_xml = [item.versioned_path_in_bucket for item in existing_versioned_files_in_xml]

    for bucket in [
                   (c['css_bucket'], CSS_PREFIX),
                   (c['js_bucket'], JS_PREFIX),
                   (c['image_bucket'], IMAGE_PREFIX)]:

        keys_matching_pattern = get_all_matching_keys(bucket[0], bucket[1])

        for key_ in keys_matching_pattern:

            if (key_.key in keys_in_xml):
                print('Skipping deletion of http://' + bucket[0].name + '.s3.amazonaws.com/' + key_.key +
                      ', currently indexed in XML file \n')

            else:
                key_.delete()
                print('Deleted http://' + bucket[0].name + '.s3.amazonaws.com/' + key_.key + '\n')


def get_all_matching_keys(bucket, prefix_=None):
    return [item for item in bucket.list(prefix=prefix_) if is_matching_versioned_pattern(item.key) is True]


def is_matching_versioned_pattern(path):
    return bool(re.search('\/(.*-\d{12}\..*$)', path))


if __name__ == '__main__':
    cleanup_main()
