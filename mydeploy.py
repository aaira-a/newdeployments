
import boto
import configparser
import gzip
import os
import re
import subprocess
import xml.etree.ElementTree as ET


AWS_CONFIG_PATH = ''    # path to config file (ini format) containing aws credentials
AWS_PROFILE = ''        # name of aws profile from the config file to be used
BASE_PATH = ''          # path of the repo www folder
CSS_BUCKET = ''         # name of the css bucket
JS_BUCKET = ''          # name of the js bucket
XML_PATH = ''           # path of the xml file containing latest file versions


def deploy_main():

    cred = get_aws_credentials(AWS_CONFIG_PATH, AWS_PROFILE)

    css_bucket = connect_to_bucket(cred, CSS_BUCKET)
    js_bucket = connect_to_bucket(cred, JS_BUCKET)

    files = create_list_from_xml(XML_PATH)

    for file_ in files:

        file_path = BASE_PATH + file_[0]
        file_type = file_[1]
        file_version = file_[2]

        minify_file(file_path, file_type)

        gzip_file(file_path + '.temp')

        versioned_file_path = get_versioned_file_name(file_path + '.temp.gz', file_version, file_type)
        rename_file(file_path + '.temp.gz', versioned_file_path)

        versioned_file_path_without_base = get_versioned_file_name(file_[0] + '.temp.gz', file_version, file_type)

        if file_type == 'css':
            upload_gzipped_file_to_bucket(versioned_file_path, versioned_file_path_without_base, file_type, css_bucket)

        elif file_type == 'js':
            upload_gzipped_file_to_bucket(versioned_file_path, versioned_file_path_without_base, file_type, js_bucket)


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


def minify_file(path, file_type):
    if file_type == 'css':
        compress_css(path)

    elif file_type == 'js':
        compile_js(path)


def compress_css(path):
    return subprocess.call(['java', '-jar', 'yuicompressor-2.4.8.jar', path, '-o', path + '.temp'])


def compile_js(path):
    return subprocess.call(['java', '-jar', 'compiler.jar', '--js', path, '--js_output_file', path + '.temp'])


def gzip_file(path):
    with open(path, 'rb') as input_file:
        with gzip.open(path + '.gz', 'wb') as output_file:
            output_file.writelines(input_file)


def get_versioned_file_name(path_temp, version, file_type):
    base_path = re.sub(r'\.(css|js)\.temp\.gz', '', path_temp)
    return (base_path + '-' + version + '.' + file_type)


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
