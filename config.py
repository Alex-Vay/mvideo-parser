import requests

url = "https://www.mvideo.ru/noutbuki-planshety-komputery-8/noutbuki-118"  # Замените на целевой сайт
cookies = requests.get(url).cookies

headers = {
    'accept': '*/*',
    'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7,zh-CN;q=0.6,zh;q=0.5,ja;q=0.4',
    'dnt': '1',
    'priority': 'u=1, i',
    'referer': 'https://www.mvideo.ru/noutbuki-planshety-komputery-8/noutbuki-118?from=homepage',
    'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'x-kl-kfa-ajax-request': 'Ajax_Request',
}
