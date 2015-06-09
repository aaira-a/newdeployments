
import boto
import configparser
import gzip
import os
import re
import subprocess
import xml.etree.ElementTree as ET

from environment_config import (
    AWS_CONFIG_PATH,
    AWS_PROFILE,
    CSS_BUCKET,
    IMAGE_BUCKET,
    JS_BUCKET,
    PREFIX_PATH,
    XML_PATH,
    JAVA_PATH,
    MINIFIER_PATH,
    )


def deploy_main(skip_existing=True):

    connection_pools = S3Util.create_connection_pools(AWS_CONFIG_PATH, AWS_PROFILE,
                                                      CSS_BUCKET, JS_BUCKET, IMAGE_BUCKET)

    file_objects = get_file_objects(connection_pools, XML_PATH)

    if skip_existing:
        file_objects = [item for item in file_objects if item.exists_in_bucket() == False]

    for item in file_objects:
        if (len(item.version) == 10 and item.version.isdigit()):
            item.process()
        else:
            print('Skipping processing of ' + item.versioned_path_in_filesystem +
                  ', version does not equal 10 digits')


def get_file_objects(connection_pools, xml_path):
    files = XMLParser.create_matrix_from_xml(xml_path)
    file_objects = objectify_entries(files, connection_pools)
    return file_objects


def objectify_entries(entries_matrix, connection_pools):

    items = []

    for entry in entries_matrix:
        file_path = entry[0]
        file_type = entry[1]
        file_version = entry[2]

        f = StaticFile(PREFIX_PATH, file_path, file_type, file_version, connection_pools)
        items.append(f)

    return items


class StaticFile(object):

    def __init__(self, prefix_path, file_path, type_, version, connection_pools):

        if type_ == 'css':
            self.file_path = 'css/' + file_path

        elif type_ == 'js':
            self.file_path = 'scripts/' + file_path

        elif type_ == 'image':
            self.file_path = 'images/' + file_path

        self.type_ = type_
        self.version = version
        self.path_in_filesystem = prefix_path + self.file_path
        self.versioned_path_in_bucket = self.get_versioned_file_path(with_prefix=False)
        self.versioned_path_in_filesystem = self.get_versioned_file_path(with_prefix=True)

        if type_ == 'css':
            self.associated_bucket = connection_pools['css_bucket']

        elif type_ == 'js':
            self.associated_bucket = connection_pools['js_bucket']

        elif type_ == 'image':
            self.associated_bucket = connection_pools['image_bucket']
            self.gzipped_path = self.path_in_filesystem

    def process(self):
        print('\n')

        if self.type_ == 'css' or self.type_ == 'js':
            self.minify()
            self.gzip()

        self.rename()
        self.upload()

    def minify(self):
        input_ = self.path_in_filesystem
        self.minified_path = input_ + '.temp'

        if self.type_ == 'css':
            Minifier.compress_css(input_, self.minified_path)

        elif self.type_ == 'js':
            Minifier.compile_js(input_, self.minified_path)

        print('minified ' + self.path_in_filesystem + ' -> ' + self.minified_path)

    def gzip(self):
        input_ = self.minified_path
        self.gzipped_path = input_ + '.gz'

        Minifier.gzip_file(input_, self.gzipped_path)
        print('gzipped ' + self.minified_path + ' -> ' + self.gzipped_path)

    def get_versioned_file_path(self, with_prefix=True):
        if with_prefix:
            input_path = self.path_in_filesystem
        else:
            input_path = self.file_path

        split = re.search(r'(.*)\.(css|js|gif|jpg|jpeg|png)$', input_path).groups()
        return (split[0] + '-' + self.version + '.' + split[1])

    def rename(self):
        os.rename(self.gzipped_path, self.versioned_path_in_filesystem)
        print('renamed ' + self.gzipped_path + ' -> ' + self.versioned_path_in_filesystem)

    def upload(self):
        S3Util.upload_gzipped_file_to_bucket(self.versioned_path_in_filesystem,
                                             self.versioned_path_in_bucket,
                                             self.type_,
                                             self.associated_bucket)

        print('uploaded ' + self.versioned_path_in_bucket + ' -> ' +
              'http://' + self.associated_bucket.name + '.s3.amazonaws.com/' + self.versioned_path_in_bucket)

    def exists_in_bucket(self):
        return S3Util.file_exists_in_s3_bucket(self.versioned_path_in_bucket,
                                               self.associated_bucket)


class S3Util(object):

    def create_connection_pools(config_path, profile,
                                css_bucket_name, js_bucket_name, image_bucket_name):

        cred = S3Util.get_aws_credentials(config_path, profile)

        css_bucket = S3Util.connect_to_bucket(cred, css_bucket_name)
        js_bucket = S3Util.connect_to_bucket(cred, js_bucket_name)
        image_bucket = S3Util.connect_to_bucket(cred, image_bucket_name)

        return {'css_bucket': css_bucket,
                'js_bucket': js_bucket,
                'image_bucket': image_bucket}

    def get_aws_credentials(path, profile):
        config = configparser.ConfigParser()
        config.read(path)
        p = config[profile]
        return {'id': p['aws_access_key_id'],
                'secret': p['aws_secret_access_key']}

    def connect_to_bucket(profile, bucket):
        connection = boto.connect_s3(profile['id'], profile['secret'])
        return connection.get_bucket(bucket)

    def file_exists_in_s3_bucket(path, bucket):
        k = boto.s3.key.Key(bucket)
        k.key = path
        return k.exists()

    def upload_gzipped_file_to_bucket(source_path, uploaded_as_path, file_type, bucket):
        k = boto.s3.key.Key(bucket)
        k.key = uploaded_as_path

        if file_type == 'css':
            headers = {'Content-Encoding': 'gzip',
                       'Content-Type': 'text/css',
                       'Cache-Control': 'max-age=31536000'}

        elif file_type == 'js':
            headers = {'Content-Encoding': 'gzip',
                       'Content-Type': 'application/javascript',
                       'Cache-Control': 'max-age=31536000'}

        elif file_type == 'image':
            headers = {'Cache-Control': str.encode('max-age=31536000, no transform, public')}

        k.set_contents_from_filename(source_path, headers=headers, policy='public-read')


class XMLParser(object):

    def create_matrix_from_xml(path):
        tree = ET.parse(path)
        root = tree.getroot()
        packed = []

        for file_element in root:
            file_name = file_element.attrib['url']
            file_type = file_element[0].text
            file_version = file_element[1].text

            sublist = [file_name, file_type, file_version]
            packed.append(sublist)

        return packed


class Minifier(object):

    def compress_css(input_, output):
        return subprocess.call([JAVA_PATH + 'java', '-jar',
                                MINIFIER_PATH + 'yuicompressor-2.4.8.jar',
                                input_,
                                '-o', output])

    def compile_js(input_, output):
        return subprocess.call([JAVA_PATH + 'java', '-jar',
                                MINIFIER_PATH + 'compiler.jar',
                                '--js', input_,
                                '--js_output_file', output])

    def gzip_file(input_, output):
        with open(input_, 'rb') as input_file:
            with gzip.open(output, 'wb') as output_file:
                output_file.writelines(input_file)


if __name__ == '__main__':
    deploy_main()
