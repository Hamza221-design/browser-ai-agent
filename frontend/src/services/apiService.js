import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://192.168.18.21:8000/api/v1';
// const API_BASE_URL = 'http://localhost:8000/api/v1';

const apiService = {
  analyzeWebsite: async (url, options = {}) => {
    const defaultOptions = {
      extract_elements: ['forms', 'links'],
      test_types: ['functional', 'validation', 'negative', 'positive', 'error_handling'],
      chunk_size: 2000
    };

    const requestData = {
      url,
      ...defaultOptions,
      ...options
    };

    const response = await axios.post(`${API_BASE_URL}/analyze`, requestData);
    return response.data;
  },

  generateTestCode: async (testCase) => {
    // Map html_chunk to html_code for the /generate-test-code endpoint
    const mappedTestCase = {
      ...testCase,
      html_code: testCase.html_chunk || testCase.html_code || ''
    };
    
    const requestData = {
      test_cases: [mappedTestCase]
    };
    const response = await axios.post(`${API_BASE_URL}/generate-test-code`, requestData);
    return response.data.results[0];
  },

  generateMultipleTestCodes: async (testCases) => {
    // Map html_chunk to html_code for each test case
    const mappedTestCases = testCases.map(testCase => ({
      ...testCase,
      html_code: testCase.html_chunk || testCase.html_code || ''
    }));
    
    const requestData = {
      test_cases: mappedTestCases
    };
    const response = await axios.post(`${API_BASE_URL}/generate-test-code`, requestData);
    return response.data.results;
  },

  chatAnalyze: async (message) => {
    const requestData = {
      message: message
    };
    const response = await axios.post(`${API_BASE_URL}/chat-analyze`, requestData);
    return response.data;
  },

  chatGenerateCode: async (testCases, url) => {
    const requestData = {
      test_cases: testCases,
      url: url
    };
    const response = await axios.post(`${API_BASE_URL}/chat-generate-code`, requestData);
    return response.data.results;
  },

  executeTests: async (testCases) => {
    const requestData = {
      test_cases: testCases
    };
    const response = await axios.post(`${API_BASE_URL}/execute-tests`, requestData);
    return response.data;
  },

  // Unified Chat Service Functions
  sendChatMessage: async (message, sessionId = null) => {
    try {
      const requestData = {
        message: message
      };
      
      // Include session ID if provided
      if (sessionId) {
        requestData.session_id = sessionId;
      }
      
      const response = await axios.post(`${API_BASE_URL}/chat`, requestData);
      return response.data;
    } catch (error) {
      console.error('Error sending chat message:', error);
      throw error;
    }
  },

  getSessionInfo: async (sessionId) => {
    try {
      const response = await axios.get(`${API_BASE_URL}/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Error getting session info:', error);
      throw error;
    }
  },

  clearSession: async (sessionId) => {
    try {
      const response = await axios.delete(`${API_BASE_URL}/sessions/${sessionId}`);
      return response.data;
    } catch (error) {
      console.error('Error clearing session:', error);
      throw error;
    }
  },

  resetSession: async (sessionId) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/sessions/${sessionId}/reset`);
      return response.data;
    } catch (error) {
      console.error('Error resetting session:', error);
      throw error;
    }
  },

  listSessions: async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/sessions`);
      return response.data;
    } catch (error) {
      console.error('Error listing sessions:', error);
      throw error;
    }
  }
};

export default apiService;
