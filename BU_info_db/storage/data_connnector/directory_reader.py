import os
import html2text
import uuid
import aiofiles
import asyncio

from BU_info_db.storage.data_connnector.index_data_classes import WebpageIndex
from BU_info_db.storage.storage_data_classes import Webpage, TextContent


class DirectoryReader:
    SUPPORTED_MIME_TYPES = ["text/html"]

    def __init__(self, directory: str):
        self.directory = directory
        self._html2text = html2text.HTML2Text()
        self._html2text.ignore_links = True

    async def _get_file_contents(self, filepath: str, html_content: str) -> dict:
        markdown_contents = self._html2text.handle(html_content)
        return {
            "text_contents": [TextContent(text=markdown_contents, index=0, metadata={"webpage_name": filepath})],
            "mime_type": "text/markdown"
        }

    async def load_data(self) -> WebpageIndex:
        files = []

        for filename in [f for f in os.listdir(self.directory) if os.path.isfile(os.path.join(self.directory, f))]:
            fullpath = os.path.join(self.directory, filename)

            async with aiofiles.open(fullpath, 'r') as file:
                html_contents = await file.read()

            mime_type = "text/html"
            if mime_type in self.SUPPORTED_MIME_TYPES:
                files.append({'id': fullpath, 'name': filename, 'html_content': html_contents, 'mimeType': mime_type})

        print(f"{len(files)} webpages available")

        file_contents = await asyncio.gather(
            *[self._get_file_contents(file["id"], file["html_content"]) for file in files], return_exceptions=True
        )

        webpages = []
        for file, file_content in zip(files, file_contents):
            if isinstance(file_content, Exception):
                print(f"Failed to get contents for webpage {file['id']}. Error: {str(file_content)}")
                continue

            webpage = Webpage(
                id=str(uuid.uuid4()),
                html_content=file["html_content"],
                url=file["name"],
                mime_type=file_content["mime_type"],
                text_contents=file_content["text_contents"]
            )
            webpages.append(webpage)

        return WebpageIndex(webpages=webpages)
