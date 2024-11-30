import time
import requests
from bs4 import BeautifulSoup
def get_price():
    response = requests.get(
        url="https://www.maxidom.ru/catalog/dushevye-sistemy/1001529332/"
    )
    soup = BeautifulSoup(response.content, "lxml")
    title = soup.find("span", itemprop="name")
    price = soup.find("div", class_="lvl1__product-body-buy-price-base")
    price = int(price["data-repid_price"])
    time.sleep(10)
    return title.get_text() if title else None, price or None, 1001529332