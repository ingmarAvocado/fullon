from PIL import Image, ImageEnhance, ImageFilter
import pytesseract

def preprocess_image(image_path):
    img = Image.open(image_path)
    img = img.convert('L')  # Convert to grayscale
    img = img.resize((img.width * 2, img.height * 2))  # Resize to double the original size
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(3)  # Increase contrast
    img = img.filter(ImageFilter.SHARPEN)  # Sharpen the image
    return img

image_path = 'test1.jpg'
preprocessed_img = preprocess_image(image_path)
preprocessed_img.show()  # Show the preprocessed image

ocr_text = pytesseract.image_to_string(preprocessed_img)
print(ocr_text)
