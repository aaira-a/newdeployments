
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
PREFIX_PATH = ''        # path of the repo www folder
CSS_BUCKET = ''         # name of the css bucket
MINIFIER_PATH = ''      # path of the folder containing the minifiers binaries (closure compiler & yuicompressor)
JAVA_PATH = ''          # path of the folder containing java binary, may default to empty if already defined in system path
JS_BUCKET = ''          # name of the js bucket
XML_PATH = ''           # path of the xml file containing latest file versions


def deploy_main(skip_existing=True):

    cred = get_aws_credentials(AWS_CONFIG_PATH, AWS_PROFILE)

    css_bucket = connect_to_bucket(cred, CSS_BUCKET)
    js_bucket = connect_to_bucket(cred, JS_BUCKET)

    files = create_list_from_xml(XML_PATH)
    file_objects = objectify_entries(files, css_bucket, js_bucket)

    if skip_existing:
        file_objects = [item for item in file_objects if item.exists_in_bucket() == False]

    process_files(file_objects)


def process_files(file_objects):
    for f in file_objects:

        print('\n')
        f.minify()
        print('minified ' + f.path_in_filesystem)

        f.gzip()
        print('gzipped ' + f.minified_path)

        rename_file(f.gzipped_path, f.versioned_name_in_filesystem)
        print('renamed ' + f.gzipped_path + ' into ' + f.versioned_name_in_filesystem)

        f.upload()
        print('uploaded ' + f.versioned_name_in_bucket + ' into ' + f.associated_bucket.name)


def objectify_entries(entries_matrix, css_bucket, js_bucket):

    items = []

    for entry in entries_matrix:
        file_path = entry[0]
        file_type = entry[1]
        file_version = entry[2]

        f = StaticFile(PREFIX_PATH, file_path,
                       file_type, file_version,
                       css_bucket, js_bucket)
        items.append(f)

    return items


class StaticFile(object):

    def __init__(self, prefix_path, file_path, type_, version, css_bucket, js_bucket):
        self.file_path = file_path
        self.type_ = type_
        self.version = version
        self.path_in_filesystem = prefix_path + file_path
        self.versioned_name_in_bucket = self.get_versioned_file_name(with_prefix=False)
        self.versioned_name_in_filesystem = self.get_versioned_file_name(with_prefix=True)

        if type_ == 'css':
            self.associated_bucket = css_bucket

        elif type_ == 'js':
            self.associated_bucket = js_bucket

    def minify(self):
        input_ = self.path_in_filesystem
        self.minified_path = input_ + '.temp'

        if self.type_ == 'css':
            compress_css(input_, self.minified_path)

        elif self.type_ == 'js':
            compile_js(input_, self.minified_path)

    def gzip(self):
        input_ = self.minified_path
        self.gzipped_path = input_ + '.gz'

        gzip_file(input_, self.gzipped_path)

    def get_versioned_file_name(self, with_prefix=True):
        if with_prefix:
            input_path = self.path_in_filesystem
        else:
            input_path = self.file_path

        base_path = re.sub(r'\.(css|js)', '', input_path)
        return (base_path + '-' + self.version + '.' + self.type_)

    def upload(self):
        upload_gzipped_file_to_bucket(self.versioned_name_in_filesystem,
                                      self.versioned_name_in_bucket,
                                      self.type_,
                                      self.associated_bucket)

    def exists_in_bucket(self):
        return file_exists_in_s3_bucket(self.versioned_name_in_bucket,
                                        self.associated_bucket)


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


def rename_file(source, destination):
    os.rename(source, destination)


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

    k.set_contents_from_filename(source_path, headers=headers, policy='public-read')


if __name__ == '__main__':
    deploy_main()
