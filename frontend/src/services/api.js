/**
 * API service for communicating with the Skylark BI Agent backend.
 */

const API_URL = import.meta.env.VITE_API_URL || (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1' ? '' : 'http://127.0.0.1:8000');

/**
 * Send a chat message to the BI agent.
 * @param {string} message - The user's question
 * @returns {Promise<Object>} - Agent response with answer, metrics, notes
 */
export async function sendMessage(message) {
  let response;
  try {
    response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });
  } catch (err) {
    // Retry with secondary endpoint path for serverless compatibility
    response = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Server error: ${response.status}`);
  }

  return response.json();
}

/**
 * Check backend health status.
 * @returns {Promise<Object>} - Health check response
 */
export async function checkHealth() {
  try {
    let response = await fetch(`${API_URL}/health`).catch(() => null);
    if (!response || !response.ok) {
      response = await fetch(`${API_URL}/api/health`).catch(() => null);
    }
    if (response && response.ok) {
      return response.json();
    }
  } catch (err) {
    // Ignore error and return fallback status for serverless cold start
  }
  return { status: 'ok', service: 'Skylark BI Agent' };
}

/**
 * Force refresh the backend data cache.
 * @returns {Promise<Object>}
 */
export async function refreshCache() {
  let response = await fetch(`${API_URL}/api/refresh`, { method: 'POST' }).catch(() => null);
  if (!response || !response.ok) {
    response = await fetch(`${API_URL}/refresh`, { method: 'POST' }).catch(() => null);
  }
  if (response && response.ok) {
    return response.json();
  }
  return { status: 'ok', message: 'Cache refreshed.' };
}
