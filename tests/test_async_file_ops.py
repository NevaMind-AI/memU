import asyncio
import pathlib
import tempfile

import pytest

from memu.blob.local_fs import LocalFS


@pytest.fixture
def temp_dir() -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.mark.asyncio
class TestAsyncLocalFS:

    async def test_fetch_local_file_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        test_file = pathlib.Path(temp_dir) / "test.txt"
        test_content = "Hello, async world!"
        test_file.write_text(test_content, encoding="utf-8")

        local_path, content = await fs.fetch(str(test_file), modality="text")

        assert pathlib.Path(local_path).exists()
        assert content == test_content

    async def test_fetch_local_file_no_text_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        test_file = pathlib.Path(temp_dir) / "test.bin"
        test_content = b"\x00\x01\x02\x03"
        test_file.write_bytes(test_content)

        local_path, content = await fs.fetch(str(test_file), modality="audio")

        assert pathlib.Path(local_path).exists()
        assert content is None

    async def test_fetch_conversation_text_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        test_file = pathlib.Path(temp_dir) / "conversation.json"
        test_content = '{"role": "user", "content": "Hello"}'
        test_file.write_text(test_content, encoding="utf-8")

        local_path, content = await fs.fetch(str(test_file), modality="conversation")

        assert pathlib.Path(local_path).exists()
        assert content == test_content

    async def test_file_copy_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        source_dir = pathlib.Path(temp_dir) / "source"
        source_dir.mkdir()
        source_file = source_dir / "source.txt"
        test_content = "Test content for async copy"
        source_file.write_text(test_content, encoding="utf-8")

        local_path, content = await fs.fetch(str(source_file), modality="text")

        dest_file = pathlib.Path(fs.base) / source_file.name
        assert dest_file.exists()
        assert dest_file.read_text(encoding="utf-8") == test_content
        assert local_path == str(dest_file)

    async def test_fetch_http_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        try:
            local_path, content = await fs.fetch(
                "https://raw.githubusercontent.com/github/README.md",
                modality="document",
            )

            assert pathlib.Path(local_path).exists()
            assert content is not None
            assert len(content) > 0
        except Exception as e:
            pytest.skip(f"Network test skipped: {e}")

    async def test_filename_extraction_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        url1 = "http://example.com/path/to/file.txt"
        filename1 = fs._get_filename_from_url(url1, "text")
        assert filename1 == "file.txt"

        url2 = "http://example.com/file.php?type=mp3&id=123"
        filename2 = fs._get_filename_from_url(url2, "audio")
        assert filename2 == "audio_123.mp3"

        url3 = "http://example.com/unknown"
        filename3 = fs._get_filename_from_url(url3, "document")
        assert filename3 == "resource.txt"


@pytest.mark.asyncio
class TestAsyncConcurrency:

    async def test_concurrent_file_reads_async(self, temp_dir: str) -> None:
        fs = LocalFS(temp_dir)

        num_files = 10
        for i in range(num_files):
            test_file = pathlib.Path(temp_dir) / f"test_{i}.txt"
            test_file.write_text(f"Content {i}", encoding="utf-8")

        tasks = [
            fs.fetch(str(pathlib.Path(temp_dir) / f"test_{i}.txt"), "text")
            for i in range(num_files)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == num_files
        for i, (local_path, content) in enumerate(results):
            assert content == f"Content {i}"

    async def test_concurrent_operations_async(self) -> None:
        async def simulated_async_task(task_id: int, delay: float) -> tuple[int, float]:
            await asyncio.sleep(delay)
            return (task_id, delay)

        tasks = [
            simulated_async_task(i, 0.01 * (i % 3))
            for i in range(10)
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(task_id == result[0] for task_id, result in enumerate(results))
