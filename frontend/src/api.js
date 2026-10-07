import axios from 'axios';

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 180000, // 3 minutes for generation (Manim + LLM)
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Generate an educational video using the LLM planner and Manim renderer.
 * @param {string} topic - User's academic topic or question.
 * @param {string} quality - Render quality ('low_quality', 'medium_quality', 'high_quality').
 */
export async function generateVideoFromTopic(topic, quality = 'medium_quality') {
  try {
    const response = await apiClient.post('/api/video/llm/topic', {
      topic: topic.trim(),
      quality,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      // Backend returned an error response (4xx, 5xx)
      const detail = error.response.data?.detail || error.response.data?.message || 'Server error occurred.';
      throw new Error(detail);
    } else if (error.request) {
      // Network error or backend unreachable
      throw new Error(
        'Unable to connect to the SmartCampus backend. Make sure FastAPI is running on port 8000.'
      );
    } else {
      throw new Error(error.message || 'An unexpected error occurred.');
    }
  }
}

/**
 * Check backend health status.
 */
export async function checkBackendHealth() {
  try {
    const response = await apiClient.get('/health', { timeout: 4000 });
    return response.data;
  } catch (err) {
    return null;
  }
}

/**
 * Convert relative video path from backend into full browser URL.
 * @param {string} relativePath - Path like 'generated/scenes/.../file.mp4'
 */
export function getVideoUrl(relativePath) {
  if (!relativePath) return '';
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }
  const cleanPath = relativePath.replace(/^\/+/, '');
  return `${API_BASE_URL}/${cleanPath}`;
}
