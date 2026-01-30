import pytest
import io
from PIL import Image as PILImage


@pytest.mark.images
class TestImages:
    """Эндпоинты изображений"""
    
    def test_upload_image(self, client, created_hotel_ids, created_image_ids):
        """загрузки изображения для отеля"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        
        img = PILImage.new('RGB', (1200, 800), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_image.jpg', img_bytes.getvalue(), 'image/jpeg')}
        upload_response = client.post(f"/images/upload/{hotel_id}", files=files)
        
        assert upload_response.status_code == 200, \
            f"Ожидался статус 200, получен {upload_response.status_code}. Ответ: {upload_response.text[:500]}"
        upload_data = upload_response.json()
        assert upload_data["status"] == "OK"
        assert "image_id" in upload_data
        assert upload_data["image_id"] > 0
        created_image_ids.append(upload_data["image_id"])
    
    def test_upload_image_nonexistent_hotel(self, client):
        """загрузки изображения для несуществующего отеля"""
        img = PILImage.new('RGB', (1200, 800), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_image.jpg', img_bytes.getvalue(), 'image/jpeg')}
        upload_response = client.post("/images/upload/99999", files=files)
        assert upload_response.status_code == 404
    
    def test_upload_image_too_small(self, client, created_hotel_ids):
        """загрузки слишком маленького изображения"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        
        img = PILImage.new('RGB', (800, 600), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_image.jpg', img_bytes.getvalue(), 'image/jpeg')}
        upload_response = client.post(f"/images/upload/{hotel_id}", files=files)
        assert upload_response.status_code == 400
        assert "1000px" in upload_response.json()["detail"]
    
    def test_upload_image_not_image(self, client, created_hotel_ids):
        """загрузки файла, который не является изображением"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        
        text_file = io.BytesIO(b"This is not an image")
        files = {'file': ('test.txt', text_file.getvalue(), 'text/plain')}
        upload_response = client.post(f"/images/upload/{hotel_id}", files=files)
        assert upload_response.status_code == 400
        assert "изображением" in upload_response.json()["detail"]
    
    def test_get_hotel_images(self, client, created_hotel_ids, created_image_ids):
        """Получение изображений отеля"""
        if not created_hotel_ids:
            return
        
        hotel_id = created_hotel_ids[-1]
        
        img = PILImage.new('RGB', (1200, 800), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        files = {'file': ('test_get_image.jpg', img_bytes.getvalue(), 'image/jpeg')}
        upload_response = client.post(f"/images/upload/{hotel_id}", files=files)
        
        assert upload_response.status_code == 200, \
            f"Ожидался статус 200 при загрузке, получен {upload_response.status_code}. Ответ: {upload_response.text[:500]}"
        upload_data = upload_response.json()
        uploaded_image_id = upload_data["image_id"]
        created_image_ids.append(uploaded_image_id)
        
        response = client.get(f"/images/hotel/{hotel_id}")
        
        assert response.status_code == 200, \
            f"Ожидался статус 200 при получении, получен {response.status_code}. Ответ: {response.text[:500]}"
        images = response.json()
        assert isinstance(images, list)
        assert len(images) > 0
        
        image_ids = [img["id"] for img in images]
        assert uploaded_image_id in image_ids
        
        uploaded_img = next(img for img in images if img["id"] == uploaded_image_id)
        assert "filename" in uploaded_img
        assert "original_filename" in uploaded_img
        assert "width" in uploaded_img
        assert "height" in uploaded_img
        assert uploaded_img["width"] == 1200
        assert uploaded_img["height"] == 800

