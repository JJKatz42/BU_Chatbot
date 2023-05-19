from bs4 import BeautifulSoup
import requests

# HTML From Website
# URL = "https://www.bu.edu/academics/questrom/courses/"

def get_course_urls(strt_url: str) -> dict:
    """Create a dictionary of course names and urls from the Questrom course site

    Args:
        strt_url: The url of the first page of courses
    """

    course_urls = {}
    
    result = requests.get(strt_url)
    doc = BeautifulSoup(result.text, "html.parser")

    class_title = "pagination" # Class that contains the urls to the different pages of courses

    course_pages_blah = doc.find(class_=class_title)

    course_pages = course_pages_blah.find_all("a")

    last_course_page_url  = course_pages[-1].get("href")

    num_course_pages = last_course_page_url[-3:-1]

    for i in range(1, int(num_course_pages) + 1):
        # HTML From Website
        url = f"https://www.bu.edu/academics/questrom/courses/{i}/"

        result = requests.get(url)
        doc = BeautifulSoup(result.text, "html.parser")

        info = doc.find_all("ul")[4] # List of course names and urls

        courses = info.find_all("li")

        for course in courses:
            if course.find_all("a") != []:
                course_url_and_name = course.find_all("a")[0]
                course_name = course_url_and_name.find("strong").text
                course_url = "bu.edu" + course_url_and_name.get("href")
                course_urls[course_name] = course_url
            else:
                continue

    return course_urls

    # for course in course_urls:
    #     print(course + ": " + course_urls[course])
