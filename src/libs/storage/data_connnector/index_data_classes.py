import dataclasses

import src.libs.storage.storage_data_classes as storage_data_classes


@dataclasses.dataclass
class WebpageIndex:
    webpages: list[storage_data_classes.Webpage]
