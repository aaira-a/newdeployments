import unittest

from mycleanup import (
    get_all_matching_keys,
    is_matching_versioned_pattern,
    )

import mycleanup

from mydeploy import S3Util

import boto
from contextlib import redirect_stdout
import io
import moto


exists = S3Util.file_exists_in_s3_bucket
upload = S3Util.upload_gzipped_file_to_bucket

VALID_VERSION = '000000000012'


class VersionedPatternCheckerTest(unittest.TestCase):

    def test_path_with_simple_dash_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/myfile-' + VALID_VERSION + '.js'))

    def test_path_in_subdirectories_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/folder/myfile-' + VALID_VERSION + '.css'))

    def test_path_with_multiple_dashes_in_path_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/fol-der/my-file-' + VALID_VERSION + '.css'))

    def test_path_with_multiple_dots_in_path_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/fol.der/my.file0001v1.2.3-' + VALID_VERSION + '.css'))

    def test_path_without_dash_in_filename_should_return_false(self):
        self.assertFalse(is_matching_versioned_pattern('/folder/myfile' + VALID_VERSION + '.js'))

    def test_path_with_version_length_11_should_return_false(self):
        self.assertFalse(is_matching_versioned_pattern('/myfile-00000000011.js'))

    def test_path_with_version_length_12_should_return_true(self):
        self.assertTrue(is_matching_versioned_pattern('/myfile-' + VALID_VERSION + '.js'))

    def test_path_with_version_length_13_should_return_false(self):
        self.assertFalse(is_matching_versioned_pattern('/myfile-0000000000013.js'))

    def test_path_with_version_length_12_but_not_all_numbers_should_return_false(self):
        self.assertFalse(is_matching_versioned_pattern('/myfile-oooooooooo12.js'))


class GetMatchingKeysIntegrationTest(unittest.TestCase):

    @moto.mock_s3()
    def test_get_matched_pattern_key_with_prefix_should_return_correct_item(self):
        paths = ['prefix1/d/file1.css',
                 'prefix1/d/file2.css',
                 'prefix1/d/file3-' + VALID_VERSION + '.css',
                 'prefix2/d/file4-' + VALID_VERSION + '.js',
                 'prefix2/d/file5.js',
                 'prefix3/d/file6-' + VALID_VERSION + '.png',
                 'prefix3/d/file7.1.2.3.jpg']

        conn = boto.connect_s3('key', 'secret')
        bucket = conn.create_bucket('mybucket567')

        for item in paths:
            k = boto.s3.key.Key(bucket)
            k.key = item
            k.set_contents_from_string(item)

        result1 = get_all_matching_keys(bucket, 'prefix1')
        self.assertIn('prefix1/d/file3-' + VALID_VERSION + '.css', result1[0].key)

        result2 = get_all_matching_keys(bucket, 'prefix2')
        self.assertIn('prefix2/d/file4-' + VALID_VERSION + '.js', result2[0].key)

        result3 = get_all_matching_keys(bucket, 'prefix3')
        self.assertIn('prefix3/d/file6-' + VALID_VERSION + '.png', result3[0].key)


