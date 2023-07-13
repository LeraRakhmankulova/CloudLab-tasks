import os
import sys
import boto3
import argparse
import configparser

def generate_album_html(photos):
    template = """
    <!doctype html>
    <html>
        <head>
            <meta charset=utf-8>
            <link rel="stylesheet" type="text/css" href="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.css" />
            <style>
                .galleria{ width: 960px; height: 540px; background: #000 }
            </style>
            <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.0/jquery.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/galleria.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/galleria/1.6.1/themes/classic/galleria.classic.min.js"></script>
        </head>
        <body>
            <div class="galleria">
    """
    for photo in photos:
        template += f"""
                <img src="{photo}" data-title="{os.path.basename(photo)}">
            """

    template += """
            </div>
            <p>Вернуться на <a href="index.html">главную страницу</a> фотоархива</p>
            <script>
                (function() {
                    Galleria.run('.galleria');
                }());
            </script>
        </body>
    </html>
    """
    return template


def generate_index_html(albums):
    template = '''<html>
    <head>
        <meta charset=utf-8>
        <title>PhotoAlbum</title>
    </head>
    <body>
        <h1>PhotoAlbum</h1>
        <ul>\n'''

    album_number = 1
    for album in albums:
        album_name = album['Key']
        album_html = f'<li><a href="album{album_number}.html">{album_name}</a></li>\n'
        template += album_html
        album_number += 1

    template += '''        </ul>
    </body>
</html>'''

    return template


def get_mksite():
    config = configparser.ConfigParser()
    config_path = get_config_file_path()
    config.read(config_path)

    s3 = boto3.client('s3',
                    endpoint_url=config['DEFAULT']['endpoint_url'],
                    aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                    aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    response = s3.list_objects_v2(Bucket=config['DEFAULT']['bucket'])
    if not response.get('Contents'):
        print("Photo albums not found")
        sys.exit(1)
    else:
        albums = [obj for obj in response['Contents'] if obj['Key'].endswith('/')]
    
    index_html = generate_index_html(albums)
    index_html_key = f"index.html"
    s3.put_object(Bucket=config['DEFAULT']['bucket'], Key=index_html_key, Body=index_html, ContentType='text/html')

    for album in albums:
        html = generate_album_html((album['Key']))
        html_key = f"album{album_number}.html"
        s3.put_object(Bucket=config['DEFAULT']['bucket'], Key=html_key, Body=html, ContentType='text/html')
        album_number += 1

    print("Website generation and publishing completed.")


def get_delete(album):
    config_file = get_config_file_path()
    if not os.path.isfile(config_file):
        print("Configuration file not found. Use 'init' command to initialize.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)

    bucket_name = config['DEFAULT'].get('bucket')

    if not bucket_name:
        print("Bucket name is not defined in the configuration file.")
        sys.exit(1)  
          
    if list(bucket_name.objects.filter(Prefix=f"albums/{album}/").limit(1)):
        objects = []
        for obj in bucket_name.objects.filter(Prefix=f"albums/{album}/"):
            objects.append({'Key': obj.key})

        bucket_name.delete_objects(
            Delete={
                'Objects': objects
            }
        )
        print(f"Delete album with name {album}")
        sys.exit(0)
    else:
        print(f"Warning: Photo album not found {album}")
        sys.exit(1)


def get_upload(album):
    config_file = get_config_file_path()

    if not os.path.isfile(config_file):
        print(f"Configuration file not found. Use 'init' command to initialize.")
        sys.exit(1)
    
    config = configparser.ConfigParser()
    config.read(config_file)
    bucket_name = config['DEFAULT'].get('bucket')

    if not bucket_name:
        print(f"Bucket name is not defined in the configuration file.")
        sys.exit(1)

    s3 = boto3.client('s3',
                    endpoint_url=config['DEFAULT']['endpoint_url'],
                    aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                    aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])

    if s3.list_objects(Bucket=bucket_name, Prefix=f"{album}/").limit(1):
        print(f"Found directory with name {album}")

    else:
        print(f"Not found {album} in albums")
        try:
            s3.put_object(Body='', Bucket=bucket_name, Key=f"{album}/")
            print(f"Create directory with name {album} in albums")
            sys.exit(0)
        except:
            print(f"Warning: This account don`t gave Access for create directory in albums/")
            sys.exit(1)


def get_init():
    config = configparser.ConfigParser()

    bucket_name = input(f"bucket name: ")
    aws_access_key_id = input(f"AWS Access Key ID: ")
    aws_secret_access_key = input(f"AWS Secret Access Key: ")
    
    config_file = get_config_file_path()
    config.read(config_file)

    config['DEFAULT'] = {
        'bucket': bucket_name,
        'aws_access_key_id': aws_access_key_id,
        'aws_secret_access_key': aws_secret_access_key,
        'region': 'ru-central1',
        'endpoint_url': 'https://storage.yandexcloud.net'
    }

    with open(config_file, 'w') as file:
        config.write(file)

    s3 = boto3.resource('s3',
                        endpoint_url=config['DEFAULT']['endpoint_url'],
                        aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                        aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])
    s3.create_bucket(Bucket=config['DEFAULT']['bucket'])


def get_list():
    config_file = get_config_file_path()

    if not os.path.isfile(config_file):
        print(f"Configuration file not found. Use 'init' command to initialize.")
        sys.exit(1)

    config = configparser.ConfigParser()
    config.read(config_file)

    bucket_name = config['DEFAULT'].get('bucket')
    if not bucket_name:
        print(f"Bucket name is not defined in the configuration file.")
        sys.exit(1)

    s3 = boto3.client('s3',
                    endpoint_url=config['DEFAULT']['endpoint_url'],
                    aws_access_key_id=config['DEFAULT']['aws_access_key_id'],
                    aws_secret_access_key=config['DEFAULT']['aws_secret_access_key'])
    
    objects = s3.list_objects(Bucket=bucket_name)['Contents']

    if objects is None:
        print(f"Photo albums not found")
    
    albums = set([ object['Key'].split('/')[0] for object in objects if "/" in object['Key']])
    if albums:
        for album in sorted(albums):
            print(album)
    else:
        print(f"Photo not found")
        

def get_config_file_path():
    config_directory = os.path.join(os.path.expanduser("~"), ".config/cloudphoto")
    os.makedirs(config_directory, exist_ok=True)
    config_file = os.path.join(config_directory, "cloudphotorc")
    return config_file


def main():
    parser = argparse.ArgumentParser()

    subparser = parser.add_subparsers(dest='command')
    
    init = subparser.add_parser('init', help='initialize the program')
    
    list = subparser.add_parser('list', help='view the list of photos')
    
    upload = subparser.add_parser('upload', help='upload photos')
    upload.add_argument('--album', required=True, help='album name')
    upload.add_argument('--path', default=".", required=False, help='path to directory')    

    delete = subparser.add_parser('delete', help='delete album')
    delete.add_argument('album_name')
    
    mksite = subparser.add_parser('mksite', help='create website with photos')
    
    args = parser.parse_args()

    if args.command != 'init':
        config_file = get_config_file_path()
        if not os.path.isfile(config_file):
            print(f"Configuration file not found. Use 'init' command to initialize.")
            sys.exit(1)

    if args.command == 'init':
        get_init()

    if args.command == 'list':
        get_list()

    if args.command == 'upload':
        get_upload(args.album)

    if args.command == 'delete':
        get_delete(args.album)
      
    if args.command == 'mksite':
        get_mksite()
   
    else:
        print(f'Unknown command')


if __name__ == "__main__":
    main()