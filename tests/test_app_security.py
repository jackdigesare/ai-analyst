import io
import json
import tomllib
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import app

ROOT = Path(__file__).resolve().parents[1]


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


class ServerConfigSafetyTests(unittest.TestCase):
    def test_browser_request_protections_are_enabled(self) -> None:
        with (ROOT / ".streamlit" / "config.toml").open("rb") as config_file:
            server_config = tomllib.load(config_file)["server"]

        self.assertIs(server_config["enableCORS"], True)
        self.assertIs(server_config["enableXsrfProtection"], True)

        devcontainer = json.loads(
            (ROOT / ".devcontainer" / "devcontainer.json").read_text()
        )
        attach_commands = devcontainer.get("postAttachCommand", {})
        commands = (
            attach_commands.values()
            if isinstance(attach_commands, dict)
            else [attach_commands]
        )
        for command in commands:
            self.assertNotIn("--server.enableCORS false", command)
            self.assertNotIn("--server.enableXsrfProtection false", command)


if __name__ == "__main__":
    unittest.main()
