import gradio as gr
import os
import webbrowser
from template import generate_template, determine_age_group
from content import fetch_personalized_content

def sanitize_content(content):
    """
    Cleans and formats content to be HTML-safe.
    """
    return content.replace("\n", "<br>").replace("\r", "").strip()

def generate_and_display_website(age, preference):
    """
    Generates a personalized HTML template with web content dynamically inserted.
    """
    try:
        # Generate template
        print("Generating HTML Template...")
        template_html = generate_template(age)
        if not template_html:
            return "Error: Failed to generate HTML template."

        # Fetch personalized content
        print("Fetching personalized content...")
        age_group = determine_age_group(age)
        if age_group == "unknown":
            return "Error: Invalid age. Please enter a valid number."

        content, images = fetch_personalized_content(age_group, preference)

        if isinstance(content, str) and content.startswith("Error"):
            return f"Error: {content}"

        # Insert fetched content into the template
        article_sections = content.split("\n")
        filled_html = (
            template_html
            .replace("<article class=\"article-card\">", article_sections[0], 1)
            .replace("<article class=\"article-card\">", article_sections[1], 1)
            .replace("<article class=\"article-card\">", article_sections[2], 1)
        )

        # Save and open the final HTML
        output_file = "final_personalized_website.html"
        with open(output_file, "w", encoding="utf-8") as file:
            file.write(filled_html)

        webbrowser.open(f"file://{os.path.abspath(output_file)}")
        return "Website generated successfully! Check your browser for the result."

    except Exception as e:
        return f"An error occurred: {e}"

# Gradio Interface
with gr.Blocks() as demo:
    gr.Markdown("# Personalized Website Generator")
    gr.Markdown("Enter your details to generate a custom website.")

    with gr.Row():
        age_input = gr.Textbox(label="Age", placeholder="Enter your age, e.g., 25")
        preference_input = gr.Radio(["Visual", "Verbal"], label="Content Preference", value="Verbal")

    with gr.Row():
        submit_button = gr.Button("Generate Website")
        status_output = gr.Textbox(label="Status")

    submit_button.click(generate_and_display_website, inputs=[age_input, preference_input], outputs=status_output)

demo.launch()
