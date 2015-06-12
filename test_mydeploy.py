import unittest
from unittest import mock

from mydeploy import (
    Minifier,
    S3Util,
    StaticFile,
    XMLParser,
    )

import mydeploy

import boto
from contextlib import redirect_stdout
import io
import moto
import os.path

exists = S3Util.file_exists_in_s3_bucket
upload = S3Util.upload_gzipped_file_to_bucket

VALID_VERSION = '000000000012'


class XMLTest(unittest.TestCase):

    def test_open_xml_fixture_should_return_packed_lists(self):
        expected_list = [
            ['common.css', 'css', '1423532041'],
            ['path/to/component.css', 'css', '1423532040'],
            ['validation.js', 'js', '1408592767'],
            ['path/to/default.js', 'js', '1408592767'], ]
        self.assertEqual(
            XMLParser.create_matrix_from_xml('fixtures/fileVersion.xml'),
            expected_list)


class YUICompressorTest(unittest.TestCase):

    @mock.patch('subprocess.call')
    def test_compress_css_should_call_yuicompressor_with_correct_syntax(self, mock_subprocess):
        Minifier.compress_css('input', 'output')
        mock_subprocess.assert_called_with(
            ['java', '-jar', 'yuicompressor-2.4.8.jar', 'input', '-o', 'output'])

    @mock.patch('subprocess.call')
    def test_compress_css_should_return_zero_if_compression_is_successful(self, mock_subprocess):
        mock_subprocess.return_value = 0
        return_code = Minifier.compress_css('fixtures/styles.css', 'output')
        self.assertEqual(return_code, 0)

    @mock.patch('subprocess.call')
    def test_compress_css_should_return_1_if_compression_is_unsuccessful(self, mock_subprocess):
        mock_subprocess.return_value = 1
        return_code = Minifier.compress_css('fixtures/notfound.css', 'output')
        self.assertEqual(return_code, 1)


class ClosureCompilerTest(unittest.TestCase):

    @mock.patch('subprocess.call')
    def test_compile_js_should_call_compiler_with_correct_syntax(self, mock_subprocess):
        Minifier.compile_js('input', 'output')
        mock_subprocess.assert_called_with(
            ['java', '-jar', 'compiler.jar', '--js', 'input', '--js_output_file', 'output'])

    @mock.patch('subprocess.call')
    def test_compile_js_should_return_zero_if_compilation_is_successful(self, mock_subprocess):
        mock_subprocess.return_value = 0
        return_code = Minifier.compile_js('fixtures/cells.js', 'output')
        self.assertEqual(return_code, 0)

    @mock.patch('subprocess.call')
    def test_compile_js_should_return_1_if_compilation_is_unsuccessful(self, mock_subprocess):
        mock_subprocess.return_value = 1
        return_code = Minifier.compile_js('fixtures/notfound.js', 'output')
        self.assertEqual(return_code, 1)


class GZipTest(unittest.TestCase):

    def test_gzip_file_should_produce_smaller_file_than_original(self):
        input_path = 'fixtures/styles.css'
        output_path = 'fixtures/styles.css.suffix'

        self.assertFalse(os.path.exists(output_path))
        Minifier.gzip_file(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))

        input_size = os.path.getsize(input_path)
        output_size = os.path.getsize(output_path)

        self.assertLess(output_size, input_size)

        os.remove(output_path)
        self.assertFalse(os.path.exists(output_path))


