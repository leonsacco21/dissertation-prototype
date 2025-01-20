# Importing necessary libraries
import gradio as gr
import ollama
import webbrowser
import os

# Determining the user's age group
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

# Generating the HTML template based on the user's age
def generate_template(age):
    # Validating the user's age input
    try:
        age = int(age)
        age_group = determine_age_group(age)
        if age_group == "unknown":
            return "Invalid age entered. Please enter a valid age."
    except ValueError:
        return "Invalid input. Please enter a numeric age."

    # Defining characteristics for age-based styling
    user_characteristics = {
        "age_group": age_group,
        "preferred_layout": "simple and engaging" if age_group in ["child", "teen"] else "professional and accessible",
    }

    # Constructing the prompt for template generation
    template_prompt = f"""
        Generate only the HTML and CSS code for a clean, visually appealing webpage tailored to {user_characteristics['age_group']} users. The requirements are:

        1. Use a {user_characteristics['preferred_layout']} layout with a calming color palette (e.g., light blues, greens, and whites) and appropriate fonts.
        2. Style the header to include:
        - The website title, styled with a large font size.
        - A horizontal navigation menu with styled links (e.g., "Home", "Mental Health", "Fitness", "Articles") displayed inline and evenly spaced.
        3. Style the main content area to include:
        - Three equally sized article boxes displayed side by side in a single row.
        - Each article box must have:
            - Centered titles like "Mental Health Tips", "Fitness Advice", or "Healthy Eating".
            - Include a short, meaningful placeholder summary inside each box (e.g., "Explore tips for a balanced lifestyle.").
            - Div tags for text (e.g., "article-1", "article-2", "article-3").
        - The boxes must have some spacing between them.
        - The layout should be responsive: on smaller screens, the article boxes should stack vertically.
        4. Use internal CSS enclosed in a <style> tag inside the <head> section.
        5. Ensure the header and main content area are visually distinct and harmoniously aligned.
        6. Ensure the HTML and CSS are properly formatted, without unnecessary escape sequences like \\n or extra spaces.
        7. Ensure the output is immediately usable by copying it into a .html file.
        8. **Do not include any explanatory text, introductory lines, or comments in the output.** The response must consist solely of the HTML and CSS code.
        """

    # Generating the template using Ollama
    template_response = ollama.generate(model="llama3.2", prompt=template_prompt)

    # Cleaning the generated content
    if isinstance(template_response, dict):
        raw_template = template_response.get("response") or template_response.get("text")
    else:
        raw_template = str(template_response)

    # Removing unwanted escape characters
    clean_template = raw_template.replace("```html", "").replace("```", "").replace("\\n", "\n").replace("\\t", "\t").strip()

    # Writing the generated HTML to a standalone file
    output_file = "generated_template.html"
    with open(output_file, "w", encoding="utf-8") as file:
        file.write(clean_template)

    # Open the generated HTML in the default web browser
    webbrowser.open(f"file://{os.path.abspath(output_file)}")

    return f"Template generated successfully! The HTML file has been opened in your browser."

# Setting up the Gradio interface
with gr.Blocks() as demo:
    with gr.Row():
        gr.Markdown("## HTML Template Generator")
    with gr.Row():
        age_input = gr.Textbox(label="Enter your age:", placeholder="e.g., 25")
    with gr.Row():
        submit_button = gr.Button("Generate HTML Template")
    with gr.Row():
        output_message = gr.Textbox(label="Status", interactive=False)

    # Linking the button click to the function
    submit_button.click(generate_template, inputs=[age_input], outputs=[output_message])

# Launch the Gradio interface
demo.launch()
