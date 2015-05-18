
import re


def get_all_matching_keys(bucket, prefix_):
    return [item for item in bucket.list(prefix=prefix_) if is_matching_versioned_pattern(item.key) is True]


def is_matching_versioned_pattern(path):
    return bool(re.search('\/(.*-.*\..*$)', path))
