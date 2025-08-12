class ChatApp {
    constructor() {
        // Configure marked.js for safe rendering
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true, // Enable line breaks
                gfm: true,    // Enable GitHub Flavored Markdown
                sanitize: false, // We'll handle sanitization ourselves if needed
                smartLists: true,
                smartypants: false
            });
        }
        
        // Determine API_BASE based on current hostname
        const hostname = window.location.hostname;
        if (hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '0.0.0.0') {
            this.API_BASE = 'http://localhost:8080';
        } else {
            this.API_BASE = '';
        }
        this.currentChatId = null;
        this.currentUser = null;
        this.uploadedFiles = [];
        
        this.initializeElements();
        this.attachEventListeners();
        this.loadChatHistory();
        this.loadUserInfo();
        this.initializeView();
    }

    initializeElements() {
        // Sidebar elements
        this.sidebar = document.getElementById('sidebar');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.chatHistory = document.getElementById('chatHistory');
        this.userName = document.getElementById('userName');
        this.userEmail = document.getElementById('userEmail');

        // Main content elements
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.chatContainer = document.getElementById('chatContainer');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInputBottom = document.getElementById('chatInputBottom');

        // Input elements
        this.welcomeInput = document.getElementById('welcomeInput');
        this.messageInput = document.getElementById('messageInput');
        this.startChatBtn = document.getElementById('startChatBtn');
        this.sendBtn = document.getElementById('sendBtn');
        this.attachmentBtn = document.getElementById('attachmentBtn');
        this.welcomeAttachmentBtn = document.getElementById('welcomeAttachmentBtn');

        // File display elements
        this.chatUploadedFiles = document.getElementById('chatUploadedFiles');

        // Modal elements
        this.fileModalOverlay = document.getElementById('fileModalOverlay');
        this.fileUploadArea = document.getElementById('fileUploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.uploadedFilesContainer = document.getElementById('uploadedFiles');
    }

    attachEventListeners() {
        // Chat functionality
        this.newChatBtn.addEventListener('click', () => this.createNewChat());
        this.startChatBtn.addEventListener('click', () => this.startNewChatFromWelcome());
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        this.welcomeInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.startNewChatFromWelcome();
            }
        });
        
        // Input change listeners for button states
        this.welcomeInput.addEventListener('input', () => this.updateWelcomeButtonState());
        this.messageInput.addEventListener('input', () => this.updateSendButtonState());

        // File upload
        this.attachmentBtn.addEventListener('click', () => this.openFileModal());
        this.welcomeAttachmentBtn.addEventListener('click', () => this.openFileModal());
        this.fileUploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileUploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.fileUploadArea.addEventListener('drop', (e) => this.handleFileDrop(e));
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));

        // Modal controls
        document.getElementById('modalClose').addEventListener('click', () => this.closeFileModal());
        document.getElementById('modalCancel').addEventListener('click', () => this.closeFileModal());
        document.getElementById('modalUpload').addEventListener('click', () => this.confirmFileUpload());

        // Suggestion buttons
        document.querySelectorAll('.suggestion-btn').forEach(btn => {
            btn.addEventListener('click', () => this.handleSuggestionClick(btn.textContent));
        });

        // Auto-resize textarea
        this.messageInput.addEventListener('input', () => this.autoResizeTextarea());
    }

    async loadChatHistory() {
        try {
            const response = await fetch(`${this.API_BASE}/api/chats/`);
            
            if (response.ok) {
                const chats = await response.json();
                this.renderChatHistory(chats);
            }
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }

    async loadUserInfo() {
        try {
            const response = await fetch(`${this.API_BASE}/api/user/me`);
            
            if (response.ok) {
                const userInfo = await response.json();
                this.currentUser = userInfo;
                this.updateUserDisplay(userInfo);
            }
        } catch (error) {
            console.error('Failed to load user info:', error);
            // Fallback to default user info
            this.updateUserDisplay({
                name: 'Anonymous User',
                email: 'anonymous@example.com'
            });
        }
    }

    updateUserDisplay(userInfo) {
        this.userName.textContent = userInfo.name;
        this.userEmail.textContent = userInfo.email;
        
        // Update user avatar with first letter of name
        const userAvatar = document.querySelector('.user-avatar');
        if (userAvatar) {
            userAvatar.textContent = userInfo.name.charAt(0).toUpperCase();
        }
    }

    renderChatHistory(chats) {
        this.chatHistory.innerHTML = '';
        
        chats.forEach(chat => {
            const chatItem = document.createElement('div');
            chatItem.className = 'chat-item';
            chatItem.innerHTML = `
                <svg class="chat-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                </svg>
                <span>${chat.title}</span>
            `;
            
            chatItem.addEventListener('click', () => this.loadChat(chat.id));
            this.chatHistory.appendChild(chatItem);
        });
    }

    initializeView() {
        // Show welcome screen by default
        this.showWelcomeScreen();
        // Initialize button states
        this.updateWelcomeButtonState();
        this.updateSendButtonState();
    }

    async createNewChat() {
        // Reset to welcome screen and clear current chat
        this.currentChatId = null;
        this.showWelcomeScreen();
        this.welcomeInput.value = '';
        this.uploadedFiles = [];
        this.updateUploadedFilesDisplay();
        this.updateWelcomeFilesDisplay();
        this.updateChatFilesDisplay();
        this.updateWelcomeButtonState();
        
        // Clear any active chat selection in sidebar
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    async startNewChatFromWelcome() {
        const content = this.welcomeInput.value.trim();
        if (!content && this.uploadedFiles.length === 0) return;

        // Create the actual chat now
        const title = content ? content.substring(0, 50) + (content.length > 50 ? '...' : '') : `New Chat ${new Date().toLocaleString()}`;
        
        try {
            const response = await fetch(`${this.API_BASE}/api/chats/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title })
            });
            
            if (response.ok) {
                const chat = await response.json();
                this.currentChatId = chat.id;
                this.showChatInterface();
                this.loadChatHistory();
                this.clearMessages();
                
                // Send the message if there's content or files
                if (content || this.uploadedFiles.length > 0) {
                    await this.sendMessage(content);
                }
            }
        } catch (error) {
            console.error('Failed to create chat:', error);
        }
        
        this.welcomeInput.value = '';
        this.updateWelcomeButtonState();
    }

    async loadChat(chatId) {
        try {
            const response = await fetch(`${this.API_BASE}/api/chats/${chatId}`);
            
            if (response.ok) {
                const chat = await response.json();
                this.currentChatId = chatId;
                this.showChatInterface();
                this.renderMessages(chat.messages);
                this.updateActiveChatItem(chatId);
                
                // Clear any uploaded files when switching to existing chat
                this.uploadedFiles = [];
                this.updateUploadedFilesDisplay();
                this.updateWelcomeFilesDisplay();
                this.updateChatFilesDisplay();
                this.updateSendButtonState();
            }
        } catch (error) {
            console.error('Failed to load chat:', error);
        }
    }

    showChatInterface() {
        this.welcomeScreen.style.display = 'none';
        this.chatMessages.style.display = 'block';
        this.chatInputBottom.style.display = 'block';
    }

    showWelcomeScreen() {
        this.welcomeScreen.style.display = 'flex';
        this.chatMessages.style.display = 'none';
        this.chatInputBottom.style.display = 'none';
        this.currentChatId = null;
    }

    clearMessages() {
        this.chatMessages.innerHTML = '';
    }

    renderMessages(messages) {
        this.chatMessages.innerHTML = '';
        
        messages.forEach(message => {
            this.addMessageToChat(message);
        });
        
        this.scrollToBottom();
    }

    addMessageToChat(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}-message`;
        
        const avatarLetter = message.role === 'user' ? 'A' : 'M';
        
        let attachmentsHtml = '';
        if (message.attachments && message.attachments.length > 0) {
            attachmentsHtml = `
                <div class="message-attachments">
                    ${message.attachments.map(att => 
                        att.file_type === 'image' ? 
                        `<div class="attachment-preview">
                            <img src="${this.API_BASE}/uploads/${att.stored_filename}" alt="${att.filename}">
                        </div>` : 
                        `<div class="attachment-preview">
                            <div class="file-icon">📄</div>
                            <span>${att.filename}</span>
                        </div>`
                    ).join('')}
                </div>
            `;
        }
        
        // Render message content - use markdown for assistant messages, plain text for user messages
        let messageContent;
        if (message.role === 'assistant') {
            // Parse markdown for assistant messages
            messageContent = marked.parse(message.content);
        } else {
            // Keep user messages as plain text but escape HTML
            messageContent = this.escapeHtml(message.content);
        }
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatarLetter}</div>
            <div class="message-content">
                ${attachmentsHtml}
                <div class="message-text">${messageContent}</div>
                ${message.role === 'assistant' ? `
                <div class="message-actions">
                    <button class="retry-btn" onclick="chatApp.retryMessage('${message.id || Date.now()}')">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/>
                            <path d="M21 3v5h-5"/>
                            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/>
                            <path d="M3 21v-5h5"/>
                        </svg>
                        Retry
                    </button>
                </div>
                ` : ''}
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
    }

    async sendMessage(content = null) {
        const messageContent = content || this.messageInput.value.trim();
        if (!messageContent && this.uploadedFiles.length === 0) return;
        
        // Create chat if it doesn't exist
        if (!this.currentChatId) {
            const title = messageContent ? messageContent.substring(0, 50) + (messageContent.length > 50 ? '...' : '') : `New Chat ${new Date().toLocaleString()}`;
            
            try {
                const response = await fetch(`${this.API_BASE}/api/chats/`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ title })
                });
                
                if (response.ok) {
                    const chat = await response.json();
                    this.currentChatId = chat.id;
                    this.showChatInterface();
                    this.loadChatHistory();
                    this.clearMessages();
                }
            } catch (error) {
                console.error('Failed to create chat:', error);
                return;
            }
        }

        // Don't add user message to chat immediately if there are files
        // We'll add it after the server response to get the correct stored filenames
        if (this.uploadedFiles.length === 0) {
            const userMessage = {
                role: 'user',
                content: messageContent,
                attachments: []
            };
            
            this.addMessageToChat(userMessage);
            this.scrollToBottom();
        }

        // Clear input
        if (!content) {
            this.messageInput.value = '';
            this.autoResizeTextarea();
            this.updateSendButtonState();
        }

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Send message to API
            const formData = new FormData();
            formData.append('content', messageContent);
            formData.append('chat_id', this.currentChatId);
            formData.append('role', 'user');
            
            // Add files
            this.uploadedFiles.forEach(file => {
                formData.append('files', file);
            });

            const messageResponse = await fetch(`${this.API_BASE}/api/messages/`, {
                method: 'POST',
                body: formData
            });

            if (messageResponse.ok) {
                const userMessageResult = await messageResponse.json();
                
                // Add the user message with correct attachment info if we have files
                if (this.uploadedFiles.length > 0) {
                    this.addMessageToChat(userMessageResult);
                    this.scrollToBottom();
                }
                
                // Get assistant response
                const assistantFormData = new FormData();
                assistantFormData.append('chat_id', this.currentChatId);
                assistantFormData.append('user_message', messageContent);

                const assistantResponse = await fetch(`${this.API_BASE}/api/messages/assistant-response`, {
                    method: 'POST',
                    body: assistantFormData
                });

                if (assistantResponse.ok) {
                    const assistantMessage = await assistantResponse.json();
                    this.removeTypingIndicator();
                    this.addMessageToChat(assistantMessage);
                    this.scrollToBottom();
                }
            }
        } catch (error) {
            console.error('Failed to send message:', error);
            this.removeTypingIndicator();
        }

        // Clear uploaded files
        this.uploadedFiles = [];
        this.updateUploadedFilesDisplay();
        this.updateWelcomeFilesDisplay();
        this.updateChatFilesDisplay();
        this.updateSendButtonState();
    }

    showTypingIndicator() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant-message typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-avatar">M</div>
            <div class="message-content">
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        this.chatMessages.appendChild(typingDiv);
        this.scrollToBottom();
    }

    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    scrollToBottom() {
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    updateActiveChatItem(chatId) {
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        
        // Find and activate the current chat item
        // This would need to be enhanced to properly identify the chat item
    }

    handleSuggestionClick(text) {
        this.welcomeInput.value = text;
        this.updateWelcomeButtonState();
        this.startNewChatFromWelcome();
    }

    autoResizeTextarea() {
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 120) + 'px';
    }

    // File upload methods
    openFileModal() {
        this.fileModalOverlay.style.display = 'flex';
    }

    closeFileModal() {
        this.fileModalOverlay.style.display = 'none';
    }

    handleDragOver(e) {
        e.preventDefault();
        this.fileUploadArea.style.borderColor = '#9ca3af';
        this.fileUploadArea.style.background = '#f9fafb';
    }

    handleFileDrop(e) {
        e.preventDefault();
        this.fileUploadArea.style.borderColor = '#d1d5db';
        this.fileUploadArea.style.background = '';
        
        const files = Array.from(e.dataTransfer.files);
        this.addFilesToUpload(files);
    }

    handleFileSelect(e) {
        const files = Array.from(e.target.files);
        this.addFilesToUpload(files);
    }

    addFilesToUpload(files) {
        files.forEach(file => {
            if (!this.uploadedFiles.find(f => f.name === file.name && f.size === file.size)) {
                this.uploadedFiles.push(file);
            }
        });
        this.updateUploadedFilesDisplay();
        this.updateWelcomeFilesDisplay();
        this.updateChatFilesDisplay();
        this.updateWelcomeButtonState();
        this.updateSendButtonState();
    }

    updateUploadedFilesDisplay() {
        this.uploadedFilesContainer.innerHTML = '';
        
        this.uploadedFiles.forEach((file, index) => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'uploaded-file';
            fileDiv.innerHTML = `
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
                <button class="remove-file" onclick="chatApp.removeFile(${index})">×</button>
            `;
            this.uploadedFilesContainer.appendChild(fileDiv);
        });
    }

    removeFile(index) {
        this.uploadedFiles.splice(index, 1);
        this.updateUploadedFilesDisplay();
        this.updateWelcomeFilesDisplay();
        this.updateChatFilesDisplay();
        this.updateWelcomeButtonState();
        this.updateSendButtonState();
    }

    confirmFileUpload() {
        this.closeFileModal();
        this.updateWelcomeFilesDisplay();
        this.updateChatFilesDisplay();
        this.updateWelcomeButtonState();
        this.updateSendButtonState();
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    updateWelcomeButtonState() {
        const hasText = this.welcomeInput.value.trim().length > 0;
        const hasFiles = this.uploadedFiles.length > 0;
        const shouldEnable = hasText || hasFiles;
        
        this.startChatBtn.disabled = !shouldEnable;
        this.startChatBtn.style.opacity = shouldEnable ? '1' : '0.5';
        this.startChatBtn.style.cursor = shouldEnable ? 'pointer' : 'not-allowed';
    }

    updateSendButtonState() {
        const hasText = this.messageInput.value.trim().length > 0;
        const hasFiles = this.uploadedFiles.length > 0;
        const shouldEnable = hasText || hasFiles;
        
        this.sendBtn.disabled = !shouldEnable;
        this.sendBtn.style.opacity = shouldEnable ? '1' : '0.5';
        this.sendBtn.style.cursor = shouldEnable ? 'pointer' : 'not-allowed';
    }

    updateWelcomeFilesDisplay() {
        // Find or create the welcome files container
        let welcomeFilesContainer = document.getElementById('welcomeUploadedFiles');
        if (!welcomeFilesContainer) {
            welcomeFilesContainer = document.createElement('div');
            welcomeFilesContainer.id = 'welcomeUploadedFiles';
            welcomeFilesContainer.className = 'welcome-uploaded-files';
            
            // Insert after the chat input wrapper
            const chatInputContainer = document.querySelector('.chat-input-container');
            chatInputContainer.appendChild(welcomeFilesContainer);
        }
        
        welcomeFilesContainer.innerHTML = '';
        
        if (this.uploadedFiles.length > 0) {
            this.uploadedFiles.forEach((file, index) => {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'welcome-uploaded-file';
                
                if (file.type.startsWith('image/')) {
                    // Create image preview
                    const fileURL = URL.createObjectURL(file);
                    fileDiv.innerHTML = `
                        <div class="welcome-file-preview">
                            <img src="${fileURL}" alt="${file.name}" class="welcome-file-image">
                        </div>
                        <div class="welcome-file-info">
                            <div class="welcome-file-name">${file.name}</div>
                            <div class="welcome-file-size">${this.formatFileSize(file.size)}</div>
                        </div>
                        <button class="welcome-remove-file" onclick="chatApp.removeFile(${index})">×</button>
                    `;
                } else {
                    // Create file icon
                    fileDiv.innerHTML = `
                        <div class="welcome-file-icon">📄</div>
                        <div class="welcome-file-info">
                            <div class="welcome-file-name">${file.name}</div>
                            <div class="welcome-file-size">${this.formatFileSize(file.size)}</div>
                        </div>
                        <button class="welcome-remove-file" onclick="chatApp.removeFile(${index})">×</button>
                    `;
                }
                welcomeFilesContainer.appendChild(fileDiv);
            });
        }
    }

    updateChatFilesDisplay() {
        if (!this.chatUploadedFiles) return;
        
        this.chatUploadedFiles.innerHTML = '';
        
        if (this.uploadedFiles.length > 0) {
            this.uploadedFiles.forEach((file, index) => {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'chat-uploaded-file';
                
                if (file.type.startsWith('image/')) {
                    // Create image preview
                    const fileURL = URL.createObjectURL(file);
                    fileDiv.innerHTML = `
                        <div class="chat-file-preview">
                            <img src="${fileURL}" alt="${file.name}" class="chat-file-image">
                        </div>
                        <div class="chat-file-info">
                            <div class="chat-file-name">${file.name}</div>
                            <div class="chat-file-size">${this.formatFileSize(file.size)}</div>
                        </div>
                        <button class="chat-remove-file" onclick="chatApp.removeFile(${index})">×</button>
                    `;
                } else {
                    // Create file icon
                    fileDiv.innerHTML = `
                        <div class="chat-file-icon">📄</div>
                        <div class="chat-file-info">
                            <div class="chat-file-name">${file.name}</div>
                            <div class="chat-file-size">${this.formatFileSize(file.size)}</div>
                        </div>
                        <button class="chat-remove-file" onclick="chatApp.removeFile(${index})">×</button>
                    `;
                }
                this.chatUploadedFiles.appendChild(fileDiv);
            });
        }
    }

    async retryMessage(messageId) {
        if (!this.currentChatId) return;
        
        try {
            // Find the assistant message element to remove it
            const messages = this.chatMessages.querySelectorAll('.assistant-message');
            const lastAssistantMessage = messages[messages.length - 1];
            if (lastAssistantMessage) {
                lastAssistantMessage.remove();
            }
            
            // Show typing indicator
            this.showTypingIndicator();
            
            // Get the last user message content to retry
            const userMessages = this.chatMessages.querySelectorAll('.user-message');
            const lastUserMessage = userMessages[userMessages.length - 1];
            let userMessageContent = '';
            
            if (lastUserMessage) {
                const messageText = lastUserMessage.querySelector('.message-text');
                if (messageText) {
                    userMessageContent = messageText.textContent.trim();
                }
            }
            
            // Request new assistant response
            const assistantFormData = new FormData();
            assistantFormData.append('chat_id', this.currentChatId);
            assistantFormData.append('user_message', userMessageContent);

            const assistantResponse = await fetch(`${this.API_BASE}/api/messages/assistant-response`, {
                method: 'POST',
                body: assistantFormData
            });

            if (assistantResponse.ok) {
                const assistantMessage = await assistantResponse.json();
                this.removeTypingIndicator();
                this.addMessageToChat(assistantMessage);
                this.scrollToBottom();
            } else {
                this.removeTypingIndicator();
                console.error('Failed to get retry response');
            }
        } catch (error) {
            console.error('Failed to retry message:', error);
            this.removeTypingIndicator();
        }
    }
}

// Initialize the app
const chatApp = new ChatApp();
