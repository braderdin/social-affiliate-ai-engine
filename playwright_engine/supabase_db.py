import os
import requests

def get_supabase_config():
    """Membaca tetapan sambungan Supabase secara dinamik daripada persekitaran (env)."""
    supabase_url = os.getenv("SUPABASE_URL", "").strip() or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()
    service_role_key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip() or 
        os.getenv("SUPABASE_SECRET_KEY", "").strip() or 
        os.getenv("SUPABASE_ANON_KEY", "").strip()
    )

    if not supabase_url or not service_role_key:
        return None, None, "Kunci SUPABASE_URL atau SUPABASE_SERVICE_ROLE_KEY/ANON_KEY tidak lengkap dalam persekitaran (.env.local)."

    return supabase_url.rstrip("/"), service_role_key, ""

def save_links_to_supabase(link_items):
    """
    Memasukkan atau mengemas kini (UPSERT) senarai pautan affiliate ke dalam jadual 'affiliate_links' di Supabase Cloud.
    Memulangkan: (success_bool, saved_count, message)
    """
    supabase_url, api_key, err = get_supabase_config()
    if err:
        return False, 0, err

    if not link_items:
        return True, 0, "Tiada pautan untuk disimpan."

    endpoint = f"{supabase_url}/rest/v1/affiliate_links"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates, return=representation"
    }

    payload = []
    for item in link_items:
        product_id = str(item.get("product_id") or item.get("id") or "").strip()
        if not product_id:
            continue

        entry = {
            "product_id": product_id,
            "title": item.get("title", ""),
            "category": item.get("category", ""),
            "keyword": item.get("keyword", ""),
            "original_url": item.get("original_url", ""),
            "affiliate_link": item.get("affiliate_link", ""),
            "image_url": item.get("image_url", ""),
            "b2_image_url": item.get("b2_image_url", ""),
            "commission_rate": item.get("commission_rate", ">=20%"),
            "status_used": item.get("status_used", False)
        }
        payload.append(entry)

    if not payload:
        return False, 0, "Tiada rekod sah yang mempunyai product_id."

    try:
        res = requests.post(endpoint, json=payload, headers=headers, timeout=20)
        if res.status_code in [200, 201]:
            res_json = res.json()
            count = len(res_json) if isinstance(res_json, list) else len(payload)
            return True, count, f"Berjaya simpan (UPSERT) {count} pautan ke Supabase Cloud."
        else:
            return False, 0, f"Supabase REST API Error (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return False, 0, f"Ralat rangkaian Supabase: {str(e)}"

def fetch_unused_links(limit=10):
    """
    Membaca pautan affiliate yang belum digunakan (status_used = false) daripada Supabase.
    Memulangkan: (success_bool, records_list, message)
    """
    supabase_url, api_key, err = get_supabase_config()
    if err:
        return False, [], err

    endpoint = f"{supabase_url}/rest/v1/affiliate_links?status_used=eq.false&order=created_at.asc&limit={limit}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        res = requests.get(endpoint, headers=headers, timeout=15)
        if res.status_code == 200:
            records = res.json()
            return True, records if isinstance(records, list) else [], ""
        else:
            return False, [], f"Supabase Fetch Error (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return False, [], f"Ralat sambungan Supabase: {str(e)}"

def mark_link_as_used(product_id):
    """
    Menandakan status_used = true untuk product_id tertentu di Supabase selepas berjaya dipos ke media sosial.
    Memulangkan: (success_bool, message)
    """
    supabase_url, api_key, err = get_supabase_config()
    if err:
        return False, err

    clean_id = str(product_id).strip()
    if not clean_id:
        return False, "Product ID tidak sah."

    endpoint = f"{supabase_url}/rest/v1/affiliate_links?product_id=eq.{clean_id}"
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }
    payload = {"status_used": True}

    try:
        res = requests.patch(endpoint, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            return True, f"Product ID {clean_id} berjaya ditanda status_used=true di Supabase."
        else:
            return False, f"Supabase Update Error (HTTP {res.status_code}): {res.text}"
    except Exception as e:
        return False, f"Ralat sambungan Supabase: {str(e)}"