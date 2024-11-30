import json, os, math, time
from xlsxwriter.workbook import Workbook
import datetime
import requests
from config import headers, cookies


def get_data_mvideo():
    ids = 118 #Ноутбуки
    params = {
        'categoryId': f'{ids}',
        'offset': '0',
        'limit': '24',
        'filterParams': 'WyJ0b2xrby12LW5hbGljaGlpIiwiLTEyIiwiZGEiXQ%3D%3D',
        'doTranslit': 'true',
    }
    session = requests.Session()
    resp = session.get('https://www.mvideo.ru/bff/products/listing', params=params, cookies=cookies,
                           headers=headers).json()
    total_items = resp['body']['total']
    total_pages = math.ceil(total_items / 24)
    print(f'[INFO] Total positions: {total_items} | Total pages: {total_pages}')
    for i in range(total_pages // 10):
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
                time.sleep(30)  #время сна, так как иногда запросы не проходят, так получается спарсить всю категорию
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
                                   headers=headers).json()
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
                        print(name, current_price, link)
                        # yield {name, current_price, link}
            else:
                print(f'[!] Skipped {i + 1} page')
        except Exception as e:
            print(f'[!] Skipped {i + 1} page', e.__class__.__name__)
    # with open('data/1_product_description.json', 'w', encoding='UTF-8') as file:
    #     json.dump(products_desc, file, indent=4, ensure_ascii=False)
    # with open('data/2_product_prices.json', 'w', encoding='UTF-8') as file:
    #     json.dump(products_prices, file, indent=4, ensure_ascii=False)


# def get_result(worksheet, center):
#     row = 1
#
#     with open('data/1_product_description.json', 'r', encoding='UTF-8') as file:
#         products_desc = json.load(file)
#     with open('data/2_product_prices.json', 'r', encoding='UTF-8') as file:
#         products_prices = json.load(file)
#
#             worksheet.write(row, 0, name, center)
#             worksheet.write(row, 1, current_price, center)
#             worksheet.write(row, 2, link)
#             if n == len(items['body']['products']) - 1:
#                 n = 0
#             else:
#                 n += 1
#             row += 1


# def get_categoryId(name):
#     ids = {
#         'Ноутбуки': '118',
#         'Смартфоны': '205',
#         'Планшеты': '195',
#     }
#     item_id = ids[name]
#     return item_id


# def parse(category):
#     if not os.path.exists('output'):
#         os.mkdir('output')
#     path = f'output\\{category}-{datetime.datetime.now().strftime("%d-%m-%Y")}.xlsx'
#     workbook = Workbook(path)
#     format = workbook.add_format({'bold': True, 'align': 'center'})
#     center = workbook.add_format({'align': 'center'})
#     worksheet = workbook.add_worksheet()
#     worksheet.write(0, 0, 'Название', format)
#     worksheet.write(0, 1, 'Цена', format)
#     worksheet.write(0, 2, 'Ссылка на товар', format)
#     get_data_mvideo(get_categoryId(category))
#     get_result(worksheet, center)
#     worksheet.autofit()
#     workbook.close()
#     return path


# parse('Ноутбуки')
get_data_mvideo()