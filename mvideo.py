import asyncio
import math
import requests

from config import headers, cookies


async def get_data_mvideo():
    ids = 118 #Ноутбуки
    params = {
        'categoryId': f'{ids}',
        'offset': '0',
        'limit': '24',
        'filterParams': 'WyJ0b2xrby12LW5hbGljaGlpIiwiLTEyIiwiZGEiXQ==',
        'doTranslit': 'true',
    }
    session = requests.Session()
    resp = session.get('https://www.mvideo.ru/bff/products/listing', params=params, cookies=cookies,
                           headers=headers).json()
    total_items = resp['body']['total']
    total_pages = math.ceil(total_items / 24)
    print(f'[INFO] Total positions: {total_items} | Total pages: {total_pages}')
    for i in range(total_pages):
        try:
            products_desc = {}
            products_prices = {}
            offset = f'{i * 24}'
            params = {
                'categoryId': f'{ids}',
                'offset': offset,
                'limit': '24',
            }
            resp = session.get('https://www.mvideo.ru/bff/products/listing', params=params, cookies=cookies,
                               headers=headers).json()
            page_products_ids = resp['body']['products']
            data = {
                'productIds': page_products_ids,
            }
            resp = session.post('https://www.mvideo.ru/bff/product-details/list', cookies=cookies, headers=headers,
                                json=data)
            tr = 1
            while resp.status_code != 200 and tr < 5:
                await asyncio.sleep(30)  #время сна, так как иногда запросы не проходят, так получается спарсить всю категорию
                # time.sleep(30)
                resp = session.post('https://www.mvideo.ru/bff/product-details/list', cookies=cookies, headers=headers,
                                    json=data)
                tr += 1
            print(f'[INFO] Response code: {resp.status_code}')
            if resp.status_code == 200:
                products_desc[i] = resp.json()
                products_ids_str = ','.join(page_products_ids)
                params = {
                    'productIds': products_ids_str,
                    'isPromoApplied': 'true'
                }
                resp = session.get('https://www.mvideo.ru/bff/products/prices', params=params, cookies=cookies,
                                   headers=headers)
                tr = 1
                while resp.status_code != 200 and tr < 5:
                    await asyncio.sleep(30)
                    resp = session.get('https://www.mvideo.ru/bff/products/prices', params=params, cookies=cookies,
                                       headers=headers)
                    tr += 1
                resp = resp.json()
                material_prices = resp['body']['materialPrices']
                for item in material_prices:
                    item_id = item['price']['productId']
                    item_base_price = item['price']['basePrice']
                    item_current_price = item['price']['salePrice']
                    products_prices[item_id] = {
                        'item_basePrice': item_base_price,
                        'item_currentPrice': item_current_price,
                    }
                print(f'[+] Success get {i + 1} of the {total_pages} pages success')
                n = 0
                for items in products_desc.values():
                    products = items['body']['products']
                    for item in products:
                        product_id = item.get('productId')
                        if product_id in products_prices:
                            prices = products_prices[product_id]
                        name = items['body']['products'][n]['name']
                        current_price = prices['item_currentPrice']
                        link = f'https://www.mvideo.ru/products/{item["nameTranslit"]}-{product_id}'
                        if n == len(items['body']['products']) - 1:
                            n = 0
                        else:
                            n += 1
                        yield {
                            'id' : product_id,
                            'name' : name,
                            'price' : int(current_price),
                            'link' : link
                        }
            else:
                print(f'[!] Skipped {i + 1} page')
        except Exception as e:
            print(f'[!] Skipped {i + 1} page', e.__class__.__name__)

# async def test_parser():
#     async for product in get_data_mvideo():
#         print(product)
#
# asyncio.run(test_parser())