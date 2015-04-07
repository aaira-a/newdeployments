import unittest
from unittest import mock

from mydeploy import (
    compile_js,
    compress_css,
    create_list_from_xml,
    gzip_file,
    )

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
        compress_css('path')
        mock_subprocess.assert_called_with(
            ['java', '-jar', 'yuicompressor-2.4.8.jar', 'path', '-o', 'path' + '.temp'])

    # @mock.patch('subprocess.call')
    def test_compress_css_should_return_zero_if_compression_is_successful(self):
        # mock_subprocess.return_value = 0
        return_code = compress_css('fixtures/styles.css')
        self.assertEqual(return_code, 0)

    # @mock.patch('subprocess.call')
    def test_compress_css_should_return_1_if_compression_is_unsuccessful(self):
        # mock_subprocess.return_value = 1
        return_code = compress_css('fixtures/notfound.css')
        self.assertEqual(return_code, 1)


class ClosureCompilerTest(unittest.TestCase):

    @mock.patch('subprocess.call')
    def test_compile_js_should_call_compiler_with_correct_syntax(self, mock_subprocess):
        compile_js('path')
        mock_subprocess.assert_called_with(
            ['java', '-jar', 'compiler.jar', '--js', 'path', '--js_output_file', 'path' + '.temp'])

    # @mock.patch('subprocess.call')
    def test_compile_js_should_return_zero_if_compilation_is_successful(self):
        # mock_subprocess.return_value = 0
        return_code = compile_js('fixtures/cells.js')
        self.assertEqual(return_code, 0)

    # @mock.patch('subprocess.call')
    def test_compile_js_should_return_1_if_compilation_is_unsuccessful(self):
        # mock_subprocess.return_value = 1
        return_code = compile_js('fixtures/notfound.js')
        self.assertEqual(return_code, 1)


class GZipTest(unittest.TestCase):

    def test_gzip_file_should_produce_smaller_file_than_original(self):
        input_path = 'fixtures/styles.css'
        output_path = 'fixtures/styles.css.gz'

        self.assertFalse(os.path.exists(output_path))
        gzip_file(input_path)
        self.assertTrue(os.path.exists(output_path))

        input_size = os.path.getsize(input_path)
        output_size = os.path.getsize(output_path)

        self.assertLess(output_size, input_size)

        # os.remove(output_path)
        # self.assertFalse(os.path.exists(output_path))