class VersionedPathTest(unittest.TestCase):

    def factory(self, path, type_, version):
        connection_pools = {'css_bucket': '', 'js_bucket': '', 'image_bucket': ''}
        return StaticFile('', path, type_, version, connection_pools)

    def test_get_versioned_path_from_css_file(self):
        static_css = self.factory('fixtures/styles.css', 'css', '9001')
        self.assertEqual(static_css.get_versioned_file_path(), 'css/fixtures/styles-9001.css')

    def test_get_versioned_path_from_js_file(self):
        static_js = self.factory('fixtures/cells.js', 'js', '9002')
        self.assertEqual(static_js.get_versioned_file_path(), 'scripts/fixtures/cells-9002.js')

    def test_get_versioned_path_from_gif_image_file(self):
        static_image = self.factory('fixtures/image001.gif', 'image', '9003')
        self.assertEqual(static_image.get_versioned_file_path(), 'images/fixtures/image001-9003.gif')

    def test_get_versioned_path_from_jpg_image_file(self):
        static_image = self.factory('fixtures/image002.jpg', 'image', '9004')
        self.assertEqual(static_image.get_versioned_file_path(), 'images/fixtures/image002-9004.jpg')

    def test_get_versioned_path_from_jpeg_image_file(self):
        static_image = self.factory('fixtures/image003.jpeg', 'image', '9005')
        self.assertEqual(static_image.get_versioned_file_path(), 'images/fixtures/image003-9005.jpeg')

    def test_get_versioned_path_from_png_image_file(self):
        static_image = self.factory('fixtures/image004.png', 'image', '9006')
        self.assertEqual(static_image.get_versioned_file_path(), 'images/fixtures/image004-9006.png')


class FileRenameTest(unittest.TestCase):

    def test_rename_file_and_revert_back(self):
        source = 'fixtures/styles.css'
        destination = 'fixtures/newstyles.css.with-different-extensions.temp.gz'
        self.assertTrue(os.path.exists(source))
        self.assertFalse(os.path.exists(destination))

        os.rename(source, destination)
        self.assertFalse(os.path.exists(source))
        self.assertTrue(os.path.exists(destination))

        os.rename(destination, source)
        self.assertTrue(os.path.exists(source))
        self.assertFalse(os.path.exists(destination))


class ConfigParserTest(unittest.TestCase):

    def test_config_parser_returns_credential_from_file(self):
        expected_cred = {'id': 'testing_access_key', 'secret': 'testing_secret_key'}
        self.assertEqual(S3Util.get_aws_credentials('fixtures/boto.cfg', 'testing'), expected_cred)


@moto.mock_s3
class MotoBucketBaseTestClass(unittest.TestCase):

    def setUp(self):
        connection = boto.connect_s3('key', 'secret')
        self.bucket = connection.create_bucket('mybucket567')


class ConnectToS3BucketTest(MotoBucketBaseTestClass):

    def test_connect_to_valid_s3_bucket_using_correct_credential_should_return_correct_bucket_object(self):
        profile = {'id': 'key', 'secret': 'secret'}
        bucket_reconnect = S3Util.connect_to_bucket(profile, 'mybucket567')
        self.assertIsInstance(bucket_reconnect, boto.s3.bucket.Bucket)
        self.assertEqual(bucket_reconnect.name, 'mybucket567')


class S3FileCheckerTest(MotoBucketBaseTestClass):

    def test_file_checker_returns_true_if_filename_exists_in_bucket(self):
        k = boto.s3.key.Key(self.bucket)
        k.key = 'exists.txt'
        k.set_contents_from_string('teststring')

        result = exists('exists.txt', self.bucket)
        self.assertTrue(result)

    def test_file_checker_returns_false_if_filename_doesnt_exist_in_bucket(self):
        result = exists('doesnt_exist.txt', self.bucket)
        self.assertFalse(result)


class UploadFileToS3Test(MotoBucketBaseTestClass):

    def test_upload_to_s3_should_pass(self):
        upload('fixtures/styles_gzipped.css', 'styles.css', 'css', self.bucket)

        result = exists('styles.css', self.bucket)
        self.assertTrue(result)

    def test_upload_css_to_s3_should_append_correct_headers(self):
        upload('fixtures/styles_gzipped.css', 'styles.css', 'css', self.bucket)

        k = self.bucket.get_key('styles.css')
        self.assertEqual(k.content_encoding, 'gzip')
        self.assertIn('text/css', k.content_type)
        self.assertEqual(k.cache_control, 'max-age=31536000')

    def test_upload_js_to_s3_should_append_correct_headers(self):
        upload('fixtures/cells_gzipped.js', 'cells.js', 'js', self.bucket)

        k = self.bucket.get_key('cells.js')
        self.assertEqual(k.content_encoding, 'gzip')
        self.assertIn('application/javascript', k.content_type)
        self.assertEqual(k.cache_control, 'max-age=31536000')

    def test_upload_image_to_s3_should_append_correct_headers(self):
        upload('fixtures/logo.png', 'logo.png', 'image', self.bucket)

        k = self.bucket.get_key('logo.png')
        self.assertEqual(k.cache_control, "max-age=31536000, no transform, public")

    @unittest.skip('acl not implemented in moto yet, exception if executed')
    def test_upload_to_s3_should_set_public_read_acl(self):
        upload('fixtures/cells_gzipped.js', 'cells.js', 'js', self.bucket)

        k = self.bucket.get_key('cells.js')
        policy = k.get_acl()
        self.assertEqual(policy.acl.grants[1].uri, 'http://acs.amazonaws.com/groups/global/AllUsers')
        self.assertEqual(policy.acl.grants[1].permission, 'READ')


