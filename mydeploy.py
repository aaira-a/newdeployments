
import boto
import configparser
import gzip
import os
import re
import subprocess
import xml.etree.ElementTree as ET

# all paths are relative to jenkins job's workspace
AWS_CONFIG_PATH = ''    # path to config file (ini format) containing aws credentials
AWS_PROFILE = ''        # name of aws profile from the config file to be used
PREFIX_PATH = ''          # path of the repo www folder
CSS_BUCKET = ''         # name of the css bucket
MINIFIER_PATH = ''      # path of the folder containing the minifiers binaries (closure compiler & yuicompressor)
JAVA_PATH = ''          # path of the folder containing java binary, may default to empty if already defined in system path
JS_BUCKET = ''          # name of the js bucket
XML_PATH = ''           # path of the xml file containing latest file versions


def deploy_main():

    cred = get_aws_credentials(AWS_CONFIG_PATH, AWS_PROFILE)

    css_bucket = connect_to_bucket(cred, CSS_BUCKET)
    js_bucket = connect_to_bucket(cred, JS_BUCKET)

    files = create_list_from_xml(XML_PATH)

    for file_ in files:

        file_path = file_[0]
        file_type = file_[1]
        file_version = file_[2]

        file_object = StaticFile(PREFIX_PATH, file_path, file_type, file_version)

        print('\n')
        file_object.minify_file()
        print('minified ' + file_object.path_in_filesystem)

        file_object.gzip_file()
        print('gzipped ' + file_object.minified_path)

        versioned_file_path = file_object.get_versioned_file_name()
        rename_file(file_object.gzipped_path, versioned_file_path)
        print('renamed ' + file_object.gzipped_path + ' into ' + versioned_file_path)

        versioned_file_path_without_base = file_object.get_versioned_file_name(with_prefix=False)

        if file_type == 'css':
            upload_gzipped_file_to_bucket(versioned_file_path, versioned_file_path_without_base, file_type, css_bucket)
            print('uploaded ' + versioned_file_path_without_base + ' into ' + CSS_BUCKET)

        elif file_type == 'js':
            upload_gzipped_file_to_bucket(versioned_file_path, versioned_file_path_without_base, file_type, js_bucket)
            print('uploaded ' + versioned_file_path_without_base + ' into ' + JS_BUCKET)


class StaticFile(object):

    def __init__(self, prefix_path, file_path, file_type, file_version):
        self.prefix_path = prefix_path
        self.file_path = file_path
        self.file_type = file_type
        self.file_version = file_version
        self.path_in_filesystem = prefix_path + file_path

    def minify_file(self):
        if self.file_type == 'css':
            self._compress_css()

        elif self.file_type == 'js':
            self._compile_js()

    def _compress_css(self):
        self.minified_path = self.path_in_filesystem + '.temp'
        return subprocess.call([JAVA_PATH + 'java', '-jar', MINIFIER_PATH + 'yuicompressor-2.4.8.jar', self.path_in_filesystem, '-o', self.path_in_filesystem + '.temp'])

    def _compile_js(self):
        self.minified_path = self.path_in_filesystem + '.temp'
        return subprocess.call([JAVA_PATH + 'java', '-jar', MINIFIER_PATH + 'compiler.jar', '--js', self.path_in_filesystem, '--js_output_file', self.path_in_filesystem + '.temp'])

    def gzip_file(self):
        with open(self.minified_path, 'rb') as input_file:
            with gzip.open(self.minified_path + '.gz', 'wb') as output_file:
                output_file.writelines(input_file)
        self.gzipped_path = self.minified_path + '.gz'

    def get_versioned_file_name(self, with_prefix=True):
        if with_prefix:
            input_path = self.path_in_filesystem
        else:
            input_path = self.file_path

        base_path = re.sub(r'\.(css|js)', '', input_path)
        return (base_path + '-' + self.file_version + '.' + self.file_type)


def create_list_from_xml(path):
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


def rename_file(source, destination):
    os.rename(source, destination)


def get_aws_credentials(path=None, profile=None):
    if profile is None or path is None:
        return None

    else:
        config = configparser.ConfigParser()
        config.read(path)
        p = config[profile]
        return {'id': p['aws_access_key_id'], 'secret': p['aws_secret_access_key']}


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

    k.set_contents_from_filename(source_path, headers=headers, policy='public-read')


if __name__ == '__main__':
    deploy_main()
