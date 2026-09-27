import binascii
import io
import struct
import unittest
import zipfile
from unittest import mock

import openpyxl

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

    def test_rejects_xlsx_with_forged_uncompressed_size(self) -> None:
        limit = 1024 * 1024
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "xl/worksheets/sheet1.xml",
                b"x" * (limit + app.XLSX_DECOMPRESSION_CHUNK_BYTES),
            )

        forged = bytearray(content.getvalue())
        local_header = forged.index(b"PK\x03\x04")
        central_header = forged.index(b"PK\x01\x02")
        struct.pack_into("<I", forged, local_header + 22, 1)
        struct.pack_into("<I", forged, central_header + 24, 1)
        observed_prefix_crc = binascii.crc32(b"x" * (limit + 1))
        struct.pack_into("<I", forged, local_header + 14, observed_prefix_crc)
        struct.pack_into("<I", forged, central_header + 16, observed_prefix_crc)
        uploaded = UploadedFile(bytes(forged), "data.xlsx")

        with mock.patch.object(app, "MAX_XLSX_UNCOMPRESSED_BYTES", limit):
            with self.assertRaisesRegex(ValueError, "expands beyond"):
                app.validate_xlsx_archive(uploaded)

    def test_rejects_inconsistent_xlsx_size_metadata(self) -> None:
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"x" * 100)

        forged = bytearray(content.getvalue())
        central_header = forged.index(b"PK\x01\x02")
        struct.pack_into("<I", forged, central_header + 24, 99)
        uploaded = UploadedFile(bytes(forged), "data.xlsx")

        with self.assertRaisesRegex(ValueError, "inconsistent ZIP size"):
            app.validate_xlsx_archive(uploaded)

    def test_rejects_unsafe_xlsx_compression_before_decompression(self) -> None:
        for compression in (zipfile.ZIP_BZIP2, zipfile.ZIP_LZMA):
            with self.subTest(compression=compression):
                content = io.BytesIO()
                with zipfile.ZipFile(content, "w", compression) as archive:
                    archive.writestr("xl/worksheets/sheet1.xml", b"x" * 100)
                uploaded = UploadedFile(content.getvalue(), "data.xlsx")

                with mock.patch.object(
                    zipfile.ZipFile,
                    "open",
                    side_effect=AssertionError("must reject before decompression"),
                ):
                    with self.assertRaisesRegex(ValueError, "compression method"):
                        app.validate_xlsx_archive(uploaded)

    def test_accepts_valid_xlsx(self) -> None:
        workbook = openpyxl.Workbook()
        worksheet = workbook.active
        worksheet.append(["name", "value"])
        worksheet.append(["safe", 1])
        content = io.BytesIO()
        workbook.save(content)
        uploaded = UploadedFile(content.getvalue(), "data.xlsx")

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
