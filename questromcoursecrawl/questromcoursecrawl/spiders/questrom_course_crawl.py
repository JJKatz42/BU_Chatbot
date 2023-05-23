# pylint: disable=W0223

import os
import requests
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor


class CourseSpider(CrawlSpider):
    """A spider to crawl the Questrom course site and extract course urls

    Args:
        CrawlSpider: A spider that crawls a website and extracts information
    """
    name = "mycrawler"
    allowed_domains = ["bu.edu"]
    start_urls = ["https://www.bu.edu/academics/questrom/courses/"]
    course_urls = {}

    rules = (
        Rule(LinkExtractor(allow=(r"/academics/questrom/courses/\d+/")), callback="parse_course", follow=True),
        Rule(LinkExtractor(allow=("/academics/questrom/courses/")), callback="parse_course", follow=True),
    )

    def parse_course(self, response):
        """Parse the course page and extract the course url

        Args:
            response: The response from the course page
        """
        # Extract additional information about the course if needed
        # For example, you can extract course title, description, etc.
        course_title = response.css('h1::text').get()
        course_url = response.url

        self.course_urls[course_title] = course_url.replace("?wantsMobile=true", "")

def run_crawler():
    """Run the crawler and return the course urls

    Args:
        None
    """
    process = CrawlerProcess(get_project_settings())
    process.crawl(CourseSpider)
    process.start()

    returned_course_urls = CourseSpider.course_urls

    return returned_course_urls


def download_html(url_dict, output_dir):
    """Download the HTML content of the websites in the dictionary

    Args:
        url_dict: A dictionary of website titles and urls
        output_dir: The directory to store the downloaded HTML files
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for course_title, url in url_dict.items():
        filename = os.path.join(output_dir, f"{course_title}.html")
        response = requests.get(url, timeout=100)
        if response.status_code == 200:
            with open(filename, "w", encoding="utf-8") as file:
                file.write(response.text)
                print(f"HTML downloaded for {course_title}")
        else:
            print(f"Failed to download HTML for {course_title}")

# Example usage
urls = run_crawler()
output_directory = "/workspaces/BU_Chatbot/Questrom_Course_Site_HTML_From_Scrapy_Using_Crawler"
download_html(urls, output_directory)
