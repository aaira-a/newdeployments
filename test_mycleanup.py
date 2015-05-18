import unittest

from mycleanup import (
    get_all_matching_keys,
    is_matching_versioned_pattern,
    )


import boto
import moto


class VersionedPatternCheckerTest(unittest.TestCase):

    def test_path_with_simple_dash_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/myfile-0001.js'))

    def test_path_in_subdirectories_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/folder/myfile-0001.css'))

    def test_path_with_multiple_dashes_in_path_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/fol-der/my-file-00-01.css'))

    def test_path_with_multiple_dots_in_path_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/fol.der/my.file0001-v1.5.3.css'))

    def test_path_without_dash_in_filename_should_return_false(self):
        self.assertFalse(is_matching_versioned_pattern('/folder/myfile0001.js'))


class GetMatchingKeysIntegrationTest(unittest.TestCase):

    @moto.mock_s3()
    def test_get_matched_pattern_key_with_prefix_should_return_correct_item(self):
        paths = ['prefix1/d/file1.css',
                 'prefix1/d/file2.css',
                 'prefix1/d/file3-v1.0.0.css',
                 'prefix2/d/file4-123.js',
                 'prefix2/d/file5.js',
                 'prefix3/d/file6-23.png',
                 'prefix3/d/file7.1.2.3.jpg']

        conn = boto.connect_s3('key', 'secret')
        bucket = conn.create_bucket('mybucket567')

        for item in paths:
            k = boto.s3.key.Key(bucket)
            k.key = item
            k.set_contents_from_string(item)

        result1 = get_all_matching_keys(bucket, 'prefix1')
        self.assertIn('prefix1/d/file3-v1.0.0.css', result1[0].key)

        result2 = get_all_matching_keys(bucket, 'prefix2')
        self.assertIn('prefix2/d/file4-123.js', result2[0].key)

        result3 = get_all_matching_keys(bucket, 'prefix3')
        self.assertIn('prefix3/d/file6-23.png', result3[0].key)
