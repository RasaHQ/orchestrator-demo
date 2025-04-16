import os
from jinja2 import Environment, FileSystemLoader, TemplateNotFound


class TemplateRenderer:
    def __init__(self, template_path):
        """
        Initialize the TemplateRenderer with the given template path.
        
        :param template_path: The full path to the Jinja2 template file.
        """
        if not template_path:
            raise ValueError("A valid template_path must be provided")

        # Get the directory and filename
        template_dir = os.path.dirname(template_path)
        template_filename = os.path.basename(template_path)

        # Validate directory and file
        if not os.path.isdir(template_dir):
            raise FileNotFoundError(f"Template directory not found: {template_dir}")
        if not os.path.isfile(template_path):
            raise FileNotFoundError(f"Template file not found: {template_path}")

        # Initialize Jinja2 environment and load the template
        self.env = Environment(loader=FileSystemLoader(template_dir))
        try:
            self.template = self.env.get_template(template_filename)
        except TemplateNotFound:
            raise FileNotFoundError(f"Template file not found by Jinja2: {template_filename}")

    def render(self, **kwargs):
        """
        Render the template with the provided variables.
        
        :param kwargs: Variables to be passed to the template for rendering.
        :return: Rendered string.
        """
        return self.template.render(**kwargs)


# Example usage:
# renderer = TemplateRenderer("/path/to/template.html")
# prompt = renderer.render(results=results, user_message=user_message)