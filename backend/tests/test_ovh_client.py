"""
Unit Tests for OVHClient

Tests OVH AI Endpoints integration for medical text processing and vision OCR.
Mocks HTTP calls to avoid actual API requests during testing.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from io import BytesIO
from PIL import Image

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.ovh_client import OVHClient


class TestOVHClientInitialization:
    """Test suite for OVHClient initialization"""

    def test_initialization_with_token(self):
        """Test client initializes with access token"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            client = OVHClient()

            assert client is not None
            assert client.client is not None
            assert client.vision_client is not None

    def test_initialization_without_token(self):
        """Test client initialization without token logs warning and uses dummy key"""
        with patch('app.services.ovh_client.settings') as mock_settings:
            # Mock settings to return empty token
            mock_settings.ovh_api_token = ""
            mock_settings.ovh_ai_base_url = "https://test.com/v1"
            mock_settings.ovh_main_model = "test-main"
            mock_settings.ovh_preprocessing_model = "test-prep"
            mock_settings.ovh_translation_model = "test-trans"
            mock_settings.ovh_vision_model = "test-vision"
            mock_settings.ovh_vision_base_url = "https://test-vision.com"
            mock_settings.ai_timeout_seconds = 120
            mock_settings.use_ovh_only = True

            client = OVHClient()
            # Client should be created but with empty access_token
            assert client is not None
            assert client.client is not None
            # access_token will be empty string when not set
            assert client.access_token == ""

    def test_initialization_custom_models(self):
        """Test client initialization with custom model configuration"""
        with patch.dict(os.environ, {
            'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token',
            'OVH_MAIN_MODEL': 'custom-main-model',
            'OVH_PREPROCESSING_MODEL': 'custom-preprocessing-model',
            'OVH_VISION_MODEL': 'custom-vision-model'
        }):
            client = OVHClient()

            assert client is not None
            # Models are configured in client


class TestConnectionCheck:
    """Test suite for connection checking"""

    @pytest.fixture
    def client(self):
        """Create client instance for testing"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            return OVHClient()

    @pytest.mark.asyncio
    async def test_check_connection_success(self, client):
        """Test successful connection check"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Hello from OVH AI!"))]

        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
            success, message = await client.check_connection()

            assert success is True
            assert "successful" in message.lower()

    @pytest.mark.asyncio
    async def test_check_connection_failure(self, client):
        """Test connection check handles failures gracefully"""
        with patch.object(client.client.chat.completions, 'create', side_effect=Exception("Connection failed")):
            success, message = await client.check_connection()

            assert success is False
            assert len(message) > 0  # Should have error message

    @pytest.mark.asyncio
    async def test_check_connection_no_response(self, client):
        """Test connection check with empty response"""
        mock_response = Mock()
        mock_response.choices = []

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            success, message = await client.check_connection()

            assert success is False
            assert len(message) > 0  # Should have error message


