import asyncio
import math
import requests
from config import headers, cookies


async def perform_request(method, url, session, max_retries=5, sleep_interval=30, **kwargs):
    for attempt in range(max_retries):
        response = session.request(method, url, **kwargs)
        if response.status_code == 200:
            return response
        await asyncio.sleep(sleep_interval)
    raise NotImplemented()


async def get_data_mvideo():
    ids = 118  #Ноутбуки
    base_url = 'https://www.mvideo.ru'
    session = requests.Session()
    initial_params = {
        'categoryId': f'{ids}',
        'offset': '0',
        'limit': '24',
        'filterParams': 'WyJ0b2xrby12LW5hbGljaGlpIiwiLTEyIiwiZGEiXQ==',
        'doTranslit': 'true',
    }
    response = await perform_request('GET', f'{base_url}/bff/products/listing', session, params=initial_params,
                                     cookies=cookies, headers=headers)
    resp_json = response.json()
    total_items = resp_json['body']['total']
    total_pages = math.ceil(total_items / 24)
    print(f'[INFO] Total positions: {total_items} | Total pages: {total_pages}')

    for i in range(total_pages):
        try:
            offset = f'{i * 24}'
            page_params = {
                'categoryId': f'{ids}',
                'offset': offset,
                'limit': '24',
            }

            response = await perform_request('GET', f'{base_url}/bff/products/listing', session, params=page_params,
                                             cookies=cookies, headers=headers)

            page_products_ids = response.json()['body']['products']

            product_details_data = {'productIds': page_products_ids}
            response = await perform_request('POST', f'{base_url}/bff/product-details/list', session, cookies=cookies,
                                             headers=headers, json=product_details_data)

            products_desc = response.json()

            products_ids_str = ','.join(page_products_ids)
            price_params = {
                'productIds': products_ids_str,
                'isPromoApplied': 'true',
            }
            response = await perform_request('GET', f'{base_url}/bff/products/prices', session, params=price_params,
                                             cookies=cookies, headers=headers)

            material_prices = response.json()['body']['materialPrices']
            products_prices = {
                item['price']['productId']: {
                    'item_basePrice': item['price']['basePrice'],
                    'item_currentPrice': item['price']['salePrice'],
                }
                for item in material_prices
            }
            print(f'[+] Success fetching page {i + 1} of {total_pages}')

            for product in products_desc['body']['products']:
                product_id = product.get('productId')
                name = product.get('name')
                link = f'{base_url}/products/{product["nameTranslit"]}-{product_id}'
                prices = products_prices.get(product_id, {})
                yield {
                    'id': product_id,
                    'name': name,
                    'price': int(prices.get('item_currentPrice', 0)),
                    'link': link,
                }
        except Exception as e:
            print(f'[!] Skipped {i + 1} page: {e}')

# # Для тестирования
# async def parser_t():
#     async for product in get_data_mvideo():
#         print(product)
#
# asyncio.run(parser_t())
