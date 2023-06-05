from google.cloud import aiplatform

aiplatform.init(project="bu-chatbot-388316")

from vertexai.preview.language_models import TextEmbeddingModel
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import os
import html2text


import numpy as np  # Ensure numpy is imported

# Initialize Google AI Platform
aiplatform.init(project="bu-chatbot-388316", location="us-central1")

# Directory containing HTML files
directory = "/workspaces/BU_Chatbot/Questrom_Course_Info"

# Get list of all HTML files
html_files = [f for f in os.listdir(directory) if f.endswith('.html')]

# Dictionary to store each file's content
html_contents = {}

for html_file in html_files:
    with open(f'{directory}/{html_file}', 'r') as f:
        html_content = f.read()
        h1 = html2text.HTML2Text()
        h2 = h1.handle(html_content)
        html_contents[html_file] = h2

# Load model once
model = TextEmbeddingModel.from_pretrained("textembedding-gecko")

# Counter to track number of API requests
api_request_counter = 0


def text_embedding(text_string):
    """Text embedding with a Large Language Model."""
    print(f"API Request Count: {api_request_counter}")
    embeddings = model.get_embeddings([text_string])
    for embedding in embeddings:
        vector = np.array(embedding.values)  # Ensure embedding is a numpy array
        return vector

# Get embeddings for each html file
text1 = list(html_contents.keys())

text2 = []

for content in html_contents.values():
    # if api_request_counter < 17:  # Model's API rate limit (17 is a placeholder, adjust to your actual limit)
    #     text2.append(text_embedding(content))
    #     api_request_counter += 1
    # else:
    #     # Create a zero array of the appropriate embedding size if limit is exceeded
    #     text2.append(np.zeros(768))  # Ensure embedding size matches your model's

    text2.append(text_embedding(content))
    api_request_counter += 1
    
# Creating the DataFrame
df = pd.DataFrame(text1, columns=["text1"])
df["embeddings"] = text2

df.head(25)


# Embedding for the target string
target_string = "sm 132"
target_embedding = text_embedding(target_string)

# Calculate similarity score
similarity_scores = cosine_similarity(np.vstack(df['embeddings'].values), [target_embedding])  # Ensure cosine_similarity receives numpy arrays
df['similarity_score'] = similarity_scores

# Sorting the dataframe by similarity scores in descending order and getting the top 3
df = df.sort_values(by='similarity_score', ascending=False)

df.head(50)

from vertexai.preview.language_models import (ChatModel, InputOutputTextPair)

chat_model = ChatModel.from_pretrained("chat-bison@001")

import html2text


# top1 = [top_3_courses[2]]
df_top_3 = df.head(3)
df_top_3.head(3)

top_3_courses = df_top_3['text1'].tolist()


print(f"Top 3 courses similar to {target_string}: {top_3_courses}")


text = ""
for html_file in top_3_courses:
    with open(f'{directory}/{html_file}', 'r') as f:
        html_content = f.read()
        h1 = html2text.HTML2Text()
        h1.ignore_links = True
        h2 = h1.handle(html_content)
        h3 = h2[:2000]
        text = text + h3 + "\n"
        # print(h2)


# text = text.replace("  ", " ")
# text = text[:4000]

# with open('Questrom_Course_Info/bu.edu-academics-questrom-courses-qst-sm-132-.html', 'r') as f:
#     html_content = f.read()
#     h1 = html2text.HTML2Text()
#     h1.ignore_links = True
#     h2 = h1.handle(html_content)
#     text = h2

# print(text)


chat = chat_model.start_chat(
    context=f"Here is the text from BU course webpages {text}",
    examples=[
        InputOutputTextPair(
            input_text="Give me a description of the course.",
            output_text="Introduces the basic principles, methods, and challenges of modern managerial accounting. Covers traditional topics such as job-order costing, cost-volume-profit analysis, budgeting and variance analysis, profitability analysis, relevant costs for decision making, and cost-plus pricing, as well as emerging topics such as Activity-Based Cost (ABC) accounting. ",
        ),
        InputOutputTextPair(
            input_text="What are the prerequesits for the course?",
            output_text="QST SM131; CAS MA120, MA121, or MA123 previous or concurrent; sophomore standing.",
        ),
    ],
    temperature=0.1,
    max_output_tokens=100,
    top_p=0.001,
    top_k=0.01,
)

prompt = "describe the course Measuring Financial Value"

print(chat.send_message(f"{prompt}")) 