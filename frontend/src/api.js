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
export async function generateVideoFromTopic(topic, quality = 'medium_quality', targetDuration = 30) {
  try {
    const response = await apiClient.post('/api/video/llm/topic', {
      topic: topic.trim(),
      quality,
      target_duration: targetDuration,
      target_duration_seconds: targetDuration,
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

/**
 * Synthesize educational voiceover narration using IndicF5 TTS.
 * @param {object} plan - EducationalVideoPlan object
 * @param {number} targetDuration - Target duration in seconds
 */
export async function generateNarrationFromPlan(plan, targetDuration = 30) {
  try {
    const response = await apiClient.post('/api/audio/tts', {
      plan,
      target_duration_seconds: targetDuration,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      const detail = error.response.data?.detail || error.response.data?.message || 'TTS generation error.';
      throw new Error(detail);
    } else {
      throw new Error(error.message || 'Unable to synthesize audio.');
    }
  }
}

/**
 * Convert relative audio path from backend into full browser URL.
 */
export function getAudioUrl(relativePath) {
  if (!relativePath) return '';
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }
  const cleanPath = relativePath.replace(/^\/+/, '');
  return `${API_BASE_URL}/${cleanPath}`;
}

/**
 * Transcribe narration audio using faster-whisper to produce timestamps and subtitles.
 * @param {string} audioPath - Path to generated narration WAV file
 * @param {string} language - Language code ('en')
 */
export async function transcribeAudio(audioPath, language = 'en') {
  try {
    const response = await apiClient.post('/api/subtitle/transcribe', {
      audio_path: audioPath,
      language,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      const detail = error.response.data?.detail || error.response.data?.message || 'Subtitle transcription error.';
      throw new Error(detail);
    } else {
      throw new Error(error.message || 'Unable to transcribe audio for subtitles.');
    }
  }
}

/**
 * Convert relative subtitle path from backend into full browser URL.
 */
export function getSubtitleUrl(relativePath) {
  if (!relativePath) return '';
  if (relativePath.startsWith('http://') || relativePath.startsWith('https://')) {
    return relativePath;
  }
  const cleanPath = relativePath.replace(/^\/+/, '');
  return `${API_BASE_URL}/${cleanPath}`;
}

/**
 * Compose video, audio, and subtitles into a final browser-ready MP4.
 * @param {string} videoPath - Relative path to Manim scene video
 * @param {string} audioPath - Relative path to narration WAV audio
 * @param {string} subtitlePath - Relative path to SRT subtitles
 * @param {boolean} burnSubtitles - Whether to burn subtitles into video
 */
export async function composeVideo(videoPath, audioPath, subtitlePath = null, burnSubtitles = true) {
  try {
    const response = await apiClient.post('/api/video/compose', {
      video_path: videoPath,
      audio_path: audioPath,
      subtitle_path: subtitlePath,
      burn_subtitles: burnSubtitles,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      const detail = error.response.data?.detail || error.response.data?.message || 'Video composition error.';
      throw new Error(detail);
    } else {
      throw new Error(error.message || 'Unable to compose final video.');
    }
  }
}

/**
 * Generate full educational video end-to-end (Qwen -> Manim + IndicF5 + Whisper -> FFmpeg -> Final MP4).
 * Optionally composites the AI Teacher avatar layer.
 */
export async function generateFullVideo(
  topic,
  quality = 'medium_quality',
  burnSubtitles = true,
  targetDuration = 30,
  character = false,
  characterPosition = 'auto',
  visualStyle = 'academic'
) {
  try {
    const response = await apiClient.post('/api/video/full', {
      topic: topic.trim(),
      quality,
      burn_subtitles: burnSubtitles,
      target_duration_seconds: targetDuration,
      character: Boolean(character),
      character_position: characterPosition,
      visual_style: visualStyle,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      const detail = error.response.data?.detail || error.response.data?.message || 'Full video generation error.';
      throw new Error(detail);
    } else {
      throw new Error(error.message || 'Unable to generate full educational video.');
    }
  }
}

/**
 * Generate AI Teacher avatar preview clip using canonical teacher.png and sample audio.
 */
export async function generateAvatarPreview(duration = 10, position = 'auto') {
  try {
    const response = await apiClient.post('/api/avatar/preview', {
      duration,
      position,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      const detail = error.response.data?.detail || error.response.data?.message || 'Avatar preview error.';
      throw new Error(detail);
    } else {
      throw new Error(error.message || 'Unable to generate avatar preview.');
    }
  }
}

/**
 * Fetch canonical character metadata and dimensions.
 */
export async function getCharacterInfo() {
  try {
    const response = await apiClient.get('/api/avatar/character');
    return response.data;
  } catch (error) {
    return null;
  }
}


