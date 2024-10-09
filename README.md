# Sony Camera AI

This project combines Sony camera control with AI-powered scene analysis and camera setting optimization. It allows you to take pictures using a Sony camera and use OpenAI's multimodal model to suggest optimal camera settings based on the captured image and a given prompt.

## Features

- Control Sony camera (take pictures, check status)
- Analyze captured images using OpenAI's language model
- Optimize camera settings based on scene analysis and user prompt

## Requirements

- Python 3.7+
- Sony camera with API support
- OpenAI API key

## Setup

1. Clone this repository:

   ```
   git clone https://github.com/sebastianboehler/sony-cam-ai.git
   cd sony-cam-ai
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
   ```

3. Install the required packages:

   ```
   pip install -r requirements.txt
   ```

4. Update the `CAMERA_URL` in `sony.py` with your camera's IP address and port.

5. Create a `.env` file in the project root and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

Run the main script:

```
python main.py
```

This will connect to the Sony camera, take a picture, analyze the scene using OpenAI's language model, and suggest optimal camera settings for the next shot.

## License

This project is open-source and available under the MIT License.
