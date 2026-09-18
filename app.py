import io
import streamlit as st
from PIL import Image
import pillow_heif

# Enable HEIC / HEIF support
pillow_heif.register_heif_opener()


# --------------------------------------------------
# Settings
# --------------------------------------------------

SUPPORTED_EXTENSIONS = [
    "heic",
    "heif",
    "png",
    "jpeg",
    "jpg",
    "webp",
    "bmp",
    "tiff",
]

MAX_FILE_SIZE_KB = 100

# Start with high quality
START_QUALITY = 95

# Minimum quality allowed before giving up
MIN_QUALITY = 60

# Reduce width and height by 10% each round
DIMENSION_SCALE = 0.90

# Don't reduce the image below this dimension
MIN_WIDTH = 200
MIN_HEIGHT = 200


# --------------------------------------------------
# Compress image to below target size
# --------------------------------------------------

def compress_to_target_size(img):
    """
    Compress an image to below MAX_FILE_SIZE_KB.

    Compression priority:
    1. Keep JPEG quality at 95.
    2. Reduce image dimensions first.
    3. Continue reducing dimensions until the file is < 100 KB.
    4. If dimensions reach the minimum, start reducing JPEG quality.
    5. Return JPG bytes and compression details.
    """

    target_size = MAX_FILE_SIZE_KB * 1024

    # JPEG requires RGB
    img = img.convert("RGB")

    # Start with original image
    current_img = img.copy()

    quality = START_QUALITY

    # --------------------------------------------------
    # STEP 1:
    # Reduce dimensions first
    # --------------------------------------------------

    while True:

        output = io.BytesIO()

        current_img.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True
        )

        jpg_bytes = output.getvalue()

        # File is already below target
        if len(jpg_bytes) < target_size:

            return (
                jpg_bytes,
                len(jpg_bytes),
                current_img.width,
                current_img.height,
                quality
            )

        # Calculate next dimensions
        new_width = int(current_img.width * DIMENSION_SCALE)
        new_height = int(current_img.height * DIMENSION_SCALE)

        # Stop dimension reduction when minimum is reached
        if new_width < MIN_WIDTH or new_height < MIN_HEIGHT:
            break

        # Reduce dimensions while preserving aspect ratio
        current_img = current_img.resize(
            (new_width, new_height),
            Image.Resampling.LANCZOS
        )

    # --------------------------------------------------
    # STEP 2:
    # Dimensions are already reduced enough.
    # Now reduce JPEG quality.
    # --------------------------------------------------

    quality = START_QUALITY

    while quality >= MIN_QUALITY:

        output = io.BytesIO()

        current_img.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True
        )

        jpg_bytes = output.getvalue()

        if len(jpg_bytes) < target_size:

            return (
                jpg_bytes,
                len(jpg_bytes),
                current_img.width,
                current_img.height,
                quality
            )

        # Reduce quality gradually
        quality -= 5

    # --------------------------------------------------
    # Could not reach target
    # --------------------------------------------------

    return None


# --------------------------------------------------
# Convert image to JPG
# --------------------------------------------------

def convert_to_jpg(uploaded_file):
    """
    Convert uploaded image to JPG and compress it
    to below 100 KB.
    """

    with Image.open(uploaded_file) as img:

        result = compress_to_target_size(img)

        if result is None:
            raise ValueError(
                f"Could not compress the image below "
                f"{MAX_FILE_SIZE_KB} KB."
            )

        return result


# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------

st.set_page_config(
    page_title="Image to JPG Converter",
    page_icon="🖼️",
    layout="centered"
)

st.title("🖼️ Image to JPG Converter")

st.write(
    "Upload one or more images and convert them to JPG "
    "files smaller than 100 KB."
)

uploaded_files = st.file_uploader(
    "Choose images",
    type=SUPPORTED_EXTENSIONS,
    accept_multiple_files=True
)


# --------------------------------------------------
# Process uploaded files
# --------------------------------------------------

if uploaded_files:

    st.write(
        f"**{len(uploaded_files)} file(s) selected**"
    )

    for uploaded_file in uploaded_files:

        filename = uploaded_file.name
        name = filename.rsplit(".", 1)[0]

        try:

            # Get original file size
            original_size_kb = (
                uploaded_file.size / 1024
            )

            (
                jpg_bytes,
                final_size_bytes,
                width,
                height,
                quality
            ) = convert_to_jpg(uploaded_file)

            final_size_kb = (
                final_size_bytes / 1024
            )

            st.success(
                f"✅ Converted: {filename} → {name}.jpg"
            )

            st.write(
                f"Original size: **{original_size_kb:.2f} KB**"
            )

            st.write(
                f"Final size: **{final_size_kb:.2f} KB**"
            )

            st.write(
                f"Final dimensions: "
                f"**{width} × {height} px**"
            )

            st.write(
                f"JPEG quality: **{quality}**"
            )

            st.download_button(
                label=f"⬇️ Download {name}.jpg",
                data=jpg_bytes,
                file_name=f"{name}.jpg",
                mime="image/jpeg",
                key=f"download_{filename}"
            )

        except Exception as e:

            st.error(
                f"❌ Failed to convert "
                f"{filename}: {str(e)}"
            )
