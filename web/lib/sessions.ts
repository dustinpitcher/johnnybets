/**
 * Session Storage Utility
 * 
 * Dual storage strategy:
 * - Authenticated users: Sync to database via API
 * - Anonymous users: localStorage only
 */

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: string;
  updatedAt: string;
  tags: string[];
}

const STORAGE_KEY = 'johnnybets_sessions';

// =============================================================================
// LOCAL STORAGE FUNCTIONS (for anonymous users)
// =============================================================================

function getLocalSessions(): ChatSession[] {
  if (typeof window === 'undefined') return [];
  
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return [];
    
    const sessions = JSON.parse(data) as ChatSession[];
    return sessions.sort((a, b) => 
      new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
  } catch {
    return [];
  }
}

function getLocalSession(id: string): ChatSession | null {
  const sessions = getLocalSessions();
  return sessions.find(s => s.id === id) || null;
}

function saveLocalSessions(sessions: ChatSession[]): void {
  if (typeof window === 'undefined') return;
  
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
  } catch (e) {
    console.error('Failed to save sessions:', e);
  }
}

function createLocalSession(firstMessage?: string): ChatSession {
  const now = new Date().toISOString();
  const session: ChatSession = {
    id: `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    title: firstMessage 
      ? firstMessage.slice(0, 50) + (firstMessage.length > 50 ? '...' : '')
      : 'New Session',
    messages: [],
    createdAt: now,
    updatedAt: now,
    tags: [],
  };
  
  const sessions = getLocalSessions();
  sessions.unshift(session);
  saveLocalSessions(sessions);
  
  return session;
}

function updateLocalSession(id: string, updates: Partial<ChatSession>): ChatSession | null {
  const sessions = getLocalSessions();
  const index = sessions.findIndex(s => s.id === id);
  
  if (index === -1) return null;
  
  sessions[index] = {
    ...sessions[index],
    ...updates,
    updatedAt: new Date().toISOString(),
  };
  
  saveLocalSessions(sessions);
  return sessions[index];
}

function addLocalMessage(sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>): ChatSession | null {
  const session = getLocalSession(sessionId);
  if (!session) return null;
  
  const newMessage: ChatMessage = {
    ...message,
    id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    timestamp: new Date().toISOString(),
  };
  
  const messages = [...session.messages, newMessage];
  
  let title = session.title;
  if (title === 'New Session' && message.role === 'user') {
    title = message.content.slice(0, 50) + (message.content.length > 50 ? '...' : '');
  }
  
  const tags = extractTags(messages);
  
  return updateLocalSession(sessionId, { messages, title, tags });
}

function deleteLocalSession(id: string): boolean {
  const sessions = getLocalSessions();
  const filtered = sessions.filter(s => s.id !== id);
  
  if (filtered.length === sessions.length) return false;
  
  saveLocalSessions(filtered);
  return true;
}

// =============================================================================
// API FUNCTIONS (for authenticated users)
// =============================================================================

async function getApiSessions(): Promise<ChatSession[]> {
  try {
    const res = await fetch('/api/sessions');
    if (!res.ok) {
      if (res.status === 401) return []; // Not authenticated
      throw new Error('Failed to fetch sessions');
    }
    return await res.json();
  } catch (error) {
    console.error('Failed to fetch sessions from API:', error);
    return [];
  }
}

async function getApiSession(id: string): Promise<ChatSession | null> {
  try {
    const res = await fetch(`/api/sessions/${id}`);
    if (!res.ok) {
      if (res.status === 401 || res.status === 404) return null;
      throw new Error('Failed to fetch session');
    }
    return await res.json();
  } catch (error) {
    console.error('Failed to fetch session from API:', error);
    return null;
  }
}

async function createApiSession(firstMessage?: string): Promise<ChatSession> {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ firstMessage }),
  });
  
  if (!res.ok) {
    throw new Error('Failed to create session');
  }
  
  return await res.json();
}

async function updateApiSession(id: string, updates: Partial<ChatSession>): Promise<ChatSession | null> {
  try {
    const res = await fetch(`/api/sessions/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error('Failed to update session:', error);
    return null;
  }
}

