import base64
import json
from api_call import parse_toc_from_image

image_path = "C:/Users/tjdrn/Desktop/team_project/My_Planit/Example/KakaoTalk_20260822_113708019_03.jpg"   # 본인 사진 경로로 수정!

with open(image_path, "rb") as f:
    img_base64 = base64.b64encode(f.read()).decode()

result = parse_toc_from_image(img_base64, media_type="image/jpeg")
print(json.dumps(result, indent=2, ensure_ascii=False))