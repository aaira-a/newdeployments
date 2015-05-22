import unittest

from mycleanup import (
    get_all_matching_keys,
    is_matching_versioned_pattern,
    )

import mycleanup

from mydeploy import (
    file_exists_in_s3_bucket as exists,
    upload_gzipped_file_to_bucket as upload,
    )

import boto
from contextlib import redirect_stdout
import io
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
        mycleanup.XML_PATH = 'fixtures/end_to_end/config/fileVersion3.xml'

    @moto.mock_s3
    def test_end_to_end_cleanup_should_delete_files_with_matching_pattern(self):

        connection = boto.connect_s3('key', 'secret')
        bucket_css = connection.create_bucket(mycleanup.CSS_BUCKET)
        bucket_js = connection.create_bucket(mycleanup.JS_BUCKET)
        bucket_image = connection.create_bucket(mycleanup.IMAGE_BUCKET)

        upload('fixtures/end_to_end/css/common.css', 'css/common-13241.css', 'css', bucket_css)
        self.assertTrue(exists('css/common-13241.css', bucket_css))

        upload('fixtures/end_to_end/js/apply.js', 'scripts/apply-14442.js', 'js', bucket_js)
        self.assertTrue(exists('scripts/apply-14442.js', bucket_js))

        upload('fixtures/end_to_end/images/image001.png', 'images/image001-14665.png', 'image', bucket_image)
        self.assertTrue(exists('images/image001-14665.png', bucket_image))

        out = io.StringIO()

        with redirect_stdout(out):
            mycleanup.cleanup_main()
        output = out.getvalue()

        expected_string_outputs = [
            'Deleted http://myrandombucket-0001.s3.amazonaws.com/css/common-13241.css',
            'Deleted http://myrandombucket-0002.s3.amazonaws.com/scripts/apply-14442.js',
            'Deleted http://myrandombucket-0003.s3.amazonaws.com/images/image001-14665.png']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertFalse(exists('css/common-13241.css', bucket_css))
        self.assertFalse(exists('scripts/apply-14442.js', bucket_js))
        self.assertFalse(exists('images/image001-14665.png', bucket_image))

    @moto.mock_s3
    def test_end_to_end_cleanup_should_not_delete_files_not_matching_pattern(self):

        connection = boto.connect_s3('key', 'secret')
        bucket_css = connection.create_bucket(mycleanup.CSS_BUCKET)
        bucket_js = connection.create_bucket(mycleanup.JS_BUCKET)
        bucket_image = connection.create_bucket(mycleanup.IMAGE_BUCKET)

        upload('fixtures/end_to_end/css/common.css', 'css/nottobedeleted.css', 'css', bucket_css)
        self.assertTrue(exists('css/nottobedeleted.css', bucket_css))

        upload('fixtures/end_to_end/js/apply.js', 'scripts/nottobedeleted.js', 'js', bucket_js)
        self.assertTrue(exists('scripts/nottobedeleted.js', bucket_js))

        upload('fixtures/end_to_end/images/image001.png', 'images/nottobedeleted.png', 'image', bucket_image)
        self.assertTrue(exists('images/nottobedeleted.png', bucket_image))

        mycleanup.cleanup_main()

        self.assertTrue(exists('css/nottobedeleted.css', bucket_css))
        self.assertTrue(exists('scripts/nottobedeleted.js', bucket_js))
        self.assertTrue(exists('images/nottobedeleted.png', bucket_image))

    @moto.mock_s3
    def test_end_to_end_cleanup_should_skip_files_indexed_in_xml(self):

        connection = boto.connect_s3('key', 'secret')
        bucket_css = connection.create_bucket(mycleanup.CSS_BUCKET)
        bucket_js = connection.create_bucket(mycleanup.JS_BUCKET)
        bucket_image = connection.create_bucket(mycleanup.IMAGE_BUCKET)

        upload('fixtures/end_to_end/css/to_persist_cleanup.css', 'css/to_persist_cleanup-9000.css', 'css', bucket_css)
        self.assertTrue(exists('css/to_persist_cleanup-9000.css', bucket_css))

        out = io.StringIO()

        with redirect_stdout(out):
            mycleanup.cleanup_main()
        output = out.getvalue()

        expected_string_outputs = [
            'Skipping deletion of http://myrandombucket-0001.s3.amazonaws.com/css/to_persist_cleanup-9000.css, '
            'currently indexed in XML file']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertTrue(exists('css/to_persist_cleanup-9000.css', bucket_css))
