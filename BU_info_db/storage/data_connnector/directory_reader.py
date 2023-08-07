import asyncio
import os
import html2text
import uuid

from urllib.parse import urlparse
# import magic

from BU_info_db.storage.data_connnector.index_data_classes import WebpageIndex
from BU_info_db.storage.storage_data_classes import Webpage, TextContent


class DirectoryReader:
    """Reader for pulling all files from a directory representing webpages"""

    SUPPORTED_MIME_TYPES = [
        "text/html"
    ]

    def __init__(self, directory: str):
        """Initialize the Directory Reader instance

        Args:
            directory: The path to the directory to read files from
        """
        self.directory = directory
        self._html2text = html2text.HTML2Text()
        self._html2text.ignore_links = True

    async def _get_file_contents(self, filepath: str) -> dict:
        """Retrieves the contents of a file in a directory and returns as TextContent objects

        Args:
            filepath: The file path of the file to get the contents for

        Returns:
            Response: The contents of the file as a list of TextContents
        """
        with open(filepath, 'r') as file:
            html_contents = file.read()

        markdown_contents = self._html2text.handle(html_contents)
        text_contents = [
            TextContent(
                text=markdown_contents,
                index=0,
                metadata={
                    "webpage_name": filepath
                }
            )
        ]
        return {
            "text_contents": text_contents,
            "mime_type": "text/markdown"
        }

    async def load_data(self) -> WebpageIndex:
        """Loads the full contents of all HTML files in the directory

        Returns:
            DocumentIndex: DocumentIndex object containing Webpages representing the full contents from the directory
        """
        files = []
        for filename in os.listdir(self.directory):
            fullpath = os.path.join(self.directory, filename)
            if os.path.isfile(fullpath):
                file_stat = os.stat(fullpath)
                with open(fullpath, 'r') as file:
                    html_contents = file.read()
                # mime_type = magic.from_file(fullpath, mime=True)
                mime_type = "text/html"

                if mime_type in self.SUPPORTED_MIME_TYPES:
                    files.append({
                        'id': fullpath,
                        'name': filename,
                        'html_content': html_contents,
                        'mimeType': mime_type
                    })

        print(f"{len(files)} webpages available")

        file_contents = await asyncio.gather(
            *[self._get_file_contents(file["id"]) for file in files], return_exceptions=True
        )

        webpages: list[Webpage] = []
        for file, file_content in zip(files, file_contents):
            if isinstance(file_content, Exception):
                print(f"Failed to download contents for webpage {file['id']}. Error: {str(file_content)}")
                continue

            id = str(uuid.uuid4())

            file_name = file["name"].replace("_", "/")

            # Create webpage object
            webpage = Webpage(
                id=id,
                html_content=file["html_content"],
                url=file_name,
                mime_type=file_content["mime_type"],
                text_contents=file_content["text_contents"]
            )
            webpages.append(webpage)

        return WebpageIndex(webpages=webpages)
