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

    def test_rejects_excessively_wide_csv_record_before_parsing(self) -> None:
        pathological_row = b"," * app.MAX_DATAFRAME_COLUMNS
        uploaded = UploadedFile(b"column\n" + pathological_row + b"\n", "data.csv")

        with mock.patch.object(app.pd, "read_csv") as read_csv:
            with self.assertRaisesRegex(ValueError, "500-column"):
                app.load_dataframe(uploaded)

        read_csv.assert_not_called()

    def test_csv_width_check_allows_delimiters_and_newlines_in_quotes(self) -> None:
        uploaded = UploadedFile(
            b'first,second\n"value, across\nlines",ok\n',
            "data.csv",
        )

        app.validate_csv_structure(uploaded)

        self.assertEqual(uploaded.tell(), 0)

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


if __name__ == "__main__":
    unittest.main()
