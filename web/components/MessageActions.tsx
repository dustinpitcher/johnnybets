'use client';

import { useState } from 'react';
import Modal, { ModalFooter, ModalButton } from './Modal';

interface MessageActionsProps {
  messageId: string;
  content: string;
  sessionId?: string | null;
}

export default function MessageActions({ messageId, content, sessionId }: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);
  const [feedbackComment, setFeedbackComment] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleShare = async () => {
    const shareUrl = sessionId 
      ? `${window.location.origin}/?session=${sessionId}`
      : window.location.href;

    if (navigator.share) {
      try {
        await navigator.share({
          title: 'JohnnyBets Analysis',
          text: content.slice(0, 200) + (content.length > 200 ? '...' : ''),
          url: shareUrl,
        });
      } catch (err) {
        // User cancelled or error
        if ((err as Error).name !== 'AbortError') {
          // Fallback to copy link
          await navigator.clipboard.writeText(shareUrl);
          alert('Link copied to clipboard!');
        }
      }
    } else {
      // Fallback: copy link
      await navigator.clipboard.writeText(shareUrl);
      alert('Link copied to clipboard!');
    }
  };

  const handleFeedback = (type: 'up' | 'down') => {
    setFeedback(type);
    setShowFeedbackModal(true);
  };

  const handleCloseModal = () => {
    setShowFeedbackModal(false);
    setFeedbackComment('');
  };

  const submitFeedback = async () => {
    setIsSubmitting(true);
    try {
      // Fetch session context for the feedback report (if session exists)
      let contextSnapshot = null;
      if (sessionId) {
        try {
          const contextRes = await fetch(`/api/sessions/${sessionId}/context`);
          if (contextRes.ok) {
            contextSnapshot = await contextRes.json();
          }
        } catch (contextErr) {
          // Context fetch is optional, continue without it
          console.warn('Could not fetch session context:', contextErr);
        }
      }

      // Save feedback to database via API with context
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messageId,
          type: feedback,
          comment: feedbackComment || undefined,
          sessionId: sessionId || undefined,
          messageContent: content.slice(0, 1000), // Store first 1000 chars for context
          contextSnapshot,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      setFeedbackSubmitted(true);
      handleCloseModal();
      
      // Reset after a delay
      setTimeout(() => setFeedbackSubmitted(false), 3000);
    } catch (err) {
      console.error('Failed to submit feedback:', err);
      alert('Failed to submit feedback. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      {/* Action buttons */}
      <div className="flex items-center gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
        {/* Copy button */}
        <button
          onClick={handleCopy}
          className="p-1.5 text-terminal-muted hover:text-terminal-accent hover:bg-terminal-surface 
                   rounded transition-colors"
          title="Copy response"
        >
          {copied ? (
            <svg className="w-4 h-4 text-terminal-accent" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          )}
        </button>

        {/* Share button */}
        <button
          onClick={handleShare}
          className="p-1.5 text-terminal-muted hover:text-terminal-accent hover:bg-terminal-surface 
                   rounded transition-colors"
          title="Share"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
              d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
          </svg>
        </button>

        {/* Divider */}
        <div className="w-px h-4 bg-terminal-border mx-1" />

        {/* Thumbs up */}
        <button
          onClick={() => handleFeedback('up')}
          className={`p-1.5 rounded transition-colors ${
            feedback === 'up' && feedbackSubmitted
              ? 'text-terminal-accent bg-terminal-accent/20' 
              : 'text-terminal-muted hover:text-terminal-accent hover:bg-terminal-surface'
          }`}
          title="Good response"
        >
          <svg className="w-4 h-4" fill={feedback === 'up' && feedbackSubmitted ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
              d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
          </svg>
        </button>

        {/* Thumbs down */}
        <button
          onClick={() => handleFeedback('down')}
          className={`p-1.5 rounded transition-colors ${
            feedback === 'down' && feedbackSubmitted
              ? 'text-terminal-error bg-terminal-error/20' 
              : 'text-terminal-muted hover:text-terminal-error hover:bg-terminal-surface'
          }`}
          title="Poor response"
        >
          <svg className="w-4 h-4" fill={feedback === 'down' && feedbackSubmitted ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
              d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
          </svg>
        </button>

        {/* Feedback submitted indicator */}
        {feedbackSubmitted && (
          <span className="text-xs text-terminal-accent ml-2">Thanks!</span>
        )}
      </div>

      {/* Feedback Modal */}
      <Modal
        isOpen={showFeedbackModal}
        onClose={handleCloseModal}
        title={feedback === 'up' ? 'What did you like?' : 'What went wrong?'}
        size="md"
      >
        <p className="text-sm text-terminal-muted mb-4">
          Your feedback helps us improve. (Optional)
        </p>
        
        <textarea
          value={feedbackComment}
          onChange={(e) => setFeedbackComment(e.target.value)}
          placeholder={
            feedback === 'up' 
              ? 'The analysis was accurate, helpful tips...' 
              : 'Incorrect information, missing context...'
          }
          className="w-full h-24 px-3 py-2 bg-terminal-bg border border-terminal-border rounded-lg
                   text-terminal-text placeholder-terminal-muted resize-none
                   focus:border-terminal-accent focus:ring-1 focus:ring-terminal-accent focus:outline-none"
          autoFocus
        />
        
        <ModalFooter>
          <ModalButton onClick={handleCloseModal} variant="secondary">
            Cancel
          </ModalButton>
          <ModalButton 
            onClick={submitFeedback} 
            variant="primary"
            disabled={isSubmitting}
          >
            {isSubmitting ? 'Submitting...' : 'Submit'}
          </ModalButton>
        </ModalFooter>
      </Modal>
    </>
  );
}