async function addApiMessage(sessionId: string, message: Omit<ChatMessage, 'id' | 'timestamp'>): Promise<ChatMessage | null> {
  try {
    const res = await fetch(`/api/sessions/${sessionId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message),
    });
    
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.error('Failed to add message:', error);
    return null;
  }
}

async function deleteApiSession(id: string): Promise<boolean> {
  try {
    const res = await fetch(`/api/sessions/${id}`, {
      method: 'DELETE',
    });
    return res.ok;
  } catch (error) {
    console.error('Failed to delete session:', error);
    return false;
  }
}

// =============================================================================
// UNIFIED INTERFACE (auto-selects based on auth state)
// =============================================================================

/**
 * Get all sessions for the current user
 * @param isAuthenticated - Whether the user is signed in
 */
export async function getSessions(isAuthenticated: boolean): Promise<ChatSession[]> {
  if (isAuthenticated) {
    return await getApiSessions();
  }
  return getLocalSessions();
}

/**
 * Get a single session by ID
 * @param id - Session ID
 * @param isAuthenticated - Whether the user is signed in
 */
export async function getSession(id: string, isAuthenticated: boolean): Promise<ChatSession | null> {
  if (isAuthenticated) {
    return await getApiSession(id);
  }
  return getLocalSession(id);
}

/**
 * Create a new session
 * @param firstMessage - Optional first message to use for title
 * @param isAuthenticated - Whether the user is signed in
 */
export async function createSession(firstMessage?: string, isAuthenticated?: boolean): Promise<ChatSession> {
  if (isAuthenticated) {
    return await createApiSession(firstMessage);
  }
  return createLocalSession(firstMessage);
}

/**
 * Update a session
 * @param id - Session ID
 * @param updates - Fields to update
 * @param isAuthenticated - Whether the user is signed in
 */
export async function updateSession(
  id: string, 
  updates: Partial<ChatSession>, 
  isAuthenticated: boolean
): Promise<ChatSession | null> {
  if (isAuthenticated) {
    return await updateApiSession(id, updates);
  }
  return updateLocalSession(id, updates);
}

/**
 * Add a message to a session
 * @param sessionId - Session ID
 * @param message - Message to add (without id/timestamp)
 * @param isAuthenticated - Whether the user is signed in
 */
export async function addMessage(
  sessionId: string, 
  message: Omit<ChatMessage, 'id' | 'timestamp'>,
  isAuthenticated: boolean
): Promise<ChatSession | ChatMessage | null> {
  if (isAuthenticated) {
    return await addApiMessage(sessionId, message);
  }
  return addLocalMessage(sessionId, message);
}

/**
 * Delete a session
 * @param id - Session ID
 * @param isAuthenticated - Whether the user is signed in
 */
export async function deleteSession(id: string, isAuthenticated: boolean): Promise<boolean> {
  if (isAuthenticated) {
    return await deleteApiSession(id);
  }
  return deleteLocalSession(id);
}

// =============================================================================
// HELPERS
// =============================================================================

function extractTags(messages: ChatMessage[]): string[] {
  const tagSet = new Set<string>();
  
  const teams = [
    'NFL', 'NHL', 'MLB', 'NBA',
    'Bills', 'Chiefs', 'Eagles', 'Cowboys', 'Patriots', '49ers', 'Packers', 'Bears',
    'Rangers', 'Bruins', 'Maple Leafs', 'Oilers', 'Penguins', 'Capitals',
    'Yankees', 'Dodgers', 'Red Sox', 'Cubs', 'Mets', 'Astros',
  ];
  
  const allText = messages
    .filter(m => m.role === 'user')
    .map(m => m.content)
    .join(' ');
  
  for (const team of teams) {
    if (allText.toLowerCase().includes(team.toLowerCase())) {
      tagSet.add(team);
    }
  }
  
  return Array.from(tagSet).slice(0, 5);
}
