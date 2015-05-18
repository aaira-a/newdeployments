import unittest

from mycleanup import (
    is_matching_versioned_pattern,
    )


class VersionedPatternChecker(unittest.TestCase):

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
