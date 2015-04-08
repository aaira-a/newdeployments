
import boto
import configparser
import gzip
import subprocess
import xml.etree.ElementTree as ET


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


def compress_css(path):
    return subprocess.call(['java', '-jar', 'yuicompressor-2.4.8.jar', path, '-o', path + '.temp'])


def compile_js(path):
    return subprocess.call(['java', '-jar', 'compiler.jar', '--js', path, '--js_output_file', path + '.temp'])


def gzip_file(path):
    with open(path, 'rb') as input_file:
        with gzip.open(path + '.gz', 'wb') as output_file:
            output_file.writelines(input_file)


def get_aws_credentials(path=None, profile=None):
    if profile is None or path is None:
        return None

    else:
        config = configparser.ConfigParser()
        config.read(path)
        p = config[profile]
        return [p['aws_access_key_id'], p['aws_secret_access_key']]


def check_if_file_exists_in_s3_bucket(path, bucket_, boto_cfg, profile):
    cred = get_aws_credentials(boto_cfg, profile)
    connection = boto.connect_s3(cred[0], cred[1])
    bucket = connection.get_bucket(bucket_)
    k = boto.s3.key.Key(bucket)
    k.key = path
    return k.exists()