class StaticFileWrapperMethodsTest(unittest.TestCase):

    def factory(self, path='mypath', type_='css'):
        connections = {'css_bucket': '', 'js_bucket': '', 'image_bucket': ''}
        return StaticFile('', path, type_, '1234567890', connections)

    def execute(self, the_object, function):
        out = io.StringIO()

        with redirect_stdout(out):
            getattr(the_object, function)()
        return out.getvalue()

    @mock.patch('mydeploy.Minifier')
    def test_minify_css_should_print_information(self, mock_Minifier):
        css_file = self.factory('css1.css', 'css')
        output = self.execute(css_file, 'minify')
        self.assertIn('minified css/css1.css -> css/css1.css.temp', output)

    @mock.patch('mydeploy.Minifier')
    def test_minify_js_should_print_information(self, mock_Minifier):
        js_file = self.factory('js1.js', 'js')
        output = self.execute(js_file, 'minify')
        self.assertIn('minified scripts/js1.js -> scripts/js1.js.temp', output)

    @mock.patch('mydeploy.Minifier')
    def test_gzip_should_print_information(self, mock_Minifier):
        css_file = self.factory('css1.css', 'css')
        css_file.minified_path = 'css1.css.temp'

        output = self.execute(css_file, 'gzip')
        self.assertIn('gzipped css1.css.temp -> css1.css.temp.gz', output)

    @mock.patch('os.rename')
    def test_rename_should_print_information(self, mock_os):
        js_file = self.factory('js1.js', 'js')
        js_file.gzipped_path = 'scripts/js1.js.temp.gz'

        output = self.execute(js_file, 'rename')
        self.assertIn('renamed scripts/js1.js.temp.gz -> scripts/js1-1234567890.js', output)

    @mock.patch('mydeploy.S3Util')
    def test_upload_should_print_information(self, mock_S3Util):
        css_file = self.factory('css1.css', 'css')
        css_file.associated_bucket = boto.s3.bucket.Bucket(name='css_bucket')

        output = self.execute(css_file, 'upload')
        self.assertIn('uploaded css/css1-1234567890.css -> '
                      'http://css_bucket.s3.amazonaws.com/css/css1-1234567890.css', output)


