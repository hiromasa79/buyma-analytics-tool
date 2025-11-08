# scraper.py (Render対応・最終完成版)

import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
# webdriver-managerはRender環境では使わないため、コメントアウトまたは削除してもOK
# from webdriver_manager.chrome import ChromeDriverManager 
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from selenium.webdriver.chrome.options import Options

def scrape_product_details(driver, product_url):
    details = {
        'brand_name': '取得失敗', 'category_1': '', 'category_2': '', 'category_3': '',
        'access_count': '0', 'wish_count': '0', 'inquiry_count': '0',
        'price': '¥0', 'origin_place': '取得失敗', 'shipping_place': '取得失敗',
        'listing_date': '取得失敗',
        '在庫ステータ-ス': '無在庫'
    }
    try:
        driver.get(product_url)
        
        if "ページが見つかりませんでした" in driver.title or "出品がとりやめられました" in driver.page_source:
            print(f"    -> ページ削除済みまたはアクセス不可: {product_url}")
            details['brand_name'] = 'ページ削除済み'
            return details

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 's_brand')))
        detail_soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        try:
            stock_table_wrap = detail_soup.find('div', class_='cse-set__table-wrap')
            if stock_table_wrap and '◎' in stock_table_wrap.get_text():
                details['在庫ステータス'] = '有在庫'
        except Exception: pass
        
        try:
            brand_tag = detail_soup.find('a', class_='brand-link')
            if brand_tag: details['brand_name'] = brand_tag.text.strip()
        except Exception: pass
        
        try:
            all_ulikelinks = detail_soup.find_all('a', class_='ulinelink')
            temp_categories = []
            found_main_cat = False
            for link in all_ulikelinks:
                text = link.text.strip()
                if '×' in text:
                    if not found_main_cat:
                        all_matches = re.findall(r'（(.*?)）', text)
                        if all_matches:
                            details['category_1'] = all_matches[-1]
                            found_main_cat = True
                    sub_cat_match = re.search(r'×\s*(.*?)(?=\s*（|$)', text)
                    if sub_cat_match: temp_categories.append(sub_cat_match.group(1))
            details['category_2'] = temp_categories[0] if len(temp_categories) > 0 else ''
            details['category_3'] = temp_categories[1] if len(temp_categories) > 1 else ''
        except Exception: pass

        try:
            ac_tag = detail_soup.find('span', class_='ac_count')
            if ac_tag: details['access_count'] = ac_tag.text.strip()
        except Exception: pass
        
        try:
            fav_tag = detail_soup.find('span', class_='fav_count')
            if fav_tag: details['wish_count'] = fav_tag.text.strip().replace('人', '')
        except Exception: pass
        
        try:
            inq_tag = detail_soup.find('p', id='tabmenu_inqcnt')
            if inq_tag: details['inquiry_count'] = inq_tag.text.strip()
        except Exception: pass
        
        try:
            price_tag = detail_soup.find('span', class_='price_txt')
            if price_tag: details['price'] = price_tag.text.strip()
        except Exception: pass
        
        try:
            buy_area = detail_soup.find('dl', id='s_buying_area')
            if buy_area and buy_area.find('a'): details['origin_place'] = buy_area.find('a').text.strip()
        except Exception: pass
        
        try:
            ship_area = detail_soup.find('dl', id='s_shipment_area')
            if ship_area and ship_area.find('dd'): details['shipping_place'] = ship_area.find('dd').text.strip()
        except Exception: pass
        
        try:
            image_area = detail_soup.find('div', class_='item-main-image')
            image_tag = image_area.find('img') if image_area else None
            image_url = image_tag.get('src', '') if image_tag else ''
            match = re.search(r'/item/(\d{6})/', image_url)
            if match:
                date_str = match.group(1)
                details['listing_date'] = f"20{date_str[:2]}-{date_str[2:4]}-{date_str[4:]}"
        except Exception: pass

    except TimeoutException:
        print(f"    -> タイムアウト: ページ構造が異なるか、読み込みに失敗: {product_url}")
        details['brand_name'] = '構造違い/取得失敗'
    except Exception as e:
        print(f"    詳細取得ページへのアクセス自体に失敗: {e}")
        
    return details

