import streamlit as st
from PIL import Image, ExifTags
import io
import requests
from supabase import create_client

# ---------------------------------------------------------
# ১. ক্লাউড কনফিগারেশন
# ---------------------------------------------------------
RENDER_API_URL = "https://natural-image-to-pencil-sketch-conversion.onrender.com/convert"

# Supabase Credentials (সঠিক URL এবং Key)
SUPABASE_URL = "https://zkrtqljygfvjlwhxakwq.supabase.co"
SUPABASE_KEY = "sb_publishable_UpAp9JsR6W3q4NQ2pIpDxg_X7F0XMW3"

try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception:
    supabase = None

# ---------------------------------------------------------
# ২. পেজ কনফিগারেশন
# ---------------------------------------------------------
st.set_page_config(page_title="Pencil Sketch Converter", page_icon="🎨", layout="wide")

st.title("✏️ Natural Image to Pencil Sketch Converter")
st.write("Upload an image to convert it into a pencil sketch using Cloud Architecture!")

# ---------------------------------------------------------
# ৩. সাইডবার সেটিংস (Sidebar Options)
# ---------------------------------------------------------
st.sidebar.header("🎨 Sketch Settings")

sketch_mode = st.sidebar.selectbox(
    "Sketch Style",
    ["Classic Gray", "Color Pencil"]
)

blur_kernel = st.sidebar.slider(
    "Blur Intensity (Gaussian Kernel)", 
    min_value=3, max_value=51, value=25, step=2
)

scale_factor = st.sidebar.slider(
    "Sketch Brightness/Scale", 
    min_value=100.0, max_value=300.0, value=256.0, step=10.0
)

contrast = st.sidebar.slider(
    "Contrast / Darkening", 
    min_value=0.5, max_value=2.0, value=1.0, step=0.1
)

# ---------------------------------------------------------
# ৪. ছবি সোজা করার ফাংশন
# ---------------------------------------------------------
def rotate_image_if_needed(image_pil):
    try:
        if hasattr(image_pil, '_getexif'):
            exif = image_pil._getexif()
            if exif is not None:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = dict(exif.items())
                orientation_value = exif.get(orientation)
                
                if orientation_value == 3:
                    image_pil = image_pil.rotate(180, expand=True)
                elif orientation_value == 6:
                    image_pil = image_pil.rotate(270, expand=True)
                elif orientation_value == 8:
                    image_pil = image_pil.rotate(90, expand=True)
    except Exception:
        pass
    return image_pil

# ---------------------------------------------------------
# ৫. ফাইল আপলোড ও ডিসপ্লে
# ---------------------------------------------------------
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = rotate_image_if_needed(image)
    
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    file_bytes = img_byte_arr.getvalue()
    file_name = uploaded_file.name

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        st.image(image, use_container_width=True)
        
    with col2:
        st.subheader("Pencil Sketch")
        with st.spinner("Processing in Render Cloud Server..."):
            try:
                # Supabase Upload (Input Image)
                if supabase:
                            try:
                                supabase.storage.from_("images").upload(
                                f"inputs/{file_name}", 
                                file_bytes, 
                                {"x-upsert": "true", "content-type": "image/png"}
                                )
                            except Exception as e:
                                    pass

                # API Data Payload
                files = {"file": (file_name, file_bytes, "image/png")}
                data = {
                    "blur_kernel": blur_kernel,
                    "scale_factor": scale_factor,
                    "contrast": contrast,
                    "sketch_mode": sketch_mode
                }

                # Render Cloud API Request
                response = requests.post(RENDER_API_URL, files=files, data=data)
                
                if response.status_code == 200:
                    sketch_hex = response.json()["sketch_bytes"]
                    sketch_bytes = bytes.fromhex(sketch_hex)

                    # Supabase Upload (Output Image)
                    if supabase:
                                try:
                                    supabase.storage.from_("images").upload(
                                    f"outputs/sketch_{file_name}", 
                                    sketch_bytes, 
                                    {"x-upsert": "true", "content-type": "image/png"}
                                        )
                                except Exception as e:
                                    pass

                    # Display Output Sketch
                    st.image(sketch_bytes, use_container_width=True)
                    
                    st.download_button(
                        label="📥 Download Sketch",
                        data=sketch_bytes,
                        file_name=f"sketch_{file_name}",
                        mime="image/png"
                    )
                else:
                    st.error("Processing failed at Render API backend.")
            except Exception as e:
                st.error(f"Cloud connection error: {e}")
