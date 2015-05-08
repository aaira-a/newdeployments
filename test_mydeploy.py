import unittest
from unittest import mock

from mydeploy import (
    compile_js,
    compress_css,
    gzip_file,
    connect_to_bucket,
    file_exists_in_s3_bucket,
    create_list_from_xml,
    get_aws_credentials,
    StaticFile,
    upload_gzipped_file_to_bucket,
    )

import mydeploy

import boto
from contextlib import redirect_stdout
import io
import moto
import os.path


class XMLTest(unittest.TestCase):

    def test_open_xml_fixture_should_return_packed_lists(self):
        expected_list = [
            ['common.css', 'css', '1423532041'],
            ['path/to/component.css', 'css', '1423532040'],
            ['validation.js', 'js', '1408592767'],
            ['path/to/default.js', 'js', '1408592767'], ]
        self.assertEqual(
            create_list_from_xml('fixtures/fileVersion.xml'),
            expected_list)


class YUICompressorTest(unittest.TestCase):

    @mock.patch('subprocess.call')
    def test_compress_css_should_call_yuicompressor_with_correct_syntax(self, mock_subprocess):
        compress_css('input', 'output')
        mock_subprocess.assert_called_with(
            ['java', '-jar', 'yuicompressor-2.4.8.jar', 'input', '-o', 'output'])

    @mock.patch('subprocess.call')
    def test_compress_css_should_return_zero_if_compression_is_successful(self, mock_subprocess):
        mock_subprocess.return_value = 0
        return_code = compress_css('fixtures/styles.css', 'output')
        self.assertEqual(return_code, 0)

    @mock.patch('subprocess.call')
    def test_compress_css_should_return_1_if_compression_is_unsuccessful(self, mock_subprocess):
        mock_subprocess.return_value = 1
        return_code = compress_css('fixtures/notfound.css', 'output')
        self.assertEqual(return_code, 1)


class ClosureCompilerTest(unittest.TestCase):

    @mock.patch('subprocess.call')
    def test_compile_js_should_call_compiler_with_correct_syntax(self, mock_subprocess):
        compile_js('input', 'output')
        mock_subprocess.assert_called_with(
            ['java', '-jar', 'compiler.jar', '--js', 'input', '--js_output_file', 'output'])

    @mock.patch('subprocess.call')
    def test_compile_js_should_return_zero_if_compilation_is_successful(self, mock_subprocess):
        mock_subprocess.return_value = 0
        return_code = compile_js('fixtures/cells.js', 'output')
        self.assertEqual(return_code, 0)

    @mock.patch('subprocess.call')
    def test_compile_js_should_return_1_if_compilation_is_unsuccessful(self, mock_subprocess):
        mock_subprocess.return_value = 1
        return_code = compile_js('fixtures/notfound.js', 'output')
        self.assertEqual(return_code, 1)


class GZipTest(unittest.TestCase):

    def test_gzip_file_should_produce_smaller_file_than_original(self):
        input_path = 'fixtures/styles.css'
        output_path = 'fixtures/styles.css.suffix'

        self.assertFalse(os.path.exists(output_path))
        gzip_file(input_path, output_path)
        self.assertTrue(os.path.exists(output_path))

        input_size = os.path.getsize(input_path)
        output_size = os.path.getsize(output_path)

        self.assertLess(output_size, input_size)

        os.remove(output_path)
        self.assertFalse(os.path.exists(output_path))


class VersionedPathTest(unittest.TestCase):

    def test_get_versioned_path_from_css_file(self):
        self.static_css = StaticFile('', 'fixtures/styles.css', 'css', '9001', '', '')
        self.assertEqual(self.static_css.get_versioned_file_path(), 'fixtures/styles-9001.css')

    def test_get_versioned_path_from_js_file(self):
        self.static_js = StaticFile('', 'fixtures/cells.js', 'js', '9002', '', '')
        self.assertEqual(self.static_js.get_versioned_file_path(), 'fixtures/cells-9002.js')


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
        self.assertEqual(get_aws_credentials('fixtures/boto.cfg', 'testing'), expected_cred)


class ConnectToS3BucketTest(unittest.TestCase):

    @moto.mock_s3
    def test_connect_to_valid_s3_bucket_using_correct_credential_should_return_correct_bucket_object(self):
        connection = boto.connect_s3('key', 'secret')
        connection.create_bucket('myrandombucket-0001')

        profile = {'id': 'key', 'secret': 'secret'}
        bucket_reconnect = connect_to_bucket(profile, 'myrandombucket-0001')
        self.assertIsInstance(bucket_reconnect, boto.s3.bucket.Bucket)
        self.assertEqual(bucket_reconnect.name, 'myrandombucket-0001')


