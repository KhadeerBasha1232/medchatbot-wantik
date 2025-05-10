// chat.js
document.addEventListener('DOMContentLoaded', function () {
    const chatContainer = document.getElementById('chatContainer');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');

    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return value;
        }
        return '';
    }

    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        try {
            // Add user message to chat
            addMessage(message, false);
            messageInput.value = '';

            // Show typing indicator
            showTypingIndicator();

            // Send message to backend
            const response = await fetch('/chat-response/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            removeTypingIndicator();

            if (data.status === 'success') {
                addMessage(data.response, true);
            } else {
                addMessage('Sorry, there was an error processing your request.', true);
            }

        } catch (error) {
            console.error('Error:', error);
            removeTypingIndicator();
            addMessage('Sorry, there was an error connecting to the server.', true);
        }
    }


    // Add message to chat container
    function addMessage(text, isBot) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${isBot ? 'justify-start' : 'justify-end'} message-animation`;

        const messageContent = document.createElement('div');
        messageContent.className = `max-w-xl md:max-w-md p-3 rounded-lg ${isBot
                ? 'bg-white text-gray-800 shadow-xl'
                : 'bg-blue-600 text-white'
            }`;
        // Parse markdown using marked library
        messageContent.innerHTML = marked.parse(text);

        messageDiv.appendChild(messageContent);
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Show typing indicator
    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'flex justify-start typing-container';
        indicator.innerHTML = `
            <div class="max-w-xl md:max-w-md p-3 rounded-lg bg-white text-gray-800 shadow-sm">
                <span class="typing-indicator">Typing</span>
            </div>
        `;
        chatContainer.appendChild(indicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Remove typing indicator
    function removeTypingIndicator() {
        const indicator = document.querySelector('.typing-container');
        if (indicator) {
            indicator.remove();
        }
    }

    // Send message to backend
    // chat.js or in your script tag
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        try {
            // Add user message to chat
            addMessage(message, false);
            messageInput.value = '';
            showTypingIndicator();

            const response = await fetch('/chat-response/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken(),
                },
                body: JSON.stringify({ message: message })
            });

            const data = await response.json();
            removeTypingIndicator();

            if (data.status === 'success') {
                addMessage(data.response, true);
            } else {
                console.error('Server error:', data.message);
                addMessage('I apologize, but I encountered an error. Please try again or rephrase your question.', true);
            }

        } catch (error) {
            console.error('Network error:', error);
            removeTypingIndicator();
            addMessage('Sorry, there was an error connecting to the server. Please try again.', true);
        }
    }
    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
});