import html2text

import langchain.text_splitter as text_splitter
import BU_info_db.storage.storage_data_classes as storage_data_classes


class WebpageSplitterTransformer:
    """Splits the TextContents of Document objects to optimize for searchability"""
    def __init__(self, text_delimiters: list[str] | None = None):
        self._text_delimiters = text_delimiters or ["\n\n", "\n", " ", ""]
        self._plain_text_splitter = text_splitter.RecursiveCharacterTextSplitter(
            separators=self._text_delimiters
        )
        self._markdown_text_splitter = text_splitter.MarkdownTextSplitter()

    def transform(self, Webpage: storage_data_classes.Webpage):
        # We don't perform any splitting on CSV Documents because they are already split into 1 TextContent per sheet
        
        if Webpage.mime_type == storage_data_classes.MimeType.MARKDOWN:
            splitter = self._markdown_text_splitter
        else:
            splitter = self._plain_text_splitter

        # Create TextContent objects from text chunks of downloaded contents for the file
        h_1 = html2text.HTML2Text()
        h_1.ignore_links = True
        h_2 = h_1.handle(Webpage.html_content)
        clean_text = h_2


        chunks = splitter.split_text(clean_text)
        Webpage.text_contents = [
            storage_data_classes.TextContent(text=chunk, index=chunk_index)
            for chunk_index, chunk in enumerate(chunks)
        ]