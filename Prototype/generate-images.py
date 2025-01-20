import gradio as gr
import ollama
import webbrowser
import os
import re
import requests

# Unsplash API Key (Access Key)
UNSPLASH_ACCESS_KEY = "Qs3YZmkydHojxEkgBq5dPa2zquwK5klJEcOZRKKzrm4"

# Determine age group based on inputted age
def determine_age_group(age):
    if 1 <= age <= 12:
        return "child"
    elif 13 <= age <= 19:
        return "teen"
    elif 20 <= age <= 29:
        return "young adult"
    elif 30 <= age <= 59:
        return "adult"
    elif age >= 60:
        return "senior"
    else:
        return "unknown"

# Function to clean unnecessary text and artifacts from the generated template
def clean_generated_code(raw_template):
    # Remove code block delimiters like ```html or ```
    cleaned_template = re.sub(r"```.*?\n", "", raw_template, flags=re.DOTALL)
    # Remove explanatory text like "This HTML code creates a webpage..."
    cleaned_template = re.sub(r"This .*?screens\.", "", cleaned_template, flags=re.DOTALL)
    # Remove any lingering text outside valid HTML tags
    cleaned_template = re.sub(r"^[^<]*", "", cleaned_template, flags=re.DOTALL)
    # Remove trailing non-HTML content after </html>
    cleaned_template = re.sub(r"</html>.*", "</html>", cleaned_template, flags=re.DOTALL)
    return cleaned_template.strip()

# Function to fetch unique images using Unsplash API
def fetch_images(query, num_images=7):
    unique_images = set()  # To store unique image URLs
    page = 1  # Pagination to fetch more images if needed

    while len(unique_images) < num_images:
        url = f"https://api.unsplash.com/search/photos"
        params = {
            "query": query,
            "client_id": UNSPLASH_ACCESS_KEY,
            "per_page": num_images * 2,  # Fetch more images per query
            "page": page,
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            results = response.json()
            # Add only unique image URLs to the set
            for item in results.get("results", []):
                unique_images.add(item["urls"]["regular"])
                if len(unique_images) >= num_images:
                    break
        else:
            print(f"Error: Unable to fetch images (Status Code: {response.status_code})")
            break  # Stop fetching if there's an error
        if not results.get("results"):  # Stop if no more images are available
            print("No more results available from Unsplash.")
            break
        page += 1  # Move to the next page if more images are needed

    # Convert the set to a list and return only the required number of images
    return list(unique_images)[:num_images]

def generate_template(age, gender):
    # Validate age input
    try:
        age = int(age)
        age_group = determine_age_group(age)
        if age_group == "unknown":
            return "Invalid age entered. Please enter a valid age."
    except ValueError:
        return "Invalid input. Please enter a numeric age."

    # Validate gender input
    gender = gender.lower()
    if gender not in ["male", "female"]:
        return "Invalid gender entered. Please select Male or Female."

    # Fetch relevant images
    query = f"Health tips for a {gender} {age_group}"
    image_urls = fetch_images(query)

    if not image_urls:
        return "Failed to fetch images. Please try again."

    # Define gender-specific header colors
    header_color = "blue" if gender == "male" else "pink"

    # Construct the prompt for the LLM
    template_prompt = f"""
        Generate a visually appealing HTML and CSS template for a health-related webpage tailored specifically to a {gender} {age_group}.
        Include a structured layout with the following:
        - A prominent header section with the title: "Personalized Health Tips for {gender.capitalize()} {age_group.capitalize()}". 
          - The header should have a background color:
              - For males: {header_color}.
              - For females: {header_color}.
        - Sections for "Nutrition", "Exercise", and "General Health".
        - Each section should include a short health tip in sentence form, accompanied by an image above or beside it.
        - Use the following images dynamically fetched: {image_urls}.
        - Ensure images are 300px wide and maintain aspect ratio.
        - Use a modern and clean design with colors suited for the demographic:
            - Males: Blue/Green
            - Females: Pink/Peach
        - Ensure the layout is responsive for both desktop and mobile screens.
        - Include CSS styling within a <style> tag inside the HTML.

        The HTML should:
        - Start with <!DOCTYPE html> and end with </html>.
        - Replace placeholders {{image_1}}, {{image_2}}, etc., with the corresponding image URLs.
        - Be clean, structured, and easy to read.
        - Avoid explanatory text or comments.
    """

    # Generate the template using the LLM
    template_response = ollama.generate(model="llama3.2", prompt=template_prompt) #CHECK TEMPERATURE PARAMETER

    # Ensure a valid response is received
    raw_template = template_response.get("response", "") if isinstance(template_response, dict) else str(template_response)

    # Clean the HTML template
    cleaned_template = clean_generated_code(raw_template)

    if not cleaned_template:
        return "The generated template was empty. Please try again."

    # Replace placeholders with image URLs
    for idx, image_url in enumerate(image_urls, start=1):
        placeholder = f"{{image_{idx}}}"
        cleaned_template = cleaned_template.replace(placeholder, image_url)

    # Write the HTML to a file
    output_file = "generated_template.html"
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(cleaned_template)

    # Open the HTML file in the default web browser
    webbrowser.open(f"file://{os.path.abspath(output_file)}")

    return "Template generated successfully! The HTML file has been opened in your browser."

# Gradio Interface
with gr.Blocks() as demo:
    with gr.Row():
        gr.Markdown("## Dynamic HTML Template Generator for Personalized Health Tips")
    with gr.Row():
        age_input = gr.Textbox(label="Enter your age:", placeholder="e.g., 25")
        gender_input = gr.Dropdown(label="Select your gender:", choices=["Male", "Female"], value="Male")
    with gr.Row():
        submit_button = gr.Button("Generate HTML Template")
    with gr.Row():
        output_message = gr.Textbox(label="Status", interactive=False)

    # Link button to the function
    submit_button.click(generate_template, inputs=[age_input, gender_input], outputs=[output_message])

# Launch the Gradio interface
demo.launch()
