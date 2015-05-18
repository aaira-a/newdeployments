
import re


def is_matching_versioned_pattern(path):
    return bool(re.search('\/(.*-.*\..*$)', path))
