
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
