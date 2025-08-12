const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const sendChatMessage = async (message) => {
  try {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: message
      }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error sending chat message:', error);
    throw error;
  }
};

export const getSessionInfo = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error getting session info:', error);
    throw error;
  }
};

export const clearSession = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error clearing session:', error);
    throw error;
  }
};

export const resetSession = async (sessionId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error resetting session:', error);
    throw error;
  }
};

export const listSessions = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/sessions`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error listing sessions:', error);
    throw error;
  }
}; 