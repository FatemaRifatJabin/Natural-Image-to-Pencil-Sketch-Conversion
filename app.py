import streamlit as st
import cv2
import numpy as np
from PIL import Image, ExifTags  # ExifTags অ্যাড করা হয়েছে
import io

# ১. পেজ কনফিগারেশন
st.set_page_config(page_title="Pencil Sketch Converter", page_icon="✏️", layout="centered")

st.title("✏️ Natural Image to Pencil Sketch Converter")
st.write("Upload an image to convert it into a pencil sketch.")

# --- ছবি সোজা করার জন্য প্রয়োজনীয় নতুন ফাংশন ---
def rotate_image_if_needed(image_pil):
    """
    ছবির EXIF ডাটা ব্যবহার করে ওরিয়েন্টেশন সঠিক করে।
    """
    try:
        # ছবির EXIF ডাটা খোঁজা
        if hasattr(image_pil, '_getexif'):
            exif = image_pil._getexif()
            if exif is not None:
                # ওরিয়েন্টেশন ট্যাগ খোঁজা
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                
                exif = dict(exif.items())
                orientation_value = exif.get(orientation)
                
                # ওরিয়েন্টেশন অনুযায়ী ছবি ঘোরানো
                if orientation_value == 3:
                    image_pil = image_pil.rotate(180, expand=True)
                elif orientation_value == 6:
                    image_pil = image_pil.rotate(270, expand=True)
                elif orientation_value == 8:
                    image_pil = image_pil.rotate(90, expand=True)
    except (AttributeError, KeyError, IndexError, ValueError):
        # EXIF ডাটা না থাকলে বা কোনো এরর হলে, ছবিটি যেমন আছে তেমনই থাকবে
        pass
        
    return image_pil
# ---------------------------------------------

# ২. মডিফাইড ইমেজ প্রসেসিং ফাংশন
def convert_to_sketch(image_np, blur_ksize, scale_val):
    # গ্রেস্কেল কনভার্সন
    # Pillow থেকে OpenCV-তে আসার সময় RGB থেকে BGR কনভার্ট করা লাগতে পারে
    img_bgr = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    # ইনভার্ট করা
    inverted = cv2.bitwise_not(gray)
    
    # গসিয়ান ব্লার (ব্লার সাইজ অবশ্যই বিজোড় সংখ্যা হতে হবে)
    # জিরো বা নেগেটিভ ভ্যালু যেন না হয় তার জন্য চেক
    blur_ksize = max(1, blur_ksize if blur_ksize % 2 != 0 else blur_ksize + 1)
    blurred = cv2.GaussianBlur(inverted, (blur_ksize, blur_ksize), sigmaX=0, sigmaY=0)
    
    # কালার ডজ ব্লেন্ডিং
    sketch = cv2.divide(gray, 255 - blurred, scale=scale_val)
    return sketch

# ৩. কন্ট্রোল স্লাইডার (ঐচ্ছিক, আপনার আগের কোড থেকে রাখা হয়েছে)
st.sidebar.header("🎨 Sketch Settings")
blur_kernel = st.sidebar.slider("Blur Intensity (Gaussian Kernel)", min_value=3, max_value=51, value=21, step=2)
scale_factor = st.sidebar.slider("Sketch Brightness/Scale", min_value=100.0, max_value=300.0, value=256.0, step=10.0)

# ৪. ফাইল আপলোড অপশন
uploaded_file = st.file_uploader("Choose an image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # ফাইল থেকে ছবি ওপেন করা (Pillow লাইব্রেরি দিয়ে)
    image = Image.open(uploaded_file)
    
    # --- ছবির ওরিয়েন্টেশন ঠিক করা (নতুন ধাপ) ---
    with st.spinner("Correcting image orientation..."):
        image = rotate_image_if_needed(image)
    # ----------------------------------------
    
    img_np = np.array(image)
    
    # ২ টি কলামে অরিজিনাল ও স্কেচ ছবি দেখানো
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        # ছবির ওরিয়েন্টেশন সোজা হওয়ার পর এটি দেখানো হবে
        st.image(image, width='stretch')
        
    with col2:
        st.subheader("Pencil Sketch")
        # প্রসেস করা
        with st.spinner("Processing image..."):
            sketch_result = convert_to_sketch(img_np, blur_kernel, scale_factor)
            st.image(sketch_result, width='stretch', channels="GRAY")
            
            # ডাউনলোড বাটন তৈরি (পূর্বের ন্যায়)
            result_pil = Image.fromarray(sketch_result)
            buf = io.BytesIO()
            result_pil.save(buf, format="PNG")
            byte_im = buf.getvalue()
            
            st.download_button(
                label="📥 Download Sketch",
                data=byte_im,
                file_name="pencil_sketch.png",
                mime="image/png"
            )