import os

from Fuction import fetch_latest_dist_zip, unzip_file

if os.environ.get('RUN_AND_UPDATE_WEB') or os.environ.get('RUN_AND_UPDATE_WEB') == 'true':
    file_path = fetch_latest_dist_zip('thshu/fnos-tv-web')
    if file_path:
        unzip_file('./dist.zip')