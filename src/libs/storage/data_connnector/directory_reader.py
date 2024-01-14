import os
import html2text
import uuid
import aiofiles
import asyncio
from bs4 import BeautifulSoup

import src.libs.storage.data_connnector.index_data_classes as index_data_classes
import src.libs.storage.storage_data_classes as storage_data_classes
import src.libs.logging as logging


logger = logging.getLogger(__name__)


# Aliases
WebpageIndex = index_data_classes.WebpageIndex
Webpage = storage_data_classes.Webpage
TextContent = storage_data_classes.TextContent
MimeType = storage_data_classes.MimeType


class DirectoryReader:
    SUPPORTED_MIME_TYPES = [MimeType.HTML]

    def __init__(self, directory: str, university: str):
        self.directory = directory
        self.university = university
        self._html2text = html2text.HTML2Text()
        self._html2text.ignore_links = True

    async def _get_file_contents(self, filepath: str, html_content: str) -> dict:
        markdown_contents = self._html2text.handle(html_content)
        return {
            "text_contents": [TextContent(text=markdown_contents, index=0, metadata={"webpage_name": filepath})],
            "mime_type": "text/html"
        }

    @staticmethod
    def is_html_content(content):
        try:
            # Using the html.parser to parse the content
            soup = BeautifulSoup(content, 'html.parser')

            # Check for presence of common HTML tags.
            html_tags = ['html', 'head', 'body', 'p', 'a', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']

            for tag in html_tags:
                if soup.find(tag):
                    return True

            return False
        except:
            return False

    async def load_data(self) -> WebpageIndex:
        files = []

        for filename in [f for f in os.listdir(self.directory) if os.path.isfile(os.path.join(self.directory, f))]:
            fullpath = os.path.join(self.directory, filename)

            async with aiofiles.open(fullpath, 'r') as file:
                html_contents = await file.read()

            if self.is_html_content(html_contents):
                mime_type = "text/html"
                files.append({'id': fullpath, 'name': filename, 'html_content': html_contents, 'mimeType': mime_type})
            else:
                logger.info(f"Skipping '{filename}' as it is not HTML.")

        logger.info(f"{len(files)} webpages available")

        file_contents = await asyncio.gather(
            *[self._get_file_contents(file["id"], file["html_content"]) for file in files], return_exceptions=True
        )

        webpages = []
        for file, file_content in zip(files, file_contents):
            if isinstance(file_content, Exception):
                logger.warning(f"Failed to get contents for webpage {file['id']}. Error: {str(file_content)}")
                continue

            webpage = Webpage(
                id=str(uuid.uuid4()),
                html_content=file["html_content"],
                url=file["name"].replace("_", "/"),
                university=self.university,
                mime_type=file_content["mime_type"],
                text_contents=file_content["text_contents"]
            )
            webpages.append(webpage)

        return WebpageIndex(webpages=webpages)
