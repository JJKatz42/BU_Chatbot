# pylint: disable=W0223

import os
import shutil
import multiprocessing
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor


class CourseSpider(CrawlSpider):
    """A spider to crawl the Questrom course site and extract course urls

    Args:
        CrawlSpider: A spider that crawls a website and extracts information
    """

    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', "mycrawler")
        self.output_directory = kwargs.get('output_directory', "/Users/jonahkatz/Desktop/BU_Chatbot/new_webpages2")
        self.allowed_domains = kwargs.get('allowed_domains', [])
        self.start_urls = kwargs.get('start_urls', [])
        self.rules = (
            Rule(LinkExtractor(allow=kwargs.get('allow_rules', []), deny=kwargs.get('deny_rules', [])),
                 callback="parse_course", follow=True),
        )
        super(CourseSpider, self).__init__(*args, **kwargs)
        self.scraped_data = {}

    def parse_course(self, response):
        """Parse the course page and extract the course url

        Args:
            response: The response from the course page
        """
        if self.scraped_data.get(response.url) is None:
            self.scraped_data[response.url] = response.text

    def closed(self, reason):
        # Check if the directory exists. If it does, remove it
        if os.path.exists(self.output_directory):
            shutil.rmtree(self.output_directory)

        # Create directory if it doesn't exist
        os.makedirs(self.output_directory, exist_ok=True)

        # Iterate over URLs and their corresponding content in the dictionary
        for url, content in self.scraped_data.items():
            # Replace slashes with underscores in the URL to create a valid filename
            file_name = url.replace("/", "_")
            file_name = file_name.replace("?wantsMobile=true", "")
            file_path = os.path.join(self.output_directory, file_name)

            # Write the HTML content to the file
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

def start_crawler(name, allowed_domains, start_urls, allow_rules, deny_rules, output_directory):
    """Start the crawler process

    Args:
        None
    """
    process = CrawlerProcess(get_project_settings())
    process.crawl(CourseSpider, name=name, allowed_domains=allowed_domains, start_urls=start_urls,
                  allow_rules=allow_rules, deny_rules=deny_rules, output_directory=output_directory)
    process.start()


def run_crawler(name, allowed_domains, start_urls, allow_rules, deny_rules, output_directory):
    """Run the crawler and return the course urls

    Args:
        None
    """
    p = multiprocessing.Process(target=start_crawler, args=(name, allowed_domains, start_urls, allow_rules, deny_rules, output_directory))
    p.start()
    p.join()

    # Iterate over URLs and their corresponding content in the dictionary
    print("HELEKN SLDNS")


if __name__ == '__main__':
    # Example usage
    output_directory = "/Users/jonahkatz/Desktop/BU_Chatbot/new_webpages3"
    name = "mycrawler"
    allowed_domains = ["bu.edu"]
    start_urls = ["https://www.bu.edu/admissions/", "https://www.bu.edu/dining/"]
    allow_rules = ["/admissions/", "/dining/"]
    deny_rules = ["/admissions/visit-us/events/events-calendar/", "/admissions/visit-us/events/virtual-events-calendar/", "/dining/calendar/",  "/dining/dining_experiences/calendar/"]

    # Add bu.edu/reg/ to start_urls and allow_rules to get registration info

    # start_urls = ["https://www.bu.edu/academics/"]
    # allow_rules = ["/academics/"]
    # deny_rules = ["events-calendar/", "events/virtual-events-calendar/", "/bme-events/", "calendar/", "events/"]

    run_crawler(name, allowed_domains, start_urls, allow_rules, deny_rules, output_directory)
