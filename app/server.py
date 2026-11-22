"""Dependency-free HTTP server for the ReviewLens single-page application."""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from app import config, service, store
from app.ai import ProviderError

PUBLIC = config.ROOT / 'public'
MAX_BODY = 3 * 1024 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = 'ReviewLens/1.0'

    def send_json(self, data, status=200):
        payload = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/health':
            return self.send_json({'ok': True, 'mode': 'offline_preview' if config.DEMO_MODE else 'gemini',
                                   'configured': config.DEMO_MODE or config.is_configured(),
                                   'model': config.GEMINI_MODEL})
        if path == '/api/dashboard':
            return self.send_json({'dashboard': service.latest_dashboard()})
        file_name = path.lstrip('/') or 'index.html'
        target = (PUBLIC / file_name).resolve()
        if not target.is_relative_to(PUBLIC.resolve()) or not target.is_file():
            return self.send_error(404, 'Not found')
        body = target.read_bytes()
        mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
        self.send_response(200)
        self.send_header('Content-Type', mime + ('; charset=utf-8' if mime.startswith('text/') or mime == 'application/javascript' else ''))
        self.send_header('Content-Length', str(len(body)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlparse(self.path).path
        try:
            length = int(self.headers.get('Content-Length', '-1'))
            if length < 0 or length > MAX_BODY:
                return self.send_json({'error': 'Upload must be under 3 MB.'}, 413)
            blob = self.rfile.read(length)
            if path == '/api/upload':
                if not self.headers.get('Content-Type', '').startswith(('text/csv', 'application/vnd.ms-excel', 'application/octet-stream')):
                    return self.send_json({'error': 'Upload a CSV file.'}, 415)
                filename = self.headers.get('X-Filename', 'reviews.csv')
                result = service.import_csv(blob, filename)
                return self.send_json(result, 200)
            if path == '/api/reply':
                data = json.loads(blob)
                row_num = data.get('row_num')
                if type(row_num) is not int:
                    return self.send_json({'error': 'row_num must be an integer'}, 400)
                return self.send_json(service.generate_reply(row_num))
            return self.send_json({'error': 'Endpoint not found'}, 404)
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            return self.send_json({'error': str(exc)}, 400)
        except ProviderError as exc:
            return self.send_json({'error': str(exc)}, 503 if exc.retryable else 502)
        except Exception:
            self.log_exception()
            return self.send_json({'error': 'An unexpected server error occurred.'}, 500)

    def log_exception(self):
        import traceback
        traceback.print_exc()


def run():
    store.initialize()
    server = ThreadingHTTPServer(('127.0.0.1', config.PORT), Handler)
    print(f'ReviewLens running at http://localhost:{config.PORT}', flush=True)
    print('Mode:', 'OFFLINE PREVIEW (no AI)' if config.DEMO_MODE else 'Gemini LLM', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == '__main__':
    run()