class S3FileCheckerTest(unittest.TestCase):

    @moto.mock_s3
    def test_file_checker_returns_true_if_filename_exists_in_bucket(self):
        connection = boto.connect_s3('key', 'secret')
        bucket = connection.create_bucket('mybucket567')

        k = boto.s3.key.Key(bucket)
        k.key = 'exists.txt'
        k.set_contents_from_string('teststring')

        result = file_exists_in_s3_bucket('exists.txt', bucket)
        self.assertTrue(result)

    @moto.mock_s3
    def test_file_checker_returns_false_if_filename_doesnt_exist_in_bucket(self):
        connection = boto.connect_s3('key', 'secret')
        bucket = connection.create_bucket('mybucket567')

        result = file_exists_in_s3_bucket('doesnt_exist.txt', bucket)
        self.assertFalse(result)


class UploadFileToS3Test(unittest.TestCase):

    @moto.mock_s3
    def test_upload_to_s3_should_pass(self):
        connection = boto.connect_s3('key', 'secret')
        bucket = connection.create_bucket('mybucket567')

        upload_gzipped_file_to_bucket('fixtures/styles_gzipped.css', 'styles.css', 'css', bucket)

        result = file_exists_in_s3_bucket('styles.css', bucket)
        self.assertTrue(result)

    @moto.mock_s3
    def test_upload_css_to_s3_should_append_correct_headers(self):
        connection = boto.connect_s3('key', 'secret')
        bucket = connection.create_bucket('mybucket567')

        upload_gzipped_file_to_bucket('fixtures/styles_gzipped.css', 'styles.css', 'css', bucket)

        k = bucket.get_key('styles.css')
        self.assertEqual(k.content_encoding, 'gzip')
        self.assertIn('text/css', k.content_type)
        self.assertEqual(k.cache_control, 'max-age=31536000')

    @moto.mock_s3
    def test_upload_js_to_s3_should_append_correct_headers(self):
        connection = boto.connect_s3('key', 'secret')
        bucket = connection.create_bucket('mybucket567')

        upload_gzipped_file_to_bucket('fixtures/cells_gzipped.js', 'cells.js', 'js', bucket)

        k = bucket.get_key('cells.js')
        self.assertEqual(k.content_encoding, 'gzip')
        self.assertIn('application/javascript', k.content_type)
        self.assertEqual(k.cache_control, 'max-age=31536000')

    @unittest.skip('acl not implemented in moto yet, exception if executed')
    def test_upload_to_s3_should_set_public_read_acl(self):
        connection = boto.connect_s3('key', 'secret')
        bucket = connection.create_bucket('mybucket567')

        upload_gzipped_file_to_bucket('fixtures/cells_gzipped.js', 'cells.js', 'js', bucket)

        k = bucket.get_key('cells.js')
        policy = k.get_acl()
        self.assertEqual(policy.acl.grants[1].uri, 'http://acs.amazonaws.com/groups/global/AllUsers')
        self.assertEqual(policy.acl.grants[1].permission, 'READ')


