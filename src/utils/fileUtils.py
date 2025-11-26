import json
import os

PATH = "src/temp/json/"
def save_json(data, name: str):
    # Tao folder neu chua ton tai
    os.makedirs(PATH, exist_ok=True)
        
    with open(PATH + name + ".json", "w", encoding="utf-8") as f:
        json.dump(
            data, f,
            ensure_ascii=False,  # giữ tiếng Việt
            indent=2             # format đẹp
        )

