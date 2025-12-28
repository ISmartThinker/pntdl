from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import time
import re

app = Flask(__name__)

def get_csrf_token():
    session = requests.Session()
    
    try:
        homepage_url = 'https://klickpin.com/'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'Upgrade-Insecure-Requests': '1',
            'X-Requested-With': 'mark.via.gp',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
        }
        
        session.get(homepage_url, headers=headers, timeout=30)
        
        timestamp = int(time.time() * 1000)
        csrf_url = f'https://klickpin.com/get-csrf-token.php?t={timestamp}'
        
        csrf_headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Referer': 'https://klickpin.com/',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
        }
        
        response = session.get(csrf_url, headers=csrf_headers, timeout=30)
        
        if response.status_code == 200:
            try:
                data = response.json()
                csrf_token = data.get('csrf_token')
                return csrf_token, session
            except:
                return None, session
        
        return None, session
        
    except Exception as e:
        return None, session

def parse_download_page(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    result = {
        'title': None,
        'thumbnail': None,
        'downloads': []
    }
    
    title_tag = soup.find('p', class_='card-text')
    if title_tag:
        strong_tag = title_tag.find('strong')
        if strong_tag:
            result['title'] = strong_tag.get_text(strip=True)
    
    img_tag = soup.find('img', class_='card-img-top')
    if img_tag and img_tag.get('src'):
        result['thumbnail'] = img_tag['src']
    
    download_buttons = soup.find_all('a', href=True)
    for button in download_buttons:
        onclick = button.get('onclick', '')
        href = button.get('href', '')
        
        if 'downloadFile' in onclick:
            match = re.search(r"downloadFile\('([^']+)'", onclick)
            if match:
                download_url = match.group(1)
                quality = 'HD (564x)' if '564x' in download_url else 'Original'
                
                if download_url not in [d['url'] for d in result['downloads']]:
                    result['downloads'].append({
                        'quality': quality,
                        'url': download_url
                    })
        
        elif 'i.pinimg.com' in href and 'dl.klickpin.com' not in href:
            if href not in [d['url'] for d in result['downloads']]:
                if '564x' in href:
                    quality = 'HD (564x)'
                elif 'originals' in href:
                    quality = 'Original'
                else:
                    quality = 'Standard'
                
                result['downloads'].append({
                    'quality': quality,
                    'url': href
                })
    
    return result

def download_pinterest(pinterest_url):
    try:
        csrf_token, session = get_csrf_token()
        
        if not csrf_token:
            return {
                'status': 'error',
                'message': 'Failed to get CSRF token'
            }
        
        download_url = 'https://klickpin.com/download'
        
        payload = {
            'url': pinterest_url,
            'csrf_token': csrf_token
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'Origin': 'https://klickpin.com',
            'Upgrade-Insecure-Requests': '1',
            'X-Requested-With': 'mark.via.gp',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': 'https://klickpin.com/',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
        }
        
        response = session.post(download_url, data=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            parsed_data = parse_download_page(response.text)
            
            if parsed_data['downloads']:
                return {
                    'status': 'success',
                    'title': parsed_data['title'],
                    'thumbnail': parsed_data['thumbnail'],
                    'downloads': parsed_data['downloads'],
                    'total_downloads': len(parsed_data['downloads'])
                }
            else:
                return {
                    'status': 'error',
                    'message': 'No download links found in response'
                }
        else:
            return {
                'status': 'error',
                'message': f'HTTP {response.status_code}'
            }
            
    except requests.exceptions.Timeout:
        return {
            'status': 'error',
            'message': 'Request timeout'
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
    
    result = download_pinterest(pinterest_url)
    
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