class DeploymentMainTest(unittest.TestCase):

    def setUp(self):
        mydeploy.AWS_CONFIG_PATH = 'fixtures/end_to_end/boto2.cfg'
        mydeploy.AWS_PROFILE = 'dev'
        mydeploy.PREFIX_PATH = 'fixtures/end_to_end/'
        mydeploy.CSS_BUCKET = 'myrandombucket-0001'
        mydeploy.JAVA_PATH = ''
        mydeploy.JS_BUCKET = 'myrandombucket-0002'
        mydeploy.MINIFIER_PATH = ''
        mydeploy.XML_PATH = 'fixtures/end_to_end/config/fileVersion2.xml'

    @moto.mock_s3
    def test_end_to_end_deploy_should_pass(self):

        connection = boto.connect_s3('key', 'secret')
        bucket_css = connection.create_bucket(mydeploy.CSS_BUCKET)
        bucket_js = connection.create_bucket(mydeploy.JS_BUCKET)

        out = io.StringIO()

        with redirect_stdout(out):
            mydeploy.deploy_main()
        output = out.getvalue()

        expected_string_outputs = [
            'minified fixtures/end_to_end/css/common.css',
            'gzipped fixtures/end_to_end/css/common.css.temp',
            'renamed fixtures/end_to_end/css/common.css.temp.gz into fixtures/end_to_end/css/common-1423532041.css',
            'uploaded css/common-1423532041.css into myrandombucket-0001',
            '',
            'minified fixtures/end_to_end/js/apply.js',
            'gzipped fixtures/end_to_end/js/apply.js.temp',
            'renamed fixtures/end_to_end/js/apply.js.temp.gz into fixtures/end_to_end/js/apply-1408592767.js',
            'uploaded js/apply-1408592767.js into myrandombucket-0002']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertTrue(file_exists_in_s3_bucket('css/common-1423532041.css', bucket_css))
        self.assertTrue(file_exists_in_s3_bucket('js/apply-1408592767.js', bucket_js))

        os.remove('fixtures/end_to_end/css/common-1423532041.css')
        os.remove('fixtures/end_to_end/js/apply-1408592767.js')

        os.remove('fixtures/end_to_end/css/common.css.temp')
        os.remove('fixtures/end_to_end/js/apply.js.temp')

    @moto.mock_s3
    def test_end_to_end_should_skip_existing_file_in_default_mode(self):

        connection = boto.connect_s3('key', 'secret')
        bucket_css = connection.create_bucket(mydeploy.CSS_BUCKET)
        bucket_js = connection.create_bucket(mydeploy.JS_BUCKET)

        upload_gzipped_file_to_bucket('fixtures/end_to_end/css/common.css', 'css/common-1423532041.css', 'css', bucket_css)
        self.assertTrue(file_exists_in_s3_bucket('css/common-1423532041.css', bucket_css))

        out = io.StringIO()

        with redirect_stdout(out):
            mydeploy.deploy_main()
        output = out.getvalue()

        expected_string_outputs = [
            'minified fixtures/end_to_end/js/apply.js',
            'gzipped fixtures/end_to_end/js/apply.js.temp',
            'renamed fixtures/end_to_end/js/apply.js.temp.gz into fixtures/end_to_end/js/apply-1408592767.js',
            'uploaded js/apply-1408592767.js into myrandombucket-0002']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertTrue(file_exists_in_s3_bucket('js/apply-1408592767.js', bucket_js))

        self.assertFalse(os.path.exists('fixtures/end_to_end/css/common-1423532041.css'))

        os.remove('fixtures/end_to_end/js/apply-1408592767.js')
        os.remove('fixtures/end_to_end/js/apply.js.temp')

    @moto.mock_s3
    def test_end_to_end_should_force_process_all_files_if_explicitly_called(self):

        connection = boto.connect_s3('key', 'secret')
        bucket_css = connection.create_bucket(mydeploy.CSS_BUCKET)
        bucket_js = connection.create_bucket(mydeploy.JS_BUCKET)

        upload_gzipped_file_to_bucket('fixtures/end_to_end/css/common.css', 'css/common-1423532041.css', 'css', bucket_css)
        self.assertTrue(file_exists_in_s3_bucket('css/common-1423532041.css', bucket_css))

        out = io.StringIO()

        with redirect_stdout(out):
            mydeploy.deploy_main(skip_existing=False)
        output = out.getvalue()

        expected_string_outputs = [
            'minified fixtures/end_to_end/css/common.css',
            'gzipped fixtures/end_to_end/css/common.css.temp',
            'renamed fixtures/end_to_end/css/common.css.temp.gz into fixtures/end_to_end/css/common-1423532041.css',
            'uploaded css/common-1423532041.css into myrandombucket-0001',
            '',
            'minified fixtures/end_to_end/js/apply.js',
            'gzipped fixtures/end_to_end/js/apply.js.temp',
            'renamed fixtures/end_to_end/js/apply.js.temp.gz into fixtures/end_to_end/js/apply-1408592767.js',
            'uploaded js/apply-1408592767.js into myrandombucket-0002']

        for line in expected_string_outputs:
            self.assertIn(line, output)

        self.assertTrue(file_exists_in_s3_bucket('css/common-1423532041.css', bucket_css))
        self.assertTrue(file_exists_in_s3_bucket('js/apply-1408592767.js', bucket_js))

        os.remove('fixtures/end_to_end/css/common-1423532041.css')
        os.remove('fixtures/end_to_end/js/apply-1408592767.js')

        os.remove('fixtures/end_to_end/css/common.css.temp')
        os.remove('fixtures/end_to_end/js/apply.js.temp')
