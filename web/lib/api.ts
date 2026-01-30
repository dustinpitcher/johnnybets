/**
 * JohnnyBets API Client
 * 
 * Provides typed access to the backend API with streaming support.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface CreateSessionResponse {
  session_id: string;
  created_at: string;
  model: string | null;
  reasoning: string | null;
}

export interface ChatResponse {
  session_id: string;
  response: string;
  message_count: number;
}

export interface Tool {
  id: string;
  name: string;
  description: string;
  category: string;
  status: 'free' | 'premium' | 'roadmap' | 'idea';
  icon: string;
  sports: string[];
  function_name?: string;
  eta?: string;
  price_tier?: string;
  votes: number;
}

export interface ToolsListResponse {
  tools: Tool[];
  total: number;
  filters: {
    status: string | null;
    category: string | null;
    sport: string | null;
  };
}

export interface ToolStats {
  total: number;
  by_status: {
    free: number;
    premium: number;
    roadmap: number;
    idea: number;
  };
  by_category: {
    general: number;
    nfl: number;
    nba: number;
    nhl: number;
    mlb: number;
  };
  by_sport: {
    nfl: number;
    nhl: number;
    mlb: number;
    nba: number;
  };
}

// API Error class
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Helper for fetch with error handling
async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new APIError(
      error.detail || `Request failed with status ${response.status}`,
      response.status,
      error.detail
    );
  }

  return response.json();
}

// ============================================================================
// Chat API
// ============================================================================

export async function createSession(
  model?: string,
  reasoning: string = 'high'
): Promise<CreateSessionResponse> {
  return fetchJSON<CreateSessionResponse>('/api/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ model, reasoning }),
  });
}

export async function getSession(sessionId: string): Promise<{
  session_id: string;
  created_at: string;
  model: string | null;
  reasoning: string | null;
  message_count: number;
}> {
  return fetchJSON(`/api/chat/sessions/${sessionId}`);
}

export async function sendMessage(
  sessionId: string,
  message: string
): Promise<ChatResponse> {
  return fetchJSON<ChatResponse>(`/api/chat/sessions/${sessionId}/messages`, {
    method: 'POST',
    body: JSON.stringify({ message, stream: false }),
  });
}

/**
 * Send a message and stream the response.
 * 
 * @param sessionId - The chat session ID
 * @param message - The message to send
 * @param onChunk - Callback for each chunk of the response
 * @param onDone - Callback when streaming is complete
 * @param onError - Callback for errors
 */
export async function streamMessage(
  sessionId: string,
  message: string,
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: Error) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/sessions/${sessionId}/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new APIError('Stream request failed', response.status);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        onDone?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      
      // Process complete events
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            onDone?.();
            return;
          }
          
          if (data.startsWith('[ERROR]')) {
            throw new Error(data.slice(8));
          }
          
          // Unescape newlines
          const unescaped = data.replace(/\\n/g, '\n');
          onChunk(unescaped);
        }
      }
    }
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error(String(error)));
    throw error;
  }
}

/**
 * Quick chat with streaming - creates session automatically.
 */
export async function quickChatStream(
  message: string,
  onSessionId: (id: string) => void,
  onChunk: (chunk: string) => void,
  onDone?: () => void,
  onError?: (error: Error) => void,
  model?: string,
  reasoning: string = 'high'
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/api/chat/quick/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ message, model, reasoning }),
    });

    if (!response.ok) {
      throw new APIError('Stream request failed', response.status);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No response body');
    }

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        onDone?.();
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('event: session')) {
          // Session ID event
          const sessionLine = lines.find(l => l.startsWith('data: ') && !l.includes('['));
          if (sessionLine) {
            onSessionId(sessionLine.slice(6).trim());
          }
        } else if (line.startsWith('data: ')) {
          const data = line.slice(6);
          
          if (data === '[DONE]') {
            onDone?.();
            return;
          }
          
          if (data.startsWith('[ERROR]')) {
            throw new Error(data.slice(8));
          }
          
          const unescaped = data.replace(/\\n/g, '\n');
          onChunk(unescaped);
        }
      }
    }
  } catch (error) {
    onError?.(error instanceof Error ? error : new Error(String(error)));
    throw error;
  }
}

// ============================================================================
// Tools API
// ============================================================================

export async function getTools(filters?: {
  status?: string;
  category?: string;
  sport?: string;
}): Promise<ToolsListResponse> {
  const params = new URLSearchParams();
  if (filters?.status) params.set('status', filters.status);
  if (filters?.category) params.set('category', filters.category);
  if (filters?.sport) params.set('sport', filters.sport);
  
  const query = params.toString();
  return fetchJSON<ToolsListResponse>(`/api/tools${query ? `?${query}` : ''}`);
}

export async function getTool(toolId: string): Promise<Tool> {
  return fetchJSON<Tool>(`/api/tools/${toolId}`);
}

export async function getToolStats(): Promise<ToolStats> {
  return fetchJSON<ToolStats>('/api/tools/stats');
}

export async function voteForTool(toolId: string): Promise<{
  success: boolean;
  tool_id: string;
  new_vote_count: number;
}> {
  return fetchJSON(`/api/tools/${toolId}/vote`, {
    method: 'POST',
  });
}

// ============================================================================
// Daily Intro
// ============================================================================

export interface DailyIntroResponse {
  content: string;
  generated_at: string;
  games_featured: string[];
  sports: string[];
  date: string;
}

/**
 * Fetch the daily intro message.
 * 
 * Returns the dynamically generated intro for today, or a fallback if not available.
 */
export async function fetchDailyIntro(): Promise<DailyIntroResponse> {
  return fetchJSON<DailyIntroResponse>('/api/daily-intro');
}

// ============================================================================
// Health Check
// ============================================================================

export async function healthCheck(): Promise<{
  status: string;
  service: string;
}> {
  return fetchJSON('/health');
}

