from flask import Flask, request
from Fuction import get_platform_link
from Getdanmu import download_barrage, RetDanMuType, GetDanmuBase

app = Flask(__name__)


@app.route('/danmu/get')
def main():  # put application's code here
    douban_id = request.args.get('douban_id')
    episode_number = request.args.get('episode_number')
    url = request.args.get('url')
    all_danmu_data = {}
    if url is None:
        if episode_number:
            episode_number = int(episode_number)
        url_dict = get_platform_link(douban_id)
        if episode_number is not None:
            url_dict = {
                episode_number: url_dict[f'{episode_number}']
            }

        for k, v in url_dict.items():
            for u in v:
                danmu_data: RetDanMuType = download_barrage(u)
                if k in all_danmu_data.keys():
                    all_danmu_data[k] += danmu_data.list
                else:
                    all_danmu_data[k] = danmu_data.list
        return all_danmu_data
    else:
        danmu_data: RetDanMuType = download_barrage(url)
        return danmu_data.list


@app.route('/danmu/getEmoji')
def get_emoji():
    douban_id = request.args.get('douban_id')
    url_dict = get_platform_link(douban_id)
    emoji_data = {}
    for url in url_dict['1']:
        for c in GetDanmuBase.__subclasses__():
            if c.domain in url:
                data = c().getImg(url)
                for d in data:
                    emoji_data[d['emoji_code']] = d['emoji_url']
    return emoji_data


if __name__ == '__main__':
    app.run()
