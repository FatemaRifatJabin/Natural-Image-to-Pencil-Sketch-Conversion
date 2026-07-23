from fastapi import FastAPI, UploadFile, File, Form
import cv2
import numpy as np

app = FastAPI()

@app.post("/convert")
async def convert_to_sketch(
    file: UploadFile = File(...),
    blur_kernel: int = Form(21),
    scale_factor: float = Form(256.0),
    contrast: float = Form(1.0),
    sketch_mode: str = Form("Classic Gray")
):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # ব্লার কার্নেল অবশ্যই বিজোড় হতে হবে
    if blur_kernel % 2 == 0:
        blur_kernel += 1

    if sketch_mode == "Color Pencil":
        # রঙিন পেন্সিল স্কেচ লজিক
        sketch, _ = cv2.pencilSketch(img, sigma_s=60, sigma_r=0.07, shade_factor=0.05)
    else:
        # ক্লাসিক পেন্সিল স্কেচ লজিক
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        inverted = 255 - gray
        blurred = cv2.GaussianBlur(inverted, (blur_kernel, blur_kernel), 0)
        sketch = cv2.divide(gray, 255 - blurred, scale=scale_factor)

    # কনট্রাস্ট অ্যাডজাস্টমেন্ট
    if contrast != 1.0:
        sketch = cv2.convertScaleAbs(sketch, alpha=contrast, beta=0)

    _, encoded_img = cv2.imencode(".png", sketch)
    return {"sketch_bytes": encoded_img.tobytes().hex()}
