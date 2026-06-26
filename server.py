# -*- coding: utf-8 -*-
"""
Встроенный HTTP сервер без внешних зависимостей.
Обслуживает статические файлы, API для конвертации.
"""

import http.server
import socketserver
import json
import os
import traceback
from urllib.parse import urlparse, parse_qs
from pathlib import Path

from converter import convert, guess_mapping, parse_cfg, ROLE_ORDER, ROLE_IS_CURRENT


BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / 'static'


class SVConverterHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self.serve_file('index.html')
        elif parsed.path.startswith('/static/'):
            self.serve_static(parsed.path[8:])
        elif parsed.path == '/api/get-roles':
            self.api_get_roles()
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/convert':
            self.api_convert()
        else:
            self.send_error(404)

    def serve_file(self, fname):
        fpath = STATIC_DIR / fname
        if not fpath.exists():
            self.send_error(404)
            return
        try:
            with open(fpath, 'rb') as f:
                data = f.read()
            mime = 'text/html' if fname.endswith('.html') else 'application/javascript'
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500)

    def serve_static(self, fname):
        fpath = STATIC_DIR / fname
        if not fpath.exists():
            self.send_error(404)
            return
        try:
            with open(fpath, 'rb') as f:
                data = f.read()
            mime = 'application/javascript' if fname.endswith('.js') else 'text/css'
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', len(data))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(500)

    def api_get_roles(self):
        resp = {
            'roles': ROLE_ORDER,
            'role_is_current': ROLE_IS_CURRENT,
        }
        self.send_json_response(resp)

    def api_convert(self):
        try:
            content_len = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_len)
            data = json.loads(body.decode('utf-8'))

            cfg_text = data.get('cfg', '')
            dat_text = data.get('dat', '')
            mapping = data.get('mapping', {})
            params = data.get('params', {})

            # валидация mapping
            for role in ROLE_ORDER:
                if role not in mapping or mapping[role] is None:
                    raise ValueError(f'Не задано сопоставление для роли {role}')
                mapping[role] = int(mapping[role])

            # валидация params
            if 'mac' not in params or not params['mac']:
                raise ValueError('MAC адрес обязателен')
            if 'appid' not in params or not params['appid']:
                raise ValueError('APPID обязателен')
            if 'svid' not in params or not params['svid']:
                raise ValueError('SVID обязателен')

            params.setdefault('vlanid', 0)
            params.setdefault('confrev', 1)
            params.setdefault('vlan_pcp', 4)
            params.setdefault('simulation', False)
            params.setdefault('ktt', 1.0)
            params.setdefault('ktn', 1.0)
            params.setdefault('k3i0', 1.0)
            params.setdefault('k3u0', 1.0)

            pcap_bytes, n_frames = convert(cfg_text, dat_text, mapping, params)
            pcap_b64 = __import__('base64').b64encode(pcap_bytes).decode('ascii')

            resp = {
                'success': True,
                'pcap_b64': pcap_b64,
                'n_frames': n_frames,
                'pcap_size': len(pcap_bytes),
            }
            self.send_json_response(resp)
        except Exception as e:
            resp = {
                'success': False,
                'error': str(e),
                'traceback': traceback.format_exc(),
            }
            self.send_json_response(resp, 400)

    def send_json_response(self, data, status_code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # Отключаем стандартный лог


def run_server(host='127.0.0.1', port=8000):
    handler = SVConverterHandler
    handler.directory = str(STATIC_DIR)
    with socketserver.TCPServer((host, port), handler) as httpd:
        print(f'[SV Converter] Listening on http://{host}:{port}')
        httpd.serve_forever()