class DeploymentMainTest(unittest.TestCase):

    def setUp(self):
        mydeploy.AWS_CONFIG_PATH = 'fixtures/end_to_end/boto2.cfg'
        mydeploy.AWS_PROFILE = 'dev'
        mydeploy.CSS_BUCKET = 'myrandombucket-0001'
        mydeploy.IMAGE_BUCKET = 'myrandombucket-0003'
        mydeploy.JAVA_PATH = ''
        mydeploy.JS_BUCKET = 'myrandombucket-0002'
        mydeploy.MINIFIER_PATH = ''
        mydeploy.PREFIX_PATH = 'fixtures/end_to_end/'
        mydeploy.XML_PATH = 'fixtures/end_to_end/config/mydeploy.xml'

    def tearDown(self):

        paths_to_cleanup = [
            'fixtures/end_to_end/css/common.css.temp',
            'fixtures/end_to_end/css/common.css.temp.gz',
            'fixtures/end_to_end/css/common-' + VALID_VERSION + '.css',
            'fixtures/end_to_end/scripts/apply.js.temp',
            'fixtures/end_to_end/scripts/apply.js.temp.gz',
            'fixtures/end_to_end/scripts/apply-' + VALID_VERSION + '.js',
            'fixtures/end_to_end/scripts/notprocessed.js.temp',
            'fixtures/end_to_end/scripts/notprocessed.js.temp.gz',
            'fixtures/end_to_end/scripts/notprocessed-mispattern.js',
            ]

        for path in paths_to_cleanup:
            try:
                os.remove(path)
            except:
                pass

        try:
            os.rename('fixtures/end_to_end/images/image001-' + VALID_VERSION + '.png',
                      'fixtures/end_to_end/images/image001.png')
        except:
            pass

    def initialise_buckets(self):

        connection = boto.connect_s3('key', 'secret')
        self.bucket_css = connection.create_bucket(mydeploy.CSS_BUCKET)
        self.bucket_js = connection.create_bucket(mydeploy.JS_BUCKET)
        self.bucket_image = connection.create_bucket(mydeploy.IMAGE_BUCKET)

    def execute(self, skip_existing=None):
        out = io.StringIO()

        with redirect_stdout(out):
            if skip_existing is not None:
                mydeploy.deploy_main(skip_existing)
            else:
                mydeploy.deploy_main()

        return out.getvalue()

    @moto.mock_s3
    def test_end_to_end_deploy_should_process_and_upload_files_in_xml(self):

        self.initialise_buckets()

        self.execute()

        self.assertTrue(exists('css/common-' + VALID_VERSION + '.css', self.bucket_css))
        self.assertTrue(exists('scripts/apply-' + VALID_VERSION + '.js', self.bucket_js))
        self.assertTrue(exists('images/image001-' + VALID_VERSION + '.png', self.bucket_image))

    @moto.mock_s3
    def test_end_to_end_should_skip_existing_file_in_s3_in_default_mode(self):

        self.initialise_buckets()

        upload('fixtures/end_to_end/css/common.css', 'css/common-' + VALID_VERSION + '.css', 'css', self.bucket_css)
        self.assertTrue(exists('css/common-' + VALID_VERSION + '.css', self.bucket_css))

        upload('fixtures/end_to_end/images/image001.png', 'images/image001-' + VALID_VERSION + '.png', 'image', self.bucket_image)
        self.assertTrue(exists('images/image001-' + VALID_VERSION + '.png', self.bucket_image))

        self.execute()

        self.assertTrue(exists('scripts/apply-' + VALID_VERSION + '.js', self.bucket_js))

        self.assertFalse(os.path.exists('fixtures/end_to_end/css/common-' + VALID_VERSION + '.css'))
        self.assertFalse(os.path.exists('fixtures/end_to_end/images/image001-' + VALID_VERSION + '.png'))

    @moto.mock_s3
    def test_end_to_end_should_force_process_all_files_if_explicitly_called(self):

        self.initialise_buckets()

        upload('fixtures/end_to_end/css/common.css', 'css/common-' + VALID_VERSION + '.css', 'css', self.bucket_css)
        self.assertTrue(exists('css/common-' + VALID_VERSION + '.css', self.bucket_css))

        output = self.execute(skip_existing=False)

        self.assertIn('uploaded css/common-' + VALID_VERSION + '.css', output)

        self.assertTrue(exists('css/common-' + VALID_VERSION + '.css', self.bucket_css))
        self.assertTrue(exists('scripts/apply-' + VALID_VERSION + '.js', self.bucket_js))
        self.assertTrue(exists('images/image001-' + VALID_VERSION + '.png', self.bucket_image))

    @moto.mock_s3
    def test_end_to_end_should_not_process_files_with_version_length_does_not_equal_twelve_digits(self):

        self.initialise_buckets()

        output = self.execute()

        expected_string_outputs = [
            'Skipping processing of fixtures/end_to_end/scripts/notprocessed-mispattern.js, '
            'version does not equal 12 digits']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertFalse(exists('scripts/notprocessed-mispattern.js', self.bucket_js))

        self.assertFalse(os.path.exists('fixtures/end_to_end/scripts/notprocessed-mispattern.js'))
