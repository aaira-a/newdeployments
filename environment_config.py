
# all paths are relative to jenkins job's workspace (absolute path is fine too)

# common config for both deployment and cleanup scripts
AWS_CONFIG_PATH = ''    # path to config file (ini format) containing aws credentials
AWS_PROFILE = ''        # name of aws profile from the config file to be used

CSS_BUCKET = ''         # name of the css bucket
IMAGE_BUCKET = ''       # name of the image bucket
JS_BUCKET = ''          # name of the js bucket

XML_PATH = ''           # path of the xml file containing latest file versions


# config specific to deployment script
JAVA_PATH = ''          # path of the folder containing java binary, may default to empty if already defined in system path
MINIFIER_PATH = ''      # path of the folder containing the minifiers binaries (closure compiler & yuicompressor)
PREFIX_PATH = ''        # path of the repo www folder


# config specific to cleanup script
CSS_PREFIX = ''         # prefix of base path in buckets (eg. base folder name)
IMAGE_PREFIX = ''       # to narrow down selections during bucket.list() operations
JS_PREFIX = ''          # by excluding other irrelevant folders (log, etc)
