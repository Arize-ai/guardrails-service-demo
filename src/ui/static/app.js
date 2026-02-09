// Configuration
const AGENT_API_URL = 'http://localhost:8001';
const GUARDRAILS_API_URL = 'http://localhost:8000';
const UI_API_URL = 'http://localhost:5000';

// State management
let chatMessages = [];
let lastUserRequest = null;
let lastDetectionScores = null;

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadStats();
    addSystemMessage('Welcome to the Guardrails Chat Interface! Send a message to start chatting.');

    // Auto-refresh stats every 5 seconds to keep counts up-to-date
    setInterval(loadStats, 1000000);
});

// Event listeners
function initializeEventListeners() {
    document.getElementById('send-message').addEventListener('click', sendMessage);
    document.getElementById('message-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    document.getElementById('clear-chat').addEventListener('click', clearChat);
    document.getElementById('add-last-to-malicious').addEventListener('click', addLastRequestToMalicious);
    document.getElementById('add-last-to-relevant').addEventListener('click', addLastRequestToRelevant);
    document.getElementById('refresh-stats').addEventListener('click', syncAndLoadStats);

    // Threshold sliders
    const anomalySlider = document.getElementById('relevance-threshold');
    const anomalyValue = document.getElementById('relevance-threshold-value');
    anomalySlider.addEventListener('input', (e) => {
        anomalyValue.textContent = parseFloat(e.target.value).toFixed(2);
    });

    const maliciousSlider = document.getElementById('malicious-threshold');
    const maliciousValue = document.getElementById('malicious-threshold-value');
    maliciousSlider.addEventListener('input', (e) => {
        maliciousValue.textContent = parseFloat(e.target.value).toFixed(2);
    });
}

// Chat functions
async function sendMessage() {
    const input = document.getElementById('message-input');
    const message = input.value.trim();

    if (!message) {
        showToast('Please enter a message', 'error');
        return;
    }

    // Clear input and disable button
    input.value = '';
    const sendBtn = document.getElementById('send-message');
    sendBtn.disabled = true;
    sendBtn.innerHTML = '<span class="loading"></span> Sending...';

    // Add user message to chat
    addMessage('user', message);

    // Save the user request
    lastUserRequest = message;

    // Get threshold values from sliders
    const anomalyThreshold = parseFloat(document.getElementById('relevance-threshold').value);
    const maliciousThreshold = parseFloat(document.getElementById('malicious-threshold').value);

    try {
        const response = await fetch(`${AGENT_API_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                system_prompt: null,
                anomaly_threshold: anomalyThreshold,
                malicious_threshold: maliciousThreshold
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Debug: log the response
        console.log('Chat response:', data);

        // Save detection scores
        lastDetectionScores = {
            anomaly: data.anomaly_details || {},
            malicious: data.malicious_details || {}
        };

        console.log('Detection scores:', lastDetectionScores);

        // Update detection scores display
        updateDetectionScores(lastDetectionScores);

        // Enable the "Add Last Request" buttons
        document.getElementById('add-last-to-malicious').disabled = false;
        document.getElementById('add-last-to-relevant').disabled = false;

        // Add assistant response
        addMessage('assistant', data.response, {
            timestamp: data.timestamp
        });

    } catch (error) {
        console.error('Error sending message:', error);
        addMessage('system', `Error: ${error.message}. Make sure the agent service is running on ${AGENT_API_URL}`);
        showToast('Failed to send message', 'error');
    } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = 'Send Message';
    }
}

function addMessage(type, content, metadata = {}) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) {
        console.error('chat-messages element not found in DOM');
        return;
    }
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;

    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = type === 'user' ? 'U' : type === 'assistant' ? 'A' : 'S';

    const contentWrapper = document.createElement('div');
    contentWrapper.style.display = 'flex';
    contentWrapper.style.flexDirection = 'column';

    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    messageContent.textContent = content;

    const messageMeta = document.createElement('div');
    messageMeta.className = 'message-meta';

    const timestamp = new Date().toLocaleTimeString();
    messageMeta.innerHTML = `<span>${timestamp}</span>`;

    if (metadata.model) {
        messageMeta.innerHTML += `<span>Model: ${metadata.model}</span>`;
    }

    contentWrapper.appendChild(messageContent);
    contentWrapper.appendChild(messageMeta);

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentWrapper);

    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    chatMessages.push({ type, content, metadata, timestamp });
}

function addSystemMessage(content) {
    addMessage('system', content);
}

function clearChat() {
    if (confirm('Are you sure you want to clear the chat history?')) {
        document.getElementById('chat-messages').innerHTML = '';
        chatMessages = [];
        addSystemMessage('Chat cleared. Start a new conversation!');
    }
}

// Detection scores display
function updateDetectionScores(scores) {
    updateAnomalyScores(scores.anomaly);
    updateMaliciousScores(scores.malicious);
}

function updateAnomalyScores(details) {
    const container = document.getElementById('relevance-scores');

    if (!container) {
        console.error('Element "relevance-scores" not found in DOM');
        return;
    }

    if (!details || Object.keys(details).length === 0) {
        container.innerHTML = '<p class="no-data">No data available</p>';
        return;
    }

    const riskLevel = getRiskLevel(details.median_distance, 'anomaly');

    container.innerHTML = `
        <div class="score-item">
            <span class="score-label">Median Distance:</span>
            <span class="score-value">${(details.median_distance || 0).toFixed(3)}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Risk Level:</span>
            <span class="risk-badge ${riskLevel}">${riskLevel}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Similar Records:</span>
            <span class="score-value">${details.similar_records_count || 0}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Min Distance:</span>
            <span class="score-value">${(details.min_distance || 0).toFixed(3)}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Max Distance:</span>
            <span class="score-value">${(details.max_distance || 0).toFixed(3)}</span>
        </div>
    `;
}

function updateMaliciousScores(details) {
    const container = document.getElementById('malicious-scores');

    if (!container) {
        console.error('Element "malicious-scores" not found in DOM');
        return;
    }

    if (!details || Object.keys(details).length === 0) {
        container.innerHTML = '<p class="no-data">No data available</p>';
        return;
    }

    const riskLevel = getRiskLevel(details.detection_distance, 'malicious');

    container.innerHTML = `
        <div class="score-item">
            <span class="score-label">Detection Distance:</span>
            <span class="score-value">${(details.detection_distance || 0).toFixed(3)}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Risk Level:</span>
            <span class="risk-badge ${riskLevel}">${riskLevel}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Similar Records:</span>
            <span class="score-value">${details.similar_records_count || 0}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Min Distance:</span>
            <span class="score-value">${(details.min_distance || 0).toFixed(3)}</span>
        </div>
        <div class="score-item">
            <span class="score-label">Median Distance:</span>
            <span class="score-value">${(details.median_distance || 0).toFixed(3)}</span>
        </div>
    `;
}

function getRiskLevel(distance, type) {
    if (type === 'anomaly') {
        // Higher distance = higher anomaly risk
        if (distance > 0.8) return 'high';
        if (distance > 0.6) return 'medium';
        return 'low';
    } else {
        // Lower distance = higher malicious risk
        if (distance < 0.2) return 'high';
        if (distance < 0.6) return 'medium';
        return 'low';
    }
}

// Guardrails functions
async function addLastRequestToMalicious() {
    if (!lastUserRequest) {
        showToast('No request to add', 'error');
        return;
    }

    const btn = document.getElementById('add-last-to-malicious');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="loading"></span> Adding to Arize...';

    try {
        const response = await fetch(`${UI_API_URL}/datasets/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                dataset_type: 'pharmacy-malicious-baseline',
                text: lastUserRequest,
                timestamp: new Date().toISOString()
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server error:', response.status, errorText);
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        await response.json();
        showToast('Added to Arize malicious dataset! Click "Refresh Stats" to sync.', 'success');

    } catch (error) {
        console.error('Error adding to Arize dataset:', error);
        showToast(`Failed to add to dataset: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function addLastRequestToRelevant() {
    if (!lastUserRequest) {
        showToast('No request to add', 'error');
        return;
    }

    const btn = document.getElementById('add-last-to-relevant');
    btn.disabled = true;
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="loading"></span> Adding to Arize...';

    try {
        const response = await fetch(`${UI_API_URL}/datasets/add`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                dataset_type: 'pharmacy-anomaly-baseline',
                text: lastUserRequest,
                timestamp: new Date().toISOString()
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            console.error('Server error:', response.status, errorText);
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }

        await response.json();
        showToast('Added to Arize anomaly dataset! Click "Refresh Stats" to sync.', 'success');

    } catch (error) {
        console.error('Error adding to Arize dataset:', error);
        showToast(`Failed to add to dataset: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// Statistics functions
async function loadStats() {
    // Just fetch stats from vector store (lightweight, used for auto-refresh)
    try {
        const [anomalyResponse, maliciousResponse] = await Promise.all([
            fetch(`${GUARDRAILS_API_URL}/anomaly/baseline/stats`),
            fetch(`${GUARDRAILS_API_URL}/malicious/baseline/stats`)
        ]);

        if (!anomalyResponse.ok || !maliciousResponse.ok) {
            throw new Error('Failed to fetch statistics');
        }

        const anomalyStats = await anomalyResponse.json();
        const maliciousStats = await maliciousResponse.json();

        updateStatsDisplay(anomalyStats, maliciousStats);

    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('stats-display').innerHTML = `
            <p style="color: var(--danger-color);">Failed to load statistics</p>
            <p style="font-size: 12px;">Make sure services are running</p>
        `;
    }
}

async function syncAndLoadStats() {
    // Sync from Arize AND fetch stats (heavy operation, triggered by button click)
    const btn = document.getElementById('refresh-stats');
    const originalText = btn ? btn.textContent : '';

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading"></span> Syncing from Arize...';
    }

    try {
        // First, sync datasets from Arize to vector store
        const syncResponse = await fetch(`${UI_API_URL}/datasets/sync`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (syncResponse.ok) {
            const syncData = await syncResponse.json();
            console.log('Arize sync results:', syncData);

            if (syncData.results) {
                const anomalySynced = syncData.results.anomaly?.records_synced || 0;
                const maliciousSynced = syncData.results.malicious?.records_synced || 0;
                showToast(`Cleared old data and synced from Arize: ${anomalySynced} anomaly, ${maliciousSynced} malicious records`, 'success');
            }
        } else {
            console.warn('Sync failed, continuing to load stats');
        }

        // Then fetch updated stats
        await loadStats();

    } catch (error) {
        console.error('Error syncing:', error);
        showToast('Failed to sync from Arize', 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    }
}

function updateStatsDisplay(anomalyStats, maliciousStats) {
    const statsDisplay = document.getElementById('stats-display');
    statsDisplay.innerHTML = `
        <div style="margin-bottom: 12px;">
            <strong style="color: var(--primary-color);">Relevant Baseline</strong>
            <p>Total Records: ${anomalyStats.total_records || 0}</p>
            <p style="font-size: 11px; color: var(--text-secondary);">Collection: ${anomalyStats.collection_name || 'N/A'}</p>
        </div>
        <div>
            <strong style="color: var(--danger-color);">Malicious Baseline</strong>
            <p>Total Records: ${maliciousStats.total_records || 0}</p>
            <p style="font-size: 11px; color: var(--text-secondary);">Collection: ${maliciousStats.collection_name || 'N/A'}</p>
        </div>
    `;
}

// Toast notifications
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✓',
        error: '✕',
        info: 'ℹ'
    };

    const titles = {
        success: 'Success',
        error: 'Error',
        info: 'Info'
    };

    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-content">
            <div class="toast-title">${titles[type]}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}
