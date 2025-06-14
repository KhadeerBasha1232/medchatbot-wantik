document.addEventListener('DOMContentLoaded', function () {
    const chatContainer = document.getElementById('chatContainer');
    const messageInput = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    const sessionList = document.getElementById('sessionList');
    const sessionTitle = document.getElementById('sessionTitle');
    const newChatBtn = document.getElementById('newChatBtn');
    const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('mainContent');
    let currentSessionId = null;
    let isTyping = false; // Track typing state

    // Debug: Verify elements exist
    console.log('chatContainer:', chatContainer);
    console.log('toggleSidebarBtn:', toggleSidebarBtn);
    console.log('sidebar:', sidebar);
    console.log('mainContent:', mainContent);
    console.log('newChatBtn:', newChatBtn);

    // Function to get CSRF token from cookies
    function getCSRFToken() {
        const cookies = document.cookie.split(';');
        for (let cookie of cookies) {
            const [name, value] = cookie.trim().split('=');
            if (name === 'csrftoken') return value;
        }
        return '';
    }

    // Function to add a message to the chat container
    function addMessage(text, isBot) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `flex ${isBot ? 'justify-start' : 'justify-end'} mb-4 message-animation`;
        const messageContent = document.createElement('div');
        messageContent.className = `max-w-xl md:max-w-md p-3 rounded-lg ${isBot ? 'bg-white text-gray-800 shadow-xl' : 'bg-blue-600 text-white'}`;
        // Parse markdown using marked library
        messageContent.innerHTML = marked.parse(text);
        messageDiv.appendChild(messageContent);
        chatContainer.appendChild(messageDiv);
        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    // Function to show typing indicator and disable input
    function showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'flex justify-start mb-4 typing-container';
        indicator.innerHTML = `
            <div class="max-w-xl md:max-w-md p-3 rounded-lg bg-white text-gray-800 shadow-sm">
                <span class="typing-indicator">Typing</span>
            </div>
        `;
        chatContainer.appendChild(indicator);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        // Disable send button and input
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.classList.add('opacity-50', 'cursor-not-allowed');
        }
        if (messageInput) {
            messageInput.disabled = true;
            messageInput.classList.add('opacity-50', 'cursor-not-allowed');
        }
        // Set typing state and add beforeunload event
        isTyping = true;
        window.addEventListener('beforeunload', handleBeforeUnload);
    }

    // Function to remove typing indicator and re-enable input
    function removeTypingIndicator() {
        const indicator = document.querySelector('.typing-container');
        if (indicator) indicator.remove();
        // Re-enable send button and input
        if (sendBtn) sendBtn.disabled = false;
        if (messageInput) {
            messageInput.disabled = false;
            messageInput.classList.remove('opacity-50', 'cursor-not-allowed');
        }
        // Clear typing state and remove beforeunload event
        isTyping = false;
        window.removeEventListener('beforeunload', handleBeforeUnload);
    }

    // Function to handle beforeunload event
    function handleBeforeUnload(event) {
        if (isTyping) {
            event.preventDefault();
            event.returnValue = 'The bot is responding. Do you want to exit anyway?';
        }
    }

    // Function to show toast notification
    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 left-4 p-4 rounded-lg shadow-lg z-[80] max-w-xs animate-slide-in transition-all duration-300 ${type === 'success' ? 'bg-green-500 text-white' : 'bg-red-500 text-white'}`;
        toast.textContent = message;
        document.body.appendChild(toast);

        // Auto-dismiss after 3 seconds
        setTimeout(() => {
            toast.classList.remove('animate-slide-in');
            toast.classList.add('animate-slide-out');
            setTimeout(() => {
                toast.remove();
            }, 300); // Match animation duration
        }, 3000);
    }

    // Function to show confirmation popup
    function showDeleteConfirmation(sessionId, sessionTitle) {
        // Apply blur to background
        sidebar.classList.add('blur-sm');
        mainContent.classList.add('blur-sm');

        // Create popup overlay
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[70]';
        overlay.id = 'deleteOverlay';

        // Create popup content
        const popup = document.createElement('div');
        popup.className = 'bg-white rounded-lg p-6 max-w-sm w-full shadow-xl';
        popup.setAttribute('role', 'dialog');
        popup.setAttribute('aria-labelledby', 'deletePopupTitle');
        popup.innerHTML = `
            <h3 id="deletePopupTitle" class="text-lg font-semibold mb-4">Delete Chat Session</h3>
            <p class="text-gray-600 mb-6">Are you sure you want to delete the session "${sessionTitle}"? This action cannot be undone.</p>
            <div class="flex justify-end space-x-2">
                <button id="cancelDelete" class="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition-colors">Cancel</button>
                <button id="confirmDelete" class="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">Delete</button>
            </div>
        `;

        // Append popup to overlay and overlay to body
        overlay.appendChild(popup);
        document.body.appendChild(overlay);

        // Event listeners for buttons
        document.getElementById('cancelDelete').addEventListener('click', () => {
            document.body.removeChild(overlay);
            sidebar.classList.remove('blur-sm');
            mainContent.classList.remove('blur-sm');
        });

        document.getElementById('confirmDelete').addEventListener('click', () => {
            deleteSession(sessionId);
            document.body.removeChild(overlay);
            sidebar.classList.remove('blur-sm');
            mainContent.classList.remove('blur-sm');
        });

        // Close popup when clicking outside
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                document.body.removeChild(overlay);
                sidebar.classList.remove('blur-sm');
                mainContent.classList.remove('blur-sm');
            }
        });
    }

    // Function to delete a session
    async function deleteSession(sessionId) {
        try {
            const response = await fetch(`/delete_chat_session/${sessionId}/`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            });
            const data = await response.json();
            if (data.status === 'success') {
                // Remove session from sidebar
                const sessionDiv = document.querySelector(`#sessionList > div[data-session-id="${sessionId}"]`);
                if (sessionDiv) sessionDiv.remove();
                // If deleted session was active, start a new chat
                if (currentSessionId === sessionId) {
                    startNewChat();
                }
                // Refresh session list
                await loadChatSessions();
                showToast('Chat session deleted successfully.', 'success');
            } else {
                console.error('Error deleting session:', data.message);
                showToast('Error: Unable to delete the session.', 'error');
            }
        } catch (error) {
            console.error('Error deleting session:', error);
            showToast('Error: Unable to delete the session.', 'error');
        }
    }

    // Function to add a session to the sidebar
    function addSessionToSidebar(session) {
        const sessionDiv = document.createElement('div');
        sessionDiv.className = 'p-3 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors flex items-center justify-between';
        sessionDiv.dataset.sessionId = session.session_id;
        sessionDiv.innerHTML = `
            <span class="text-sm truncate flex-1 pr-2">${session.title}</span>
            <div class="flex items-center space-x-2">
                <button class="delete-session-btn text-red-500 hover:text-red-700 p-1 rounded" data-session-id="${session.session_id}" data-session-title="${session.title}">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
                <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1" d="M9 5l7 7-7 7" />
                </svg>
            </div>
        `;
        // Click session title to load messages
        sessionDiv.querySelector('.truncate').addEventListener('click', () => {
            currentSessionId = session.session_id;
            localStorage.setItem('currentSessionId', currentSessionId);
            loadSessionMessages(session.session_id, session.title);
        });
        // Click delete button to show confirmation
        sessionDiv.querySelector('.delete-session-btn').addEventListener('click', (e) => {
            e.stopPropagation(); // Prevent session click
            showDeleteConfirmation(session.session_id, session.title);
        });
        sessionList.appendChild(sessionDiv);
    }

    // Function to fetch and display chat sessions
    async function loadChatSessions() {
        try {
            console.log("Fetching /get_chat_sessions/"); // Debug
            const response = await fetch('/get_chat_sessions/', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            });
            const data = await response.json();
            if (data.status === 'success') {
                sessionList.innerHTML = ''; // Clear existing sessions
                data.sessions.forEach(session => addSessionToSidebar(session));
                return data.sessions;
            } else {
                console.error('Error loading chat sessions:', data.message);
                return [];
            }
        } catch (error) {
            console.error('Error fetching chat sessions:', error);
            return [];
        }
    }

    // Function to load messages for a specific session
    async function loadSessionMessages(sessionId, title) {
        currentSessionId = sessionId;
        localStorage.setItem('currentSessionId', currentSessionId); // Save to localStorage
        sessionTitle.textContent = title || 'Medical Assistant';
        chatContainer.innerHTML = ''; // Clear chat container
        try {
            const response = await fetch(`/get_session_messages/${sessionId}/`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                }
            });
            const data = await response.json();
            if (data.status === 'success') {
                data.messages.forEach(message => addMessage(message.content, message.role === 'assistant'));
                // Highlight active session
                document.querySelectorAll('#sessionList > div').forEach(div => {
                    div.classList.remove('bg-blue-100');
                    if (div.dataset.sessionId === sessionId) {
                        div.classList.add('bg-blue-100');
                    }
                });
            } else {
                console.error('Error loading session messages:', data.message);
                addMessage('Error: Unable to load session messages.', true);
                startNewChat(); // Fallback to new chat if session is invalid
                localStorage.removeItem('currentSessionId'); // Clear invalid session
            }
        } catch (error) {
            console.error('Error fetching session messages:', error);
            addMessage('Error: Unable to load session messages.', true);
            startNewChat(); // Fallback to new chat if session is invalid
            localStorage.removeItem('currentSessionId'); // Clear invalid session
        }
    }

    // Function to create a new session
    async function createNewSession() {
        try {
            const response = await fetch('/create_chat_session/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ title: 'New Chat' })
            });
            const data = await response.json();
            if (data.status === 'success') {
                currentSessionId = data.session_id;
                localStorage.setItem('currentSessionId', currentSessionId); // Save to localStorage
                sessionTitle.textContent = 'New Chat';
                await loadChatSessions();
                return data.session_id;
            } else {
                console.error('Error creating new session:', data.message);
                addMessage('Error: Unable to create a new session.', true);
                return null;
            }
        } catch (error) {
            console.error('Error creating new session:', error);
            addMessage('Error: Unable to create a new session.', true);
            return null;
        }
    }

    // Function to send a new message
    async function sendMessage() {
        const message = messageInput.value.trim();
        if (!message) return;

        // If no session exists, create a new one
        if (!currentSessionId) {
            const newSessionId = await createNewSession();
            if (!newSessionId) {
                addMessage('Error: Unable to create a new session.', true);
                return;
            }
            currentSessionId = newSessionId;
        }

        addMessage(message, false);
        messageInput.value = '';
        showTypingIndicator();

        try {
            const response = await fetch('/chat-response/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({ message, session_id: currentSessionId })
            });
            const data = await response.json();
            removeTypingIndicator();
            if (data.status === 'success') {
                addMessage(data.response, true);
                // Refresh session list if title updated
                await loadChatSessions();
                if (data.title && data.title !== sessionTitle.textContent) {
                    sessionTitle.textContent = data.title;
                }
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

    // Function to start a new chat session
    async function startNewChat() {
        currentSessionId = null;
        localStorage.removeItem('currentSessionId'); // Clear saved session
        chatContainer.innerHTML = '';
        sessionTitle.textContent = 'Medical Assistant';
        document.querySelectorAll('#sessionList > div').forEach(div => {
            div.classList.remove('bg-blue-100');
        });
        messageInput.focus();
    }

    // Function to toggle sidebar
    function toggleSidebar() {
        if (!sidebar || !mainContent || !toggleSidebarBtn) {
            console.error('Sidebar, mainContent, or toggleSidebarBtn not found');
            return;
        }
        const isCollapsed = sidebar.dataset.collapsed === 'true';
        if (isCollapsed) {
            // Expand sidebar
            sidebar.classList.remove('w-[50px]');
            sidebar.classList.add('w-64');
            mainContent.classList.remove('ml-[50px]');
            mainContent.classList.add('ml-64');
            sidebar.dataset.collapsed = 'false';
            toggleSidebarBtn.querySelector('svg').innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />';
            localStorage.setItem('sidebarCollapsed', 'false');
            console.log('Sidebar expanded');
        } else {
            // Collapse sidebar
            sidebar.classList.remove('w-64');
            sidebar.classList.add('w-[50px]');
            mainContent.classList.remove('ml-64');
            mainContent.classList.add('ml-[50px]');
            sidebar.dataset.collapsed = 'true';
            toggleSidebarBtn.querySelector('svg').innerHTML = '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />';
            localStorage.setItem('sidebarCollapsed', 'true');
            console.log('Sidebar collapsed');
        }
    }

    // Initialize sidebar state from localStorage
    function initializeSidebar() {
        if (!sidebar || !mainContent || !toggleSidebarBtn) {
            console.error('Required elements for sidebar not found');
            return;
        }
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true' || window.innerWidth < 640;
        if (isCollapsed) {
            toggleSidebar(); // Collapse sidebar on load for mobile or stored preference
        }
        console.log('Sidebar initialized, collapsed:', isCollapsed);
    }

    // Initialize chat state
    async function initializeChat() {
        initializeSidebar();
        const savedSessionId = localStorage.getItem('currentSessionId');
        if (savedSessionId) {
            // Fetch sessions to verify if saved session exists
            const sessions = await loadChatSessions();
            const session = sessions.find(s => s.session_id === savedSessionId);
            if (session) {
                // Load saved session
                loadSessionMessages(savedSessionId, session.title);
            } else {
                // Saved session is invalid, start new chat
                localStorage.removeItem('currentSessionId');
                startNewChat();
                await loadChatSessions();
            }
        } else {
            // No saved session, start new chat
            startNewChat();
            await loadChatSessions();
        }
    }

    // Event listeners
    if (sendBtn) {
        sendBtn.addEventListener('click', sendMessage);
    } else {
        console.error('sendBtn not found');
    }
    if (messageInput) {
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !messageInput.disabled) sendMessage();
        });
    } else {
        console.error('messageInput not found');
    }
    if (newChatBtn) {
        newChatBtn.addEventListener('click', startNewChat);
    } else {
        console.error('newChatBtn not found');
    }
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', toggleSidebar);
        console.log('Toggle sidebar button event listener attached');
    } else {
        console.error('toggleSidebarBtn not found');
    }

    // Initialize
    initializeChat();
});