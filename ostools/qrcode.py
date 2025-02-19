## QR CODE ## 
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, HTTPException
import io
import qrcode
import base64

from ospass.service.auth import get_or_issue_challenge

ostools_api = APIRouter(prefix="/api")

# 최초 인증 
# OSPASS로 로그인 -> QR 코드 이미지 -> 앱링크 -> 앱 실행 -> 인증
# user_session : 사용자 세션 키
@ostools_api.get("/v1/auth-init")
async def auth_init(user_session: str):
    try:
        # Challenge 생성
        challenge = get_or_issue_challenge(user_session)
        print(f"Challenge : {challenge}")
        if not challenge:
            raise HTTPException(status_code=404, detail="Challenge not found")

        # QR 코드에 인코딩할 데이터 (URL 형식)
        applink = f"https://smartlab.os-lab.dev?s={user_session}&c={challenge}"

        # QR 코드 이미지 생성
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(applink)
        qr.make(fit=True)

        # QR 코드를 PIL 이미지로 변환
        img = qr.make_image(fill_color="blue", back_color="white")
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")

        # 이미지 데이터를 Base64로 인코딩
        img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
        img_data_url = f"data:image/png;base64,{img_base64}"

        # Challenge와 QR 코드 Data URL 반환
        return {"challenge": challenge, "qr_code_data_url": img_data_url}

    except Exception as e:
        print(f"Error Occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

