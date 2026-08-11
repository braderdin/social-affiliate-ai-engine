import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Muat turun tetapan dari .env.local
load_dotenv(dotenv_path=".env.local")

# Tambah laluan akar projek
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright_engine.supabase_db import save_links_to_supabase
from playwright_engine.link_pool_manager import add_links_to_pool
from src.redis_db import mark_product_posted

REDIS_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
REDIS_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()

class LinkReceiverHandler(BaseHTTPRequestHandler):
    
    def _set_cors_headers(self):
        """Membenarkan permintaan CORS daripada pelayar web Lazada."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Content-Type', 'application/json')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_cors_headers()

    def do_GET(self):
        """Respon positif apabila server diuji secara terus dari pelayar web."""
        self._set_cors_headers()
        response_data = {
            "status": "online",
            "message": "Server Receiver Aktif! Sedia menerima data POST daripada Microsoft Edge."
        }
        self.wfile.write(json.dumps(response_data).encode('utf-8'))

    def do_POST(self):
        if self.path == '/save':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                payload = json.loads(post_data.decode('utf-8'))
                items = payload.get("items", [])

                if not items:
                    self._set_cors_headers()
                    self.wfile.write(json.dumps({"success": False, "error": "Tiada item dihantar"}).encode('utf-8'))
                    return

                # 1. Simpan ke Upstash Redis
                redis_saved = 0
                for item in items:
                    p_id = str(item.get("product_id", "")).strip()
                    title = item.get("title", "")
                    if p_id and REDIS_URL and REDIS_TOKEN:
                        mark_product_posted(REDIS_URL, REDIS_TOKEN, p_id, title)
                        redis_saved += 1

                # 2. Simpan ke Supabase Cloud
                supa_ok, supa_count, supa_msg = save_links_to_supabase(items)

                # 3. Simpan ke Local JSON Pool (data/affiliate_link_pool.json)
                added_count, total_pool = add_links_to_pool(items)

                print(f"\n📥 [RECEIVER SUCCESS] Menerima {len(items)} pautan dari Microsoft Edge!")
                print(f"   • Upstash Redis : {redis_saved} item direkodkan")
                print(f"   • Supabase Cloud: {supa_msg}")
                print(f"   • Local JSON    : +{added_count} baharu (Jumlah Pool: {total_pool})")

                self._set_cors_headers()
                response_data = {
                    "success": True,
                    "saved_count": len(items),
                    "supabase_msg": supa_msg,
                    "pool_total": total_pool
                }
                self.wfile.write(json.dumps(response_data).encode('utf-8'))

            except Exception as e:
                print(f"❌ [RECEIVER ERROR] {str(e)}")
                self._set_cors_headers()
                self.wfile.write(json.dumps({"success": False, "error": str(e)}).encode('utf-8'))

def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, LinkReceiverHandler)
    print("\n" + "="*70)
    print(f"🚀 [SERVER RUNNING] Receiver Server aktif di http://127.0.0.1:{port}")
    print(" Sedia menerima pautan affiliate daripada Microsoft Edge!")
    print("="*70 + "\n")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()