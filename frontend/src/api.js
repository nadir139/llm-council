/**
 * API client for the LLM Council backend with Clerk authentication.
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001';

/**
 * Get headers with optional auth token
 */
async function getHeaders(getToken) {
  const headers = {
    'Content-Type': 'application/json',
  };

  // Add auth token if getToken function is provided
  if (getToken) {
    try {
      const token = await getToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (error) {
      console.error('Failed to get auth token:', error);
    }
  }

  return headers;
}

export const api = {
  /**
   * Create user profile after onboarding questions.
   */
  async createProfile(profileData, getToken) {
    const response = await fetch(`${API_BASE}/api/users/profile`, {
      method: 'POST',
      headers: await getHeaders(getToken),
      body: JSON.stringify(profileData),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create profile');
    }
    return response.json();
  },

  /**
   * Get current user's profile.
   */
  async getProfile(getToken) {
    const response = await fetch(`${API_BASE}/api/users/profile`, {
      headers: await getHeaders(getToken),
    });
    if (!response.ok) {
      if (response.status === 404) {
        return null; // Profile doesn't exist yet
      }
      if (response.status === 401) {
        return null; // Not authenticated yet (during sign-in flow)
      }
      throw new Error('Failed to get profile');
    }
    return response.json();
  },

  /**
   * Update user profile (if not locked).
   */
  async updateProfile(profileData, getToken) {
    const response = await fetch(`${API_BASE}/api/users/profile`, {
      method: 'PATCH',
      headers: await getHeaders(getToken),
      body: JSON.stringify(profileData),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to update profile');
    }
    return response.json();
  },

  /**
   * List all conversations.
   */
  async listConversations(getToken) {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      headers: await getHeaders(getToken),
    });
    if (!response.ok) {
      if (response.status === 401) {
        return []; // Not authenticated yet, return empty list
      }
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation(getToken) {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: await getHeaders(getToken),
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      {
        headers: await getHeaders(getToken),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: await getHeaders(getToken),
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @param {function} getToken - Function to get auth token
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: await getHeaders(getToken),
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },

  /**
   * Toggle the starred status of a conversation.
   */
  async toggleStarConversation(conversationId, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/star`,
      {
        method: 'POST',
        headers: await getHeaders(getToken),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to toggle star');
    }
    return response.json();
  },

  /**
   * Update the title of a conversation.
   */
  async updateConversationTitle(conversationId, title, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/title`,
      {
        method: 'PATCH',
        headers: await getHeaders(getToken),
        body: JSON.stringify({ title }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to update title');
    }
    return response.json();
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`,
      {
        method: 'DELETE',
        headers: await getHeaders(getToken),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
    return response.json();
  },

  /**
   * Submit follow-up answers and generate second report (Feature 3).
   *
   * This endpoint saves the follow-up context and automatically generates
   * a second council report with the additional information.
   *
   * @param {string} conversationId - The conversation ID
   * @param {string} followUpAnswers - User's answers to follow-up questions
   * @param {function} getToken - Function to get auth token
   * @returns {Promise<object>} - Second report with stage1, stage3, and metadata
   */
  async submitFollowUp(conversationId, followUpAnswers, getToken) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/follow-up`,
      {
        method: 'POST',
        headers: await getHeaders(getToken),
        body: JSON.stringify({ follow_up_answers: followUpAnswers }),
      }
    );
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to submit follow-up');
    }
    return response.json();
  },
};
