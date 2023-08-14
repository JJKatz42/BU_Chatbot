# What is the strawman
### The following is a strawman end-to-end solution for the BUChatbot
What is a strawman?
- A strawman version of a product is a prototype solution to a problem, built on incomplete information and ideas that have not been fully thought through. The purpose of the strawman is to (even though it's in a rough state) help ensure everyone involved has a common understanding of the concept.

### Capabilities of the strawman:
- First, the strawman will take in a folder containing files where each file represents a webpage. The file's contents will hold the HTML content of the corresponding webpage, while the file's title will be the webpage's URL. (Note: you cannot store "/" in a file name, so they have been replaced with "_"). 
- (get_embeddings) Then, the strawman will calculate and store the embeddings for the contents of all the files along with the URL and content in a CSV file
- (open) Lastly, the strawman will take in a query and find the most relevant content of the query using cosine vector similarity and then input the query and relevant content into an LLM model to retrieve an answer to the query


Info Glossary:

Strawman: https://thinkinsights.net/consulting/strawman-proposal-brainstorming-the-mckinsey-way/
embeddings: https://www.deepset.ai/blog/the-beginners-guide-to-text-embeddings
openAI documentation for embeddings: https://platform.openai.com/docs/api-reference/embeddings
cosine similarity: https://medium.com/@techclaw/cosine-similarity-between-two-arrays-for-word-embeddings-c8c1c98811b
