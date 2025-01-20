import requests
from bs4 import BeautifulSoup
from googlesearch import search  # to use Google search
from langchain import LLMChain, PromptTemplate
from langchain_community.chat_models import ChatOllama
import ollama
import gradio as gr
import re

# 1. Get user input for website and search term
def get_user_input():
    website_url = input("Enter the website URL: ")
    search_term = input("Enter the search term: ")
    return website_url, search_term

# 2. Perform a site-specific search using Google
def site_search(website_url, search_term):
    query = f"site:{website_url} {search_term}"
    search_results = list(search(query, num_results=5))  # Return top 5 results
    return search_results

# 3. Scrape content from the search results
def scrape_page(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # You can refine this to get specific content (e.g., article body, text)
    paragraphs = soup.find_all('p')
    text_content = ' '.join([para.get_text() for para in paragraphs])

    # Attempt to find the main image
    main_image = None
    
    # 2. Look for Open Graph image first (common for main images)
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image["content"]:
        main_image = og_image["content"]
    else:
        # 3. Fallback to finding the first <img> tag if no og:image is present
        img_tag = soup.find("img")
        if img_tag and img_tag["src"]:
            main_image = img_tag["src"]
    
    return text_content, main_image

# 4. Summarize the content using a local LLM (Ollama-based)
def summarize_content(text_content):

    result = ollama.generate(
            model="llama3.1",
            prompt=f"Summarize the following content:\n\n{text_content}\n\n If the page contains lists or tables, format your output as a list or table accordingly. \n\n If there is a date indicating the page publishing date put it at the start of your summary followed by a new line.",
            options={
                "temperature": 0.7,
                "top_p": 0.9
            })

    # Use the Mistral model from Ollama

    return result

        # Convert headings marked by '**' to HTML <h2> tags
def format_headings(text):
    text = re.sub(r'\*\*(.*?)\*\*', r'<h3>\1</h3>', text, count=1)
    return text

# Main function to run the workflow
def handle_prompt(website_url, search_term, style='Reading' ):
   # website_url, search_term = get_user_input()
    search_results = site_search(website_url, search_term)
    summaries = []
    main_images = []
    formatted_response =''
    for idx, result in enumerate(search_results):
        print(f"\nResult {idx+1}: {result}")
        
        # Scrape the page content
        page_content, main_image = scrape_page(result)
        
        # Generate summary using LLM
        summary = summarize_content(page_content)
        
        # Output link and summary
        print(f"\nSummary for {result}:")
        print(summary)

        print("Main Image URL:", main_image)

        if main_image:
                summaries.append(result + '\n\n' + summary.get('response','no response')), main_images.append(main_image)  # Return image in a list for Gradio Gallery
        else:
                summaries.append(result + '\n\n' + summary.get('response','no response')),  main_images

        # Join the list into a single string
        formatted_response = "<hr>".join(summaries)

        # Replace newlines and format headings
        formatted_response = formatted_response.replace("\n\n", "<br><br>").replace("\n", "<br>")
        formatted_response = format_headings(formatted_response)

    return formatted_response, main_images  

# Gradio Interface for Querying
def gradio_query_interface():
    """Gradio UI for querying with custom or predefined prompts."""

    # List of predefined prompts
    predefined_prompts = [
        "None",  # Default value in case no selection is made
        "Summarize the key points of the document.",
        "What is the most important data in this document?",
        "Extract the table content.",
        "Give me an overview of the conclusions."
    ]

    learning_styles = [
        "Visual",
        "Reading/Writing",
        "Kinaesthetic"
    ]

    with gr.Row():
        with gr.Column():
            website_prompt = gr.Textbox(label="Enter a website", placeholder="Type your websiteprompt here...")
            prompt = gr.Textbox(label="Enter your question", placeholder="Type your website prompt here...")
            #predefined_prompt = gr.Dropdown(choices=predefined_prompts, label="Or select a predefined prompt", value="None")
            learning_style = gr.Dropdown(choices=learning_styles, label="Select your style", value="Visual")
            query_button = gr.Button("Query your AI assistant")
        with gr.Column():
            
            query_output_text = gr.Markdown(label="Your Summmary:")
            query_output_images = gr.Gallery(label="Query Image Output")  # Gallery for displaying images
    
    return website_prompt, prompt, learning_style, query_button, query_output_text, query_output_images

# Combine both interfaces with two submit buttons
def create_combined_interface():
    with gr.Blocks(css="footer{display:none !important}") as gr_interface:
        gr.Markdown("# STAR - Personalized Newspaper")
        gr.Markdown("Enter a website and then run queries using a custom or predefined prompt.")
        
        # Part 2: Querying section
        website_prompt, prompt, learning_style, query_button, query_output_text, query_output_images = gradio_query_interface()
        
        # Query button triggers RAG query
        query_button.click(
            fn=handle_prompt,  
            inputs=[website_prompt, prompt, learning_style],
            outputs=[query_output_text, query_output_images]
        )
    return gr_interface

# Launch the combined interface
interface = create_combined_interface()
interface.launch(share=True, server_port=8090)