def analyze_buyma(base_url, start_date_str, end_date_str):
    if not base_url or not base_url.startswith('https://www.buyma.com'):
        print("不正なURLのため処理を中断します。")
        return []
        
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    # ★★★ ここからがRender環境用の設定 ★★★
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument('user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
    
    driver = None
    try:
        # webdriver-manager を使わず、システムにインストールされたChromeを直接使う
        service = Service()
        driver = webdriver.Chrome(service=service, options=options)
        # ★★★ ここまでがRender環境用の設定 ★★★

        driver.implicitly_wait(10)
        
        BASE_URL_DOMAIN = 'https://www.buyma.com'
        all_product_base_info = []
        
        driver.get(base_url)
        
        page_count = 1
        stop_scraping = False
        while not stop_scraping:
            print(f"リストページ収集中: {page_count} ページ目")
            time.sleep(1)
            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.buyeritemtable_body')))
            except TimeoutException:
                print("ページの読み込みがタイムアウトしました。")
                break

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_boxes = soup.find_all('div', class_='buyeritemtable_body')
            if not product_boxes:
                print("商品リストが見つかりません。")
                break

            for box in product_boxes:
                contract_date_text = '取得失敗'
                p_tags = box.find_all('p')
                for p in p_tags:
                    if '成約日' in p.text:
                        contract_date_text = p.text
                        break
                if contract_date_text == '取得失敗': continue
                date_match = re.search(r'(\d{4}/\d{2}/\d{2})', contract_date_text)
                if not date_match: continue
                
                item_date = datetime.strptime(date_match.group(1), '%Y/%m/%d')
                if item_date < start_date:
                    stop_scraping = True
                    break
                
                if start_date <= item_date <= end_date:
                    name_tag = box.find('p', class_='buyeritem_name')
                    name = name_tag.text.strip() if name_tag else '名前取得失敗'
                    product_link_tag = name_tag.find('a') if name_tag else None
                    partial_url = product_link_tag['href'] if product_link_tag else ''
                    full_url = BASE_URL_DOMAIN + partial_url if partial_url else 'URL取得失敗'
                    
                    image_tag_in_list = box.find('img')
                    image_url_in_list = image_tag_in_list.get('src', '') if image_tag_in_list else ''
                    listing_match = re.search(r'/item/(\d{6})/', image_url_in_list)
                    listing_date = f"20{listing_match.group(1)[:2]}-{listing_match.group(1)[2:4]}-{listing_match.group(1)[4:]}" if listing_match else '取得失敗'
                    
                    order_count = '不明'
                    for p in p_tags:
                        if '注文数' in p.text:
                            order_count = p.text.strip().replace('注文数', '').replace(':', '').replace('：', '').strip()
                            break

                    all_product_base_info.append({
                        '商品名': name, '商品ページURL': full_url, 
                        '注文情報': order_count, '成約日': item_date.strftime('%Y-%m-%d'), 
                        '出品日': listing_date
                    })
            
            if stop_scraping: break
            try:
                next_button = driver.find_element(By.LINK_TEXT, '次へ')
                driver.execute_script("arguments[0].click();", next_button)
                page_count += 1
            except (NoSuchElementException, TimeoutException):
                break

        final_results = []
        if all_product_base_info:
            # main_windowの管理と新しいタブの作成をやめ、メモリ消費を抑える
            for i, base_info in enumerate(all_product_base_info):
                print(f"詳細情報取得中 ({i+1}/{len(all_product_base_info)})")
                details = {}
                if base_info['商品ページURL'] != 'URL取得失敗':
                    try:
                        # 新しいタブは開かず、現在のタブでURLにアクセスする
                        # scrape_product_details関数が内部で driver.get() を呼ぶのでこれでOK
                        details = scrape_product_details(driver, base_info['商品ページURL'])
                    except Exception as e:
                        print(f"詳細ページアクセスエラー: {e}")

                product_info = base_info.copy()
                product_info.update(details)
                final_results.append(product_info)
        return final_results
    except WebDriverException as e:
        print(f"WebDriverでエラーが発生しました: {e}")
        return []
    finally:
        if driver:
            driver.quit()