class CleanupMainIntegrationTest(unittest.TestCase):

    def setUp(self):
        mycleanup.AWS_CONFIG_PATH = 'fixtures/end_to_end/boto2.cfg'
        mycleanup.AWS_PROFILE = 'dev'
        mycleanup.CSS_BUCKET = 'myrandombucket-0001'
        mycleanup.IMAGE_BUCKET = 'myrandombucket-0003'
        mycleanup.JS_BUCKET = 'myrandombucket-0002'
        mycleanup.CSS_PREFIX = 'css/'
        mycleanup.IMAGE_PREFIX = 'images/'
        mycleanup.JS_PREFIX = 'scripts/'
        mycleanup.XML_PATH = 'fixtures/end_to_end/config/mycleanup.xml'

    def initialise_buckets(self):

        connection = boto.connect_s3('key', 'secret')
        self.bucket_css = connection.create_bucket(mycleanup.CSS_BUCKET)
        self.bucket_js = connection.create_bucket(mycleanup.JS_BUCKET)
        self.bucket_image = connection.create_bucket(mycleanup.IMAGE_BUCKET)

    def execute(self):
        out = io.StringIO()

        with redirect_stdout(out):
            mycleanup.cleanup_main()

        return out.getvalue()

    @moto.mock_s3
    def test_end_to_end_cleanup_should_delete_files_with_matching_pattern(self):

        self.initialise_buckets()

        upload('fixtures/end_to_end/css/common.css', 'css/common-' + VALID_VERSION + '.css', 'css', self.bucket_css)
        self.assertTrue(exists('css/common-' + VALID_VERSION + '.css', self.bucket_css))

        upload('fixtures/end_to_end/scripts/apply.js', 'scripts/apply-' + VALID_VERSION + '.js', 'js', self.bucket_js)
        self.assertTrue(exists('scripts/apply-' + VALID_VERSION + '.js', self.bucket_js))

        upload('fixtures/end_to_end/images/image001.png', 'images/image001-' + VALID_VERSION + '.png', 'image', self.bucket_image)
        self.assertTrue(exists('images/image001-' + VALID_VERSION + '.png', self.bucket_image))

        output = self.execute()

        expected_string_outputs = [
            'Deleted http://myrandombucket-0001.s3.amazonaws.com/css/common-' + VALID_VERSION + '.css',
            'Deleted http://myrandombucket-0002.s3.amazonaws.com/scripts/apply-' + VALID_VERSION + '.js',
            'Deleted http://myrandombucket-0003.s3.amazonaws.com/images/image001-' + VALID_VERSION + '.png']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertFalse(exists('css/common-' + VALID_VERSION + '.css', self.bucket_css))
        self.assertFalse(exists('scripts/apply-' + VALID_VERSION + '.js', self.bucket_js))
        self.assertFalse(exists('images/image001-' + VALID_VERSION + '.png', self.bucket_image))

    @moto.mock_s3
    def test_end_to_end_cleanup_should_not_delete_files_not_matching_pattern(self):

        self.initialise_buckets()

        upload('fixtures/end_to_end/css/common.css', 'css/nottobedeleted.css', 'css', self.bucket_css)
        self.assertTrue(exists('css/nottobedeleted.css', self.bucket_css))

        upload('fixtures/end_to_end/scripts/apply.js', 'scripts/nottobedeleted.js', 'js', self.bucket_js)
        self.assertTrue(exists('scripts/nottobedeleted.js', self.bucket_js))

        upload('fixtures/end_to_end/images/image001.png', 'images/nottobedeleted.png', 'image', self.bucket_image)
        self.assertTrue(exists('images/nottobedeleted.png', self.bucket_image))

        self.execute()

        self.assertTrue(exists('css/nottobedeleted.css', self.bucket_css))
        self.assertTrue(exists('scripts/nottobedeleted.js', self.bucket_js))
        self.assertTrue(exists('images/nottobedeleted.png', self.bucket_image))

    @moto.mock_s3
    def test_end_to_end_cleanup_should_skip_files_indexed_in_xml(self):

        self.initialise_buckets()

        upload('fixtures/end_to_end/css/to_persist_cleanup.css', 'css/to_persist_cleanup-' + VALID_VERSION + '.css', 'css', self.bucket_css)
        self.assertTrue(exists('css/to_persist_cleanup-' + VALID_VERSION + '.css', self.bucket_css))

        output = self.execute()

        expected_string_outputs = [
            'Skipping deletion of http://myrandombucket-0001.s3.amazonaws.com/css/to_persist_cleanup-' + VALID_VERSION + '.css, '
            'currently indexed in XML file']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertTrue(exists('css/to_persist_cleanup-' + VALID_VERSION + '.css', self.bucket_css))
