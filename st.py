import chainlit as cl
import requests
import asyncio

# API Endpoints
# API Endpoints from environment variables
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000/query/")
HISTORY_URL = os.environ.get("HISTORY_URL", "http://127.0.0.1:8000/history/")
CLEAR_HISTORY_URL = os.environ.get("CLEAR_HISTORY_URL", "http://127.0.0.1:8000/clear_history/")

@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    await cl.Message(
        content="Hello! How can I assist you with your Horizon Europe grant writing needs?"
    ).send()
    
    # Fetch and display chat history
    try:
        history_response = requests.get(HISTORY_URL)
        if history_response.status_code == 200:
            chat_history = history_response.json()
            
            if chat_history:
                history_content = "## 📜 Previous Chat History\n\n"
                for entry in chat_history[:5]:  # Limit to most recent 5 entries
                    history_content += f"**Q:** {entry['question']}\n\n"
                    history_content += f"**A:** {entry['answer'][:300]}...\n\n"
                    history_content += "---\n\n"
                
                await cl.Message(content=history_content).send()
    except Exception as e:
        print(f"Failed to load chat history: {str(e)}")

@cl.on_message
async def main(message: cl.Message):
    """Process user messages and stream responses."""
    query = message.content
    
    # Create a message placeholder for streaming
    msg = cl.Message(content="Retrieving information...")
    await msg.send()
    
    try:
        # Set up streaming from FastAPI
        with requests.post(API_URL, json={"query": query}, stream=True) as response:
            if response.status_code == 200:
                # Process the streaming response
                buffer = ""
                full_response = ""
                
                for chunk in response.iter_content(chunk_size=1, decode_unicode=True):
                    if chunk:
                        buffer += chunk
                        full_response += chunk
                        
                        # Update on spaces to simulate word-by-word streaming
                        if ' ' in buffer:
                            words = buffer.split(' ')
                            if len(words) > 1:
                                msg.content = full_response
                                await msg.update()
                                buffer = words[-1]
                                await asyncio.sleep(0.01)
                
                # Add any remaining content
                if buffer:
                    full_response += buffer
                    msg.content = full_response
                    await msg.update()
                
                # Format the final response for better readability
                formatted_response = format_response(full_response)
                msg.content = formatted_response
                await msg.update()
            else:
                error_message = f"Error: API returned status code {response.status_code}"
                msg.content = error_message
                await msg.update()
    
    except Exception as e:
        msg.content = f"An error occurred: {str(e)}"
        await msg.update()

def format_response(text):
    """Format the response to ensure proper markdown structure."""
    # Clean up potential extra spaces from streaming
    text = ' '.join(text.split())
    
    # Handle bullet points with proper formatting
    for bullet_marker in [" - ", "- "]:
        text = text.replace(bullet_marker, "\n* ")
    
    # Process line by line for better formatting
    lines = []
    current_section = None
    
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        
        # Format headings
        lower_line = line.lower()
        if any(section in lower_line for section in ["excellence", "impact", "implementation"]) and len(line) < 50:
            current_section = line
            line = f"## {line}"
        elif current_section and any(subsection in lower_line for subsection in [
            "objectives", "ambition", "state-of-the-art", "methodology", "trl level",
            "impact pathway", "dissemination", "communication", "work plan"
        ]) and len(line) < 60:
            line = f"### {line}"
        
        lines.append(line)
    
    # Join with double newlines for better readability
    formatted_text = '\n\n'.join(lines)
    
    # Ensure bullet points have proper spacing
    formatted_text = formatted_text.replace("\n*", "\n\n*")
    
    return formatted_text

@cl.on_chat_end
async def on_chat_end():
    """Clear chat history when session ends."""
    try:
        requests.delete(CLEAR_HISTORY_URL)
        print("Chat history cleared successfully")
    except Exception as e:
        print(f"Error while clearing chat history: {str(e)}")
