import streamlit as st
import numpy as np
from PIL import Image, ExifTags
import io
import requests
from supabase import create_client

# ---------------------------------------------------------
# ১. ক্লাউড কনফিগারেশন (Cloud Credentials)
# ---------------------------------------------------------
# Render Backend API URL (এখানে URL বসানো হয়েছে)
RENDER_API_URL = "https://natural-image-to-pencil-sketch-conversion.onrender.com/convert"

# Supabase Credentials (আপনার Supabase Dashboard থেকে সংগৃহীত URL & Anon Key বসাবেন)
SUPABASE_URL = "https://zkrtqljygfvjlwhxakwq.supabase.co/rest/v1/"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InprcnRxbGp5Z2Z2amx3aHhha3dxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQ4MjQ2OTUsImV4cCI6MjEwMDQwMDY5NX0.h9Nr261YNi-FbbEckF-J6VVl_RjkD-MW5dychqr73nE"

# Supabase Client তৈরি
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    supabase = None

# ---------------------------------------------------------
# ২. পেজ কনফিগারেশন
# ---------------------------------------------------------
st.set_page_config(page_title="Pencil Sketch Converter", page_icon="✏️", layout="centered")

st.title("✏️ Natural Image to Pencil Sketch Converter")
st.write("Upload an image to store it in **Supabase Cloud** and process via **Render Cloud API**.")

# ---------------------------------------------------------
# ৩. ছবি সোজা করার ফাংশন (Image Orientation)
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
    except (AttributeError, KeyError, IndexError, ValueError):
        pass
        
    return image_pil

# ---------------------------------------------------------
# ৪. ফাইল আপলোড ও প্রসেসিং
# ---------------------------------------------------------
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # ফাইল পড়া ও ওরিয়েন্টেশন সোজা করা
    image = Image.open(uploaded_file)
    image = rotate_image_if_needed(image)
    
    # ছবি বাইটে রূপান্তর করা (API & Cloud Upload এর জন্য)
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    file_bytes = img_byte_arr.getvalue()
    file_name = uploaded_file.name

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        st.image(image, use_column_width=True)
        
    with col2:
        st.subheader("Pencil Sketch")
        if st.button("🚀 Convert via Cloud"):
            with st.spinner("Processing on Render Cloud Server & Syncing with Supabase..."):
                try:
                    # ১. Section 5: Supabase Cloud Storage-এ Original Image সেভ করা
                    if supabase:
                        try:
                            supabase.storage.from_("images").upload(f"inputs/{file_name}", file_bytes, {"x-upsert": "true"})
                        except Exception as e:
                            st.warning("Note: Original Image failed to upload to Supabase.")

                    # ২. Section 4: Render Cloud API-তে প্রসেসিং রিকোয়েস্ট পাঠানো (RENDER_API_URL ব্যবহার করা হয়েছে)
                    files = {"file": (file_name, file_bytes, "image/png")}
                    response = requests.post(RENDER_API_URL, files=files)
                    
                    if response.status_code == 200:
                        sketch_hex = response.json()["sketch_bytes"]
                        sketch_bytes = bytes.fromhex(sketch_hex)

                        # ৩. Section 5: Supabase Cloud Storage-এ Output Sketch Image সেভ করা
                        if supabase:
                            try:
                                supabase.storage.from_("images").upload(f"outputs/sketch_{file_name}", sketch_bytes, {"x-upsert": "true"})
                            except Exception as e:
                                pass

                        # ৪. আউটপুট স্কেচ ইমেজ ডিসপ্লে করা
                        st.image(sketch_bytes, use_column_width=True)
                        
                        # ডাউনলোড বাটন
                        st.download_button(
                            label="📥 Download Sketch",
                            data=sketch_bytes,
                            file_name=f"sketch_{file_name}",
                            mime="image/png"
                        )
                        st.success("Successfully Processed!")
                    else:
                        st.error("Render Server processing failed. Please check backend logs.")
                except Exception as e:
                    st.error(f"Error connecting to backend: {e}")
