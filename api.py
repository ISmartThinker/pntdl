from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

app = Flask(__name__)

class PinterestDownloader:
    def __init__(self):
        self.savepin_url = 'https://www.savepin.app/download.php'
        
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
    
    def download_video_data(self, video_url):
        params = {
            'url': video_url,
            'lang': 'en',
            'type': 'redirect'
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Referer': 'https://www.savepin.app/'
        }
        
        try:
            response = self.session.get(self.savepin_url, params=params, headers=headers, timeout=15)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                return {
                    'success': False,
                    'error': 'Unexpected JSON response from savepin'
                }
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            title_tag = soup.find('h1')
            title = title_tag.text.strip() if title_tag else 'Unknown'
            
            download_links = []
            table = soup.find('table', {'border': '1'})
            if table:
                tbody = table.find('tbody')
                if tbody:
                    rows = tbody.find_all('tr')
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) == 3:
                            quality = cells[0].text.strip()
                            format_type = cells[1].text.strip().lower()
                            link_tag = cells[2].find('a', {'class': 'button is-success is-small'})
                            if link_tag and 'href' in link_tag.attrs:
                                href = link_tag['href']
                                if href.startswith('force-save.php?url='):
                                    media_url = href.replace('force-save.php?url=', '')
                                    media_url = unquote(media_url)
                                    download_links.append({
                                        'quality': quality,
                                        'url': media_url,
                                        'extension': 'jpg' if format_type == 'jpg' else 'mp4',
                                        'type': 'image' if format_type == 'jpg' else 'video'
                                    })
            
            if download_links:
                return {
                    'success': True,
                    'data': {
                        'title': title,
                        'medias': download_links,
                        'source': 'pinterest'
                    },
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'success': False,
                'error': 'No media found for the provided URL'
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Failed to fetch media: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

downloader = PinterestDownloader()

@app.route('/', methods=['GET'])
def docs():
    return jsonify({
        'api': 'Pinterest Video Downloader API',
        'version': '1.0',
        'endpoints': {
            '/api/download': {
                'method': 'GET',
                'description': 'Download Pinterest videos and images',
                'parameters': {
                    'url': 'Pinterest URL (required)'
                },
                'example': '/api/download?url=https://in.pinterest.com/pin/484699978668992701/'
            }
        },
        'response_format': {
            'success': 'boolean',
            'data': {
                'title': 'string',
                'medias': [
                    {
                        'quality': 'string',
                        'url': 'string',
                        'extension': 'string',
                        'type': 'string'
                    }
                ],
                'source': 'string'
            },
            'timestamp': 'ISO 8601 datetime'
        }
    }), 200

@app.route('/api/download', methods=['GET'])
def download():
    try:
        video_url = request.args.get('url', '').strip()
        
        if not video_url:
            return jsonify({
                'success': False,
                'error': 'URL parameter is required'
            }), 400
        
        try:
            parsed = urlparse(video_url)
            if 'pinterest' not in parsed.netloc:
                return jsonify({
                    'success': False,
                    'error': 'Invalid Pinterest URL'
                }), 400
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Invalid URL format'
            }), 400
        
        result = downloader.download_video_data(video_url)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