class TestMedicalTextProcessing:
    """Test suite for medical text processing"""

    @pytest.fixture
    def client(self):
        """Create client instance for testing"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            return OVHClient()

    @pytest.mark.asyncio
    async def test_process_medical_text_success(self, client):
        """Test successful medical text processing"""
        full_prompt = "Classify this medical document: Patient has diabetes mellitus type 2"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="DIAGNOSIS: Diabetes Type 2"))]
        mock_response.usage = Mock(prompt_tokens=50, completion_tokens=20, total_tokens=70)

        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
            result = await client.process_medical_text_with_prompt(
                full_prompt=full_prompt
            )

            assert result is not None
            assert isinstance(result, dict)
            assert "text" in result
            assert "Diabetes Type 2" in result["text"]
            assert result["total_tokens"] == 70

    @pytest.mark.asyncio
    async def test_process_medical_text_with_variables(self, client):
        """Test medical text processing with full prompt"""
        full_prompt = "Translate to English: Patient text"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Translated text"))]
        mock_response.usage = Mock(prompt_tokens=30, completion_tokens=15, total_tokens=45)

        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response) as mock_create:
            result = await client.process_medical_text_with_prompt(
                full_prompt=full_prompt
            )

            assert isinstance(result, dict)
            assert "Translated text" in result["text"]
            # Check that the prompt was sent to API
            call_args = mock_create.call_args
            messages = call_args.kwargs['messages']
            assert any('English' in str(msg) for msg in messages)

    @pytest.mark.asyncio
    async def test_process_medical_text_temperature(self, client):
        """Test medical text processing respects temperature setting"""
        full_prompt = "Analyze: Text"
        temperature = 0.5

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Result"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = await client.process_medical_text_with_prompt(
                full_prompt=full_prompt,
                temperature=temperature
            )

            # Verify temperature was passed
            assert mock_create.call_args.kwargs['temperature'] == 0.5
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_medical_text_max_tokens(self, client):
        """Test medical text processing respects max_tokens limit"""
        full_prompt = "Summarize: Long medical text"
        max_tokens = 1000

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Summary"))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response) as mock_create:
            result = await client.process_medical_text_with_prompt(
                full_prompt=full_prompt,
                max_tokens=max_tokens
            )

            # Verify max_tokens was passed
            assert mock_create.call_args.kwargs['max_tokens'] == 1000
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_process_medical_text_api_error(self, client):
        """Test medical text processing handles API errors"""
        with patch.object(client.client.chat.completions, 'create', side_effect=Exception("API Error")):
            result = await client.process_medical_text_with_prompt(
                full_prompt="Test: Text"
            )

            assert isinstance(result, dict)
            assert "Error" in result["text"]

    @pytest.mark.asyncio
    async def test_process_medical_text_empty_response(self, client):
        """Test medical text processing handles empty responses"""
        mock_response = Mock()
        mock_response.choices = []

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            result = await client.process_medical_text_with_prompt(
                full_prompt="Test: Text"
            )

            assert isinstance(result, dict)
            assert "Error" in result["text"] or "error" in result["text"].lower()


class TestVisionOCR:
    """Test suite for vision-based OCR extraction"""

    @pytest.fixture
    def client(self):
        """Create client instance for testing"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            return OVHClient()

    @pytest.fixture
    def test_image(self):
        """Create a test PIL image"""
        return Image.new('RGB', (100, 100), color='white')

    @pytest.mark.asyncio
    async def test_extract_text_with_vision_success(self, client, test_image):
        """Test successful vision OCR extraction"""
        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": "Extracted medical text from image"}}]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            text, confidence = await client.extract_text_with_vision(test_image, "image")

            assert "medical text" in text.lower()
            assert confidence > 0.0
            assert confidence <= 1.0

    @pytest.mark.asyncio
    async def test_extract_text_with_vision_pdf_type(self, client, test_image):
        """Test vision OCR with PDF file type"""
        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": "PDF content extracted"}}]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            text, confidence = await client.extract_text_with_vision(test_image, "pdf")

            assert len(text) > 0
            assert confidence > 0.0

    @pytest.mark.asyncio
    async def test_extract_text_with_vision_error_handling(self, client, test_image):
        """Test vision OCR error handling"""
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Vision API Error"))
            mock_client_class.return_value = mock_client

            text, confidence = await client.extract_text_with_vision(test_image, "image")

            assert "Error" in text or "Fehler" in text or "error" in text.lower()
            assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_extract_text_with_vision_empty_response(self, client, test_image):
        """Test vision OCR with empty API response"""
        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "choices": []  # Empty response
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            text, confidence = await client.extract_text_with_vision(test_image, "image")

            # Empty response returns error message with calculated confidence (not 0.0)
            assert "Unerwartetes Antwortformat" in text
            assert confidence > 0.0  # Calculated based on error message text quality
            assert confidence <= 1.0

    @pytest.mark.asyncio
    async def test_process_multiple_images_ocr_success(self, client, test_image):
        """Test processing multiple images successfully"""
        images = [test_image, test_image, test_image]

        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": "Combined text from all pages"}}]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            text, confidence = await client.process_multiple_images_ocr(images)

            assert len(text) > 0
            assert confidence > 0.0

    @pytest.mark.asyncio
    async def test_process_multiple_images_empty_list(self, client):
        """Test processing empty image list"""
        text, confidence = await client.process_multiple_images_ocr([])

        assert "No images" in text or "no images" in text.lower() or len(text) == 0
        assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_process_multiple_images_merge_strategies(self, client, test_image):
        """Test different merge strategies for multiple images"""
        images = [test_image, test_image]

        mock_http_response = Mock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = {
            "choices": [{"message": {"content": "Page text"}}]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_http_response)
            mock_client_class.return_value = mock_client

            # Test smart merge
            text_smart, conf_smart = await client.process_multiple_images_ocr(images, merge_strategy="smart")
            assert len(text_smart) > 0

            # Test sequential merge
            text_seq, conf_seq = await client.process_multiple_images_ocr(images, merge_strategy="sequential")
            assert len(text_seq) > 0


