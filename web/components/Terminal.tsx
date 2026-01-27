'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useSession } from 'next-auth/react';
import { createSession as createApiSession, streamMessage } from '@/lib/api';
import * as sessionStorage from '@/lib/sessions';
import MessageActions from './MessageActions';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  role: 'system',
  content: `Oh good, another person who wants to beat the books. At least you came to someone who knows what they're doing. I'm **JohnnyBets**.

Look, here's the deal:
- 📊 **Live Odds** from every book that matters
- 🏈 **Super Bowl LX** analysis — Pats vs Seahawks, and yes I have thoughts
- 🎯 **Prop Alpha** player analysis using actual data, not vibes
- 🏒 **NHL Goalie Alpha** because save props are free money if you're not lazy
- 📈 **Arbitrage Scanner** for people who like math over luck

Ask me something. And please, make it interesting.`,
  timestamp: new Date(),
};

interface TerminalProps {
  activeSessionId?: string | null;
  onSessionChange?: (sessionId: string) => void;
  externalMessage?: string | null;
  onExternalMessageHandled?: () => void;
  populateMessage?: string | null;
  onPopulateHandled?: () => void;
}

export default function Terminal({ 
  activeSessionId,
  onSessionChange,
  externalMessage,
  onExternalMessageHandled,
  populateMessage,
  onPopulateHandled,
}: TerminalProps) {
  const { data: authSession, status: authStatus } = useSession();
  const isAuthenticated = authStatus === 'authenticated';
  
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [apiSessionId, setApiSessionId] = useState<string | null>(null);
  const [localSessionId, setLocalSessionId] = useState<string | null>(null);
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const localSessionIdRef = useRef<string | null>(null);

  // Keep ref in sync with state
  useEffect(() => {
    localSessionIdRef.current = localSessionId;
  }, [localSessionId]);

  // Load session when activeSessionId changes from parent
  useEffect(() => {
    // Wait for auth status to resolve before loading
    if (authStatus === 'loading') {
      return;
    }
    
    // Skip if we already have this session loaded (we just created it)
    if (activeSessionId && activeSessionId === localSessionIdRef.current) {
      return;
    }
    
    if (activeSessionId) {
      // Load session (async for authenticated users)
      const loadSession = async () => {
        const session = await sessionStorage.getSession(activeSessionId, isAuthenticated);
        if (session) {
          setLocalSessionId(activeSessionId);
          setApiSessionId(null); // Reset API session when loading different local session
          // Convert stored messages to display format
          const loadedMessages: Message[] = session.messages.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            timestamp: new Date(m.timestamp),
          }));
          setMessages(loadedMessages.length > 0 ? loadedMessages : [WELCOME_MESSAGE]);
        } else {
          // Session not found
          setMessages([WELCOME_MESSAGE]);
          setLocalSessionId(null);
        }
      };
      loadSession();
    } else if (activeSessionId === null) {
      // Explicitly null means new session - reset to welcome
      setMessages([WELCOME_MESSAGE]);
      setLocalSessionId(null);
      setApiSessionId(null);
    }
    // If activeSessionId is undefined (initial mount), don't reset
  }, [activeSessionId, isAuthenticated, authStatus]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Handle external message (e.g., from prompt suggestions - auto-submits)
  useEffect(() => {
    if (externalMessage && !isLoading) {
      handleSubmit(undefined, externalMessage);
      onExternalMessageHandled?.();
    }
  }, [externalMessage]);

  // Handle populate message (e.g., from ticker click - just populates input, doesn't submit)
  useEffect(() => {
    if (populateMessage) {
      setInput(populateMessage);
      inputRef.current?.focus();
      onPopulateHandled?.();
    }
  }, [populateMessage, onPopulateHandled]);

  const handleSubmit = useCallback(async (e?: React.FormEvent, overrideMessage?: string) => {
    e?.preventDefault();
    
    const messageText = overrideMessage || input.trim();
    if (!messageText || isLoading) return;

    // Add to command history
    setCommandHistory(prev => [...prev, messageText]);
    setHistoryIndex(-1);
    setInput('');

    // Create local session if needed (on first message)
    let currentLocalSessionId = localSessionId;
    if (!currentLocalSessionId) {
      const newSession = await sessionStorage.createSession(messageText, isAuthenticated);
      currentLocalSessionId = newSession.id;
      setLocalSessionId(currentLocalSessionId);
      onSessionChange?.(currentLocalSessionId);
    }

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: messageText,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMessage]);

    // Save user message to storage
    await sessionStorage.addMessage(currentLocalSessionId, {
      role: 'user',
      content: messageText,
    }, isAuthenticated);

    // Create assistant message placeholder
    const assistantId = `assistant-${Date.now()}`;
    setMessages(prev => [...prev, {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    }]);

    setIsLoading(true);

    try {
      // Create API session if needed
      let currentApiSessionId = apiSessionId;
      if (!currentApiSessionId) {
        const session = await createApiSession();
        currentApiSessionId = session.session_id;
        setApiSessionId(currentApiSessionId);
      }

      // Collect full response for saving
      let fullResponse = '';

      // Stream the response
      await streamMessage(
        currentApiSessionId,
        messageText,
        (chunk) => {
          fullResponse += chunk;
          setMessages(prev => prev.map(msg => 
            msg.id === assistantId
              ? { ...msg, content: msg.content + chunk }
              : msg
          ));
        },
        async () => {
          setMessages(prev => prev.map(msg => 
            msg.id === assistantId
              ? { ...msg, isStreaming: false }
              : msg
          ));
          setIsLoading(false);

          // Save assistant message to storage
          if (currentLocalSessionId) {
            await sessionStorage.addMessage(currentLocalSessionId, {
              role: 'assistant',
              content: fullResponse,
            }, isAuthenticated);
            onSessionChange?.(currentLocalSessionId);
          }
        },
        async (error) => {
          const errorContent = `Error: ${error.message}`;
          setMessages(prev => prev.map(msg => 
            msg.id === assistantId
              ? { ...msg, content: errorContent, isStreaming: false }
              : msg
          ));
          setIsLoading(false);

          // Save error message
          if (currentLocalSessionId) {
            await sessionStorage.addMessage(currentLocalSessionId, {
              role: 'assistant',
              content: errorContent,
            }, isAuthenticated);
          }
        }
      );
    } catch (error) {
      console.error('Chat error:', error);
      setIsLoading(false);
    }
  }, [input, isLoading, apiSessionId, localSessionId, onSessionChange, isAuthenticated]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Cmd+Enter (Mac) or Ctrl+Enter (Win/Linux)
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
      return;
    }

    // Handle up/down for command history (only when at start/end of input)
    if (e.key === 'ArrowUp') {
      // Only navigate history if cursor is at the beginning or input is empty
      const textarea = e.currentTarget;
      if (textarea.selectionStart === 0 && textarea.selectionEnd === 0) {
        e.preventDefault();
        if (commandHistory.length > 0) {
          const newIndex = historyIndex < commandHistory.length - 1 
            ? historyIndex + 1 
            : historyIndex;
          setHistoryIndex(newIndex);
          setInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
        }
      }
    } else if (e.key === 'ArrowDown') {
      // Only navigate history if cursor is at the end
      const textarea = e.currentTarget;
      if (textarea.selectionStart === textarea.value.length) {
        e.preventDefault();
        if (historyIndex > 0) {
          const newIndex = historyIndex - 1;
          setHistoryIndex(newIndex);
          setInput(commandHistory[commandHistory.length - 1 - newIndex] || '');
        } else {
          setHistoryIndex(-1);
          setInput('');
        }
      }
    }
  };

  return (
    <div 
      className="flex flex-col h-full bg-terminal-bg text-[0.85em]"
      onClick={() => inputRef.current?.focus()}
    >
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`animate-fade-in group ${
              message.role === 'user' ? 'pl-4' : ''
            }`}
          >
            {/* Role indicator */}
            <div className="flex items-center gap-2 mb-1">
              {message.role === 'user' ? (
                <>
                  <span className="text-terminal-accent font-bold">{'>'}</span>
                  <span className="text-terminal-muted text-xs">you</span>
                </>
              ) : message.role === 'assistant' ? (
                <>
                  <span className="text-terminal-warning font-bold">$</span>
                  <span className="text-terminal-muted text-xs">johnny</span>
                  {message.isStreaming && (
                    <span className="text-terminal-muted text-xs loading-dots">thinking</span>
                  )}
                </>
              ) : (
                <span className="text-terminal-info font-bold">#</span>
              )}
            </div>
            
            {/* Message content */}
            <div className={`ml-4 ${message.role === 'user' ? 'text-terminal-text' : 'prose-terminal'}`}>
              {message.role === 'user' ? (
                <span>{message.content}</span>
              ) : (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {message.content || (message.isStreaming ? '▊' : '')}
                </ReactMarkdown>
              )}
              {message.isStreaming && message.content && (
                <span className="animate-cursor-blink text-terminal-accent">▊</span>
              )}
            </div>

            {/* Action buttons for assistant messages (not streaming) */}
            {message.role === 'assistant' && !message.isStreaming && message.content && (
              <div className="ml-4">
                <MessageActions 
                  messageId={message.id}
                  content={message.content}
                  sessionId={localSessionId}
                />
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="border-t border-terminal-border p-4">
        <div className="flex items-start gap-2">
          <span className="text-terminal-accent font-bold mt-2">{'>'}</span>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              // Auto-resize textarea
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
            }}
            onKeyDown={handleKeyDown}
            placeholder={isLoading ? 'Thinking...' : 'Ask Johnny...'}
            disabled={isLoading}
            className="flex-1 bg-transparent border-none outline-none text-terminal-text placeholder-terminal-muted font-mono resize-none min-h-[40px] max-h-[150px] overflow-y-auto py-2 leading-relaxed text-[16px]"
            autoComplete="off"
            autoCorrect="off"
            autoCapitalize="off"
            spellCheck={false}
            rows={1}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="flex-shrink-0 w-11 h-11 flex items-center justify-center rounded bg-terminal-surface border border-terminal-border hover:border-terminal-accent hover:bg-terminal-accent/10 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-terminal-border disabled:hover:bg-terminal-surface transition-colors"
            aria-label="Send message"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-terminal-accent border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                className="w-5 h-5 text-terminal-accent"
              >
                <path d="M22 2L11 13" />
                <path d="M22 2L15 22L11 13L2 9L22 2Z" />
              </svg>
            )}
          </button>
        </div>
        <div className="hidden md:block text-terminal-muted text-xs mt-2 ml-6">
          Press <kbd className="px-1.5 py-0.5 bg-terminal-surface rounded text-terminal-text">⌘</kbd>+<kbd className="px-1.5 py-0.5 bg-terminal-surface rounded text-terminal-text">Enter</kbd> to send
        </div>
      </form>
    </div>
  );
}
