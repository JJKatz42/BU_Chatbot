import scrapy
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
import os

class BuAdmissionsSpider(CrawlSpider):
    name = 'bu_crawler'
    allowed_domains = ['bu.edu']
    start_urls = ['https://www.bu.edu/admissions/']

    # Dictionary to store the URL and its HTML content
    scraped_data = {}

    # Defining rules to crawl only /admissions pages and exclude certain paths
    rules = (
        Rule(LinkExtractor(allow=('/admissions/',), deny=('/admissions/visit-us/events/events-calendar/', '/admissions/visit-us/events/virtual-events-calendar/')), callback='parse_page', follow=True),
    )

    # Define callback function for processing pages
    def parse_page(self, response):
        # Adding content to dictionary
        self.scraped_data[response.url] = response.text

    # Define a method that gets called when the spider is closed
    def closed(self, reason):
        # Create directory if it doesn't exist
        os.makedirs('/workspaces/BU_Chatbot/weavdb_direct', exist_ok=True)

        # Iterate over URLs and their corresponding content in the dictionary
        for url, content in self.scraped_data.items():
            # Replace slashes with underscores in the URL to create a valid filename
            file_name = url.replace("/", "_") + ".html"
            file_path = os.path.join('/workspaces/BU_Chatbot/weavdb_direct', file_name)

            # Write the HTML content to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
