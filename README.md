# X/Twitter Automation Bot

An automated bot that handles X/Twitter interactions including DMs, mentions, and content generation using Selenium and Cloud Run.

## Features

- 🤖 Automated DM handling and responses
- 🎨 Content generation via API integration
- 📝 Mention monitoring and responses
- 🔄 Automated post creation
- 🌐 Headless browser automation
- ☁️ Cloud Run deployment ready

## Prerequisites

- Python 3.12+
- Microsoft Edge browser
- Docker (for containerization)
- X account credentials

## Local Setup

1. Clone the repository:
```bash
git clone https://github.com/peytontolbert/create-x-generations.git
cd create-x-generations
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:
```env
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
CREATE_API_KEY=your_api_key
# Add other required environment variables
```

## Running Locally

```bash
python main.py
```

## Docker Setup

1. Build the Docker image:
```bash
docker build -t selenium-bot .
```

2. Run the container:
```bash
docker run -d --name selenium-bot selenium-bot
```


## Project Structure
```
├── main.py # Application entry point
├── Dockerfile # Docker configuration
├── cloudbuild.yaml # Cloud Build configuration
├── requirements.txt # Python dependencies
├── src/
│ ├── controllers/ # Main controllers
│ │ ├── main_controller.py
│ │ ├── message_controller.py
│ │ ├── mention_controller.py
│ │ ├── post_controller.py
│ │ └── browser_controller.py
│ └── services/ # Service modules
│ ├── action_handler.py
│ ├── create_agent.py
│ ├── create_api.py
│ └── conversation_memory.py
```


## Configuration

The application can be configured through environment variables:

- `TWITTER_USERNAME`: X/Twitter login username
- `TWITTER_PASSWORD`: X/Twitter login password
- `CREATE_API_KEY`: API key for content generation
- `DISPLAY`: Display configuration for headless browser (default: ":99")

## Docker Environment

The Docker container includes:
- Python 3.12
- Microsoft Edge browser
- Edge WebDriver
- Xvfb for virtual display
- Required system dependencies

## Memory Management

The application uses a conversation memory system to track interactions:
- Stores conversation history
- Manages DM states
- Handles mention tracking
- Persists data between restarts

## Logging

Logs are written to both console and `app.log`:
- INFO level for general operations
- ERROR level for issues
- DEBUG level for detailed debugging

## Error Handling

The application includes comprehensive error handling:
- Automatic retry mechanisms
- Graceful failure recovery
- Browser session management
- Network error handling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
