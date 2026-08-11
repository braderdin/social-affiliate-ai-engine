import random
import requests

THEMED_IMAGE_POOLS = {
    "GARDEN": [
        "https://images.unsplash.com/photo-1585320806297-9794b3e4eeae?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1416879595882-3373a0480b5b?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1516253593875-bd7ba052fbc5?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1466692476868-aef1dfb1e735?auto=format&fit=crop&w=1080&q=80"
    ],
    "COFFEE_TEA": [
        "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1541167760496-1628856ab772?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1507133750040-4a8f5d07637f?auto=format&fit=crop&w=1080&q=80"
    ],
    "LIVING_ROOM": [
        "https://images.unsplash.com/photo-1513694203232-719a280e022f?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1583847268964-b28dc8f51f92?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=1080&q=80"
    ],
    "FOOD_SNACK": [
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1555507036-ab1f4038808a?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1476224203421-9ac39bcb3327?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1509722747041-616f39b57569?auto=format&fit=crop&w=1080&q=80"
    ],
    "NATURE_WINDOW": [
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1518895949257-7621c3c786d7?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1500382017468-9049fed747ef?auto=format&fit=crop&w=1080&q=80",
        "https://images.unsplash.com/photo-1513836279014-a89f7a76ae86?auto=format&fit=crop&w=1080&q=80"
    ]
}

def get_lifestyle_image_url(category="ALL"):
    category_key = str(category).upper()
    if category_key in THEMED_IMAGE_POOLS:
        pool = THEMED_IMAGE_POOLS[category_key]
    else:
        pool = [img for sublist in THEMED_IMAGE_POOLS.values() for img in sublist]

    random.shuffle(pool)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for img_url in pool:
        try:
            res = requests.head(img_url, headers=headers, timeout=5)
            if res.status_code == 200:
                return img_url
        except Exception:
            continue

    return "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=1080&q=80"