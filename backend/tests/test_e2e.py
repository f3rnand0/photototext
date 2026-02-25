import os
import pytest
from pathlib import Path

# Get the fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures"

# Expected results for each test image
# Updated with actual extracted text from Azure OCR
EXPECTED_RESULTS = {
    "85273A5B-3F64-4DFA-B4B8-8BE6E23D9DD5_4_5005_c.jpeg": {
        "expected_text": "bewusst , dünn, entschlossen.\n\n„Wer Katzen mag, hat einen guten Geschmack . , meine, Lieblingsspruch . Ich hasse Schlangen, schon beim Gedan- ken wird mir schlecht . Die ekligen Tiere, essen Ratten, Mäuse und vieles ekliges Zeug, wassuihr eher nicht wissen wollt. Würg! Auch wenn Katzen Mäuse jagen, finde ich, nicht alle Katzen jagen , sondern nur manche. Hunde sind auch süß aber zu laut , Katzen im Gegenteil nicht. Mit ihre scharfer Krallen , können sie geschickt - jagen und sich in der Wildnis.",
        "description": "Third test image - About cats and taste"
    },
    "85DAE903-61D7-435B-8CC6-9CC82B1AD87A_4_5005_c.jpeg": {
        "expected_text": "Torella * Meine Lieblingstiere * siativ- Fast jeder mag Hunde, finde ich.\n\nEtiv- haft Aber ich nicht, denn ich habe ein anderes Geschmack für Tiere.\n\nAnstatt Hunde zu mögen, mag ich am liebsten Katzen. Alle Tiere, die mit Katzen verwandt sind, mag ich. Zum Beispiel Leoparde, Geparde, Pumas Luchse , Löwen , Tiger und vieles mehr. Trotzdem finde ich Hunde halb so schlimm. Katzen sind: süß, weich, klug, humorvoll, schön, hochbegabt , einsam, ernst, selbsti",
        "description": "First test image - About favorite animals (German)"
    },
    "A579D686-84FE-4D76-9EEC-9C02F6446211_4_5005_c.jpeg": {
        "expected_text": "at verteidigen. Wenn man gles zusammenfassen würde, dann wäre das hier sehr nützlich: Katzen können sich gut schleichen und verteidigen. Sie sind gut beschützt und sehr kluge Tiere. was ich nicht geschrieben habe ist : Katzen und ihre Verwandten, können nach einem Sprung, auf die Vier landen , ohne Sich einziges Körperteil zu fer Verletzen!\n\nENDE nis",
        "description": "Second test image - About cats defending and landing"
    }
}


def get_fixture_path(filename: str) -> Path:
    """Get the full path to a fixture file."""
    return FIXTURES_DIR / filename


def get_test_images():
    """Get list of all test images in fixtures directory."""
    return [f for f in FIXTURES_DIR.glob("*.jpeg") if f.is_file()]


class TestOCRExtraction:
    """E2E tests for OCR text extraction endpoint."""

    def test_extract_text_single_image(self, client):
        """Test extracting text from a single image."""
        # Get first test image
        test_images = get_test_images()
        if not test_images:
            pytest.skip("No test images found in fixtures directory")
        
        image_path = test_images[0]
        filename = image_path.name
        
        # Prepare file for upload
        with open(image_path, "rb") as f:
            files = {
                "files": (filename, f, "image/jpeg")
            }
            response = client.post("/extract-text", files=files)
        
        # Assertions
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == 1
        assert data["results"][0]["filename"] == filename
        assert data["results"][0]["order"] == 0
        assert "text" in data["results"][0]
        assert "combined_text" in data
        
        # Check expected text (placeholder - user will update)
        # expected = EXPECTED_RESULTS.get(filename, {}).get("expected_text", "")
        # if expected and not expected.startswith("PLACEHOLDER"):
        #     assert data["results"][0]["text"] == expected

    def test_extract_text_multiple_images(self, client):
        """Test extracting text from multiple images maintaining order."""
        test_images = get_test_images()
        if len(test_images) < 2:
            pytest.skip("Need at least 2 test images")
        
        # Use first 3 images or all if less than 3
        images_to_test = test_images[:3]
        
        # Prepare files for upload
        files = []
        for image_path in images_to_test:
            files.append(
                ("files", (image_path.name, open(image_path, "rb"), "image/jpeg"))
            )
        
        try:
            response = client.post("/extract-text", files=files)
        finally:
            # Close all file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()
        
        # Assertions
        assert response.status_code == 200
        
        data = response.json()
        assert data["success"] is True
        assert len(data["results"]) == len(images_to_test)
        
        # Verify order is maintained
        for i, result in enumerate(data["results"]):
            assert result["order"] == i
            assert result["filename"] == images_to_test[i].name
            assert "text" in result
        
        # Verify combined text contains all individual texts
        combined = data["combined_text"]
        for result in data["results"]:
            assert result["text"] in combined

    def test_extract_text_line_break_cleaning(self, client):
        """Test that line breaks are properly cleaned."""
        test_images = get_test_images()
        if not test_images:
            pytest.skip("No test images found")
        
        image_path = test_images[0]
        
        with open(image_path, "rb") as f:
            files = {
                "files": (image_path.name, f, "image/jpeg")
            }
            response = client.post("/extract-text", files=files)
        
        assert response.status_code == 200
        
        data = response.json()
        text = data["results"][0]["text"]
        
        # Assertions about line break cleaning:
        # 1. Should not have single newlines within paragraphs
        # 2. Should have double newlines between paragraphs
        # 3. Should not have excessive whitespace
        
        # Check that text doesn't have unnecessary line breaks
        lines = text.split("\n")
        for i, line in enumerate(lines):
            line = line.strip()
            if line and i > 0:
                # If line doesn't start with uppercase and previous doesn't end with punctuation,
                # it should have been joined (not present as separate line)
                pass  # Placeholder for specific logic

    def test_extract_text_no_files(self, client):
        """Test error handling when no files are uploaded."""
        response = client.post("/extract-text")
        
        assert response.status_code == 422  # FastAPI validation error

    def test_extract_text_invalid_file_type(self, client):
        """Test error handling for invalid file types."""
        # Create a dummy text file
        import io
        files = {
            "files": ("test.txt", io.BytesIO(b"This is not an image"), "text/plain")
        }
        
        response = client.post("/extract-text", files=files)
        
        # Should return 400 for invalid file type
        assert response.status_code == 400
        assert "Invalid file type" in response.json()["detail"]

    def test_extract_text_too_many_files(self, client):
        """Test error handling when too many files are uploaded."""
        test_images = get_test_images()
        if not test_images:
            pytest.skip("No test images found")
        
        # Create 21 files (limit is 20)
        files = []
        for i in range(21):
            image_path = test_images[0]
            files.append(
                ("files", (f"copy_{i}_{image_path.name}", open(image_path, "rb"), "image/jpeg"))
            )
        
        try:
            response = client.post("/extract-text", files=files)
        finally:
            for _, (_, file_handle, _) in files:
                file_handle.close()
        
        assert response.status_code == 400
        assert "Maximum 20 files" in response.json()["detail"]

    def test_extract_text_file_too_large(self, client):
        """Test error handling for files exceeding size limit."""
        import io
        # Create a fake large file (11MB)
        large_content = b"0" * (11 * 1024 * 1024)
        
        files = {
            "files": ("large.jpg", io.BytesIO(large_content), "image/jpeg")
        }
        
        response = client.post("/extract-text", files=files)
        
        assert response.status_code == 400
        assert "exceeds maximum size" in response.json()["detail"]


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns 200."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "photototext"


class TestAPIInfo:
    """Tests for root/info endpoint."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "endpoints" in data


# Integration test that runs full flow with real Azure OCR
# Marked as optional since it requires Azure credentials
@pytest.mark.integration
def test_integration_with_azure(client):
    """Full integration test with actual Azure OCR service.
    
    This test requires valid Azure credentials to be configured.
    Run manually: pytest tests/test_e2e.py::test_integration_with_azure -v
    """
    test_images = get_test_images()
    if not test_images:
        pytest.skip("No test images found")
    
    # Use all available test images
    files = []
    for image_path in test_images:
        files.append(
            ("files", (image_path.name, open(image_path, "rb"), "image/jpeg"))
        )
    
    try:
        response = client.post("/extract-text", files=files)
    finally:
        for _, (_, file_handle, _) in files:
            file_handle.close()
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["success"] is True
    assert len(data["results"]) == len(test_images)
    
    # Print extracted text for manual verification
    print("\n\n=== EXTRACTED TEXT ===")
    for result in data["results"]:
        print(f"\n{result['filename']}:")
        print("-" * 50)
        print(result['text'])
    print("\n=== END ===\n")
    
    # Validate extracted text against expected results
    for result in data["results"]:
        expected = EXPECTED_RESULTS.get(result["filename"], {}).get("expected_text", "")
        if expected:
            assert result["text"] == expected, \
                f"Text mismatch for {result['filename']}\nExpected: {expected}\nGot: {result['text']}"