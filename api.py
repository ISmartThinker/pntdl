from flask import Flask, request, jsonify
import cloudscraper
from bs4 import BeautifulSoup
import json

app = Flask(__name__)

def scrape_fresh_session():
    scraper = cloudscraper.create_scraper()
    
    url = 'https://pindown.io/en1'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'upgrade-insecure-requests': '1',
        'dnt': '1',
        'x-requested-with': 'mark.via.gp',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'priority': 'u=0, i'
    }
    
    response = scraper.get(url, headers=headers, timeout=30)
    html = response.text
    
    cookies = {}
    for cookie in scraper.cookies:
        cookies[cookie.name] = cookie.value
    
    session_data = cookies.get('session_data', '')
    
    soup = BeautifulSoup(html, 'html.parser')
    
    token_name = ''
    token_value = ''
    
    possible_names = ['rBYgv', 'NaqrE']
    for name in possible_names:
        token_input = soup.find('input', {'name': name, 'type': 'hidden'})
        if token_input and token_input.get('value'):
            token_name = name
            token_value = token_input.get('value')
            break
    
    if not token_value:
        all_hidden_inputs = soup.find_all('input', {'type': 'hidden'})
        for inp in all_hidden_inputs:
            inp_name = inp.get('name')
            inp_value = inp.get('value')
            
            if inp_name and inp_name != 'lang' and inp_value and len(inp_value) == 32:
                token_name = inp_name
                token_value = inp_value
                break
    
    scraped = {
        'scraper': scraper,
        'cookies': cookies,
        'session_data': session_data,
        'token_name': token_name,
        'token_value': token_value
    }
    
    return scraped

def parse_download_links(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    downloads = []
    
    rows = soup.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) >= 2:
            quality_cell = cells[0]
            download_cell = cells[1]
            
            quality = quality_cell.get_text(strip=True)
            link_tag = download_cell.find('a', href=True)
            
            if link_tag and 'dl.pincdn.app' in link_tag['href']:
                download_url = link_tag['href']
                downloads.append({
                    'quality': quality,
                    'url': download_url
                })
    
    img_tag = soup.find('img', src=True)
    if img_tag:
        preview_url = img_tag['src']
    else:
        preview_url = None
    
    title_tag = soup.find('span', class_='video-des')
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        title = None
    
    return {
        'downloads': downloads,
        'preview': preview_url,
        'title': title
    }

def download_pinterest_video(pinterest_url):
    try:
        scraped = scrape_fresh_session()
        
        scraper = scraped['scraper']
        token_name = scraped['token_name']
        token_value = scraped['token_value']
        
        if not token_value:
            return {
                'status': 'error',
                'message': 'Token not found in page'
            }
        
        action_url = 'https://pindown.io/action'
        
        payload = {
            'url': pinterest_url,
            token_name: token_value,
            'lang': 'en'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'origin': 'https://pindown.io',
            'x-requested-with': 'mark.via.gp',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': 'https://pindown.io/en1',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'priority': 'u=1, i'
        }
        
        response = scraper.post(action_url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success') and result.get('html'):
                parsed_data = parse_download_links(result['html'])
                
                return {
                    'status': 'success',
                    'title': parsed_data['title'],
                    'preview': parsed_data['preview'],
                    'downloads': parsed_data['downloads'],
                    'total_downloads': len(parsed_data['downloads'])
                }
            else:
                return {
                    'status': 'error',
                    'message': 'Invalid response from server',
                    'data': result
                }
        else:
            return {
                'status': 'error',
                'message': f'HTTP {response.status_code}'
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Error: {str(e)}'
        }

@app.route('/api/pnt/dl', methods=['GET'])
def pinterest_dl():
    pinterest_url = request.args.get('url')
    
    if not pinterest_url:
        return jsonify({
            'status': 'error',
            'message': 'URL parameter is required',
            'example': '/api/pnt/dl?url=https://in.pinterest.com/pin/484699978669418137/',
            'api_owner': '@ISmartCoder',
            'updates_channel': '@abirxdhackz'
        }), 400
    
    result = download_pinterest_video(pinterest_url)
    
    result['api_owner'] = '@ISmartCoder'
    result['updates_channel'] = '@abirxdhackz'
    
    if result['status'] == 'success':
        return jsonify(result), 200
    else:
        return jsonify(result), 500

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'message': 'Pinterest Downloader API',
        'endpoint': '/api/pnt/dl',
        'method': 'GET',
        'parameters': {
            'url': 'Pinterest URL (required)'
        },
        'example': '/api/pnt/dl?url=https://in.pinterest.com/pin/484699978669418137/',
        'api_owner': '@ISmartCoder',
        'updates_channel': '@abirxdhackz'
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)