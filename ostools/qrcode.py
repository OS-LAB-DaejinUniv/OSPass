## QR CODE ## 
from fastapi.responses import StreamingResponse
from fastapi import APIRouter, HTTPException
import io
import qrcode

from auth import get_or_issue_challenge

ostools_api = APIRouter(prefix="/api")

@ostools_api.get("/v1/qrcode")
async def generate_qr(user_session : str):
    
    # Challenge 획득
    challenge = get_or_issue_challenge(user_session)
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    # QR Data Format
    applink = f"https://smartlab.os-lab.dev?s={user_session}&c={challenge}"
    
    qr = qrcode.QRCode(
        version=10,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=4,
    )
    qr.add_data(applink)
    qr.make(fit=True)
    
    # QR CODE transformation to Image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Image trnasformation to Bytes Stream
    img_stream = io.BytesIO()
    img.save(img_stream, format="PNG")
    img_stream.seek(0)
    
    return StreamingResponse(img_stream, media_type="image/png")