class TestLanguageTranslation:
    """Test suite for language translation"""

    @pytest.fixture
    def client(self):
        """Create client instance for testing"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            return OVHClient()

    @pytest.mark.asyncio
    async def test_translate_to_english(self, client):
        """Test translation to English"""
        german_text = "Der Patient hat Diabetes mellitus Typ 2"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="The patient has diabetes mellitus type 2"))]
        mock_response.usage = Mock(prompt_tokens=30, completion_tokens=20, total_tokens=50)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            translated, confidence = await client.translate_to_language(german_text, "EN")

            assert isinstance(translated, str)
            assert isinstance(confidence, float)
            assert "patient" in translated.lower()
            assert "diabetes" in translated.lower()
            assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_translate_to_french(self, client):
        """Test translation to French"""
        german_text = "Laborwerte normal"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Valeurs de laboratoire normales"))]
        mock_response.usage = Mock(prompt_tokens=20, completion_tokens=15, total_tokens=35)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            translated, confidence = await client.translate_to_language(german_text, "FR")

            assert isinstance(translated, str)
            assert isinstance(confidence, float)
            assert "laboratoire" in translated.lower() or "normal" in translated.lower()
            assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_translate_unsupported_language(self, client):
        """Test translation handles unsupported languages gracefully"""
        text = "Test text"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Translated text"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            # Should still attempt translation even for unusual codes
            translated, confidence = await client.translate_to_language(text, "XX")

            assert isinstance(translated, str)
            assert len(translated) > 0
            assert isinstance(confidence, float)

    @pytest.mark.asyncio
    async def test_translate_error_handling(self, client):
        """Test translation error handling - returns original text with 0.0 confidence"""
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, side_effect=Exception("Translation API Error")):
            translated, confidence = await client.translate_to_language("Text", "EN")

            assert isinstance(translated, str)
            # On error, returns original text as fallback
            assert translated == "Text"
            assert confidence == 0.0

    @pytest.mark.asyncio
    async def test_translate_preserves_medical_terms(self, client):
        """Test translation preserves medical terminology"""
        text = "HbA1c: 8.2%, Metformin 1000mg"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="HbA1c: 8.2%, Metformin 1000mg (preserved)"))]
        mock_response.usage = Mock(prompt_tokens=40, completion_tokens=25, total_tokens=65)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            translated, confidence = await client.translate_to_language(text, "EN")

            # Medical terms and values should be preserved
            assert isinstance(translated, str)
            assert "HbA1c" in translated or "hba1c" in translated.lower()
            assert "8.2" in translated
            assert "Metformin" in translated or "metformin" in translated.lower()
            assert "1000mg" in translated or "1000" in translated
            assert isinstance(confidence, float)


class TestTokenUsageTracking:
    """Test suite for token usage tracking"""

    @pytest.fixture
    def client(self):
        """Create client instance for testing"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            return OVHClient()

    @pytest.mark.asyncio
    async def test_token_usage_tracked(self, client):
        """Test that token usage is tracked correctly"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Response"))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50, total_tokens=150)

        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
            result = await client.process_medical_text_with_prompt(
                full_prompt="Test: Text"
            )

            # Token tracking happens internally - verify result contains token info
            assert isinstance(result, dict)
            assert result["total_tokens"] == 150

    @pytest.mark.asyncio
    async def test_vision_token_usage_tracked(self, client):
        """Test that vision API token usage is tracked"""
        test_image = Image.new('RGB', (100, 100), color='white')

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="OCR text"))]
        mock_response.usage = Mock(prompt_tokens=1000, completion_tokens=200, total_tokens=1200)

        with patch.object(client.vision_client.chat.completions, 'create', return_value=mock_response):
            await client.extract_text_with_vision(test_image, "image")

            # Token tracking happens internally - verify no errors


class TestEdgeCases:
    """Test suite for edge cases and error conditions"""

    @pytest.fixture
    def client(self):
        """Create client instance for testing"""
        with patch.dict(os.environ, {'OVH_AI_ENDPOINTS_ACCESS_TOKEN': 'test-token'}):
            return OVHClient()

    @pytest.mark.asyncio
    async def test_empty_input_text(self, client):
        """Test processing empty input text"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=""))]
        mock_response.usage = Mock(prompt_tokens=5, completion_tokens=0, total_tokens=5)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            result = await client.process_medical_text_with_prompt(
                full_prompt="Test: "
            )

            # Should handle gracefully
            assert result is not None
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_very_long_input_text(self, client):
        """Test processing very long input text"""
        long_text = "Medical text " * 10000  # Very long text

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Processed"))]
        mock_response.usage = Mock(prompt_tokens=50000, completion_tokens=100, total_tokens=50100)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            result = await client.process_medical_text_with_prompt(
                full_prompt=f"Summarize: {long_text}"
            )

            assert result is not None
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_special_characters_in_text(self, client):
        """Test processing text with special characters"""
        special_text = "Patient: Müller, Über, €100, 50% increase, CO₂"

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Processed special chars"))]
        mock_response.usage = Mock(prompt_tokens=30, completion_tokens=10, total_tokens=40)

        with patch.object(client.client.chat.completions, 'create', return_value=mock_response):
            result = await client.process_medical_text_with_prompt(
                full_prompt=f"Analyze: {special_text}"
            )

            assert result is not None
            assert isinstance(result, dict)


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
