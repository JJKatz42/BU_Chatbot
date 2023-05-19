from bs4 import BeautifulSoup

# HTML From File
with open("index.html", "r") as f:
    doc = BeautifulSoup(f, "html.parser")
	
print(doc.prettify()) # Print the HTML in a readable format

tags = doc.find_all("p")[0]

print(tags.find_all("b")) # Print all b tags in the first p tag
