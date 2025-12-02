import { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import Stage1 from './Stage1';
// Stage2 import removed - now hidden from users, kept in backend for analytics
import Stage3 from './Stage3';
import MedicalDisclaimer from './MedicalDisclaimer';
import CrisisResources from './CrisisResources';
import FollowUpForm from './FollowUpForm';
import './ChatInterface.css';

export default function ChatInterface({
  conversation,
  onSendMessage,
  isLoading,
  onSubmitFollowUp,  // New prop for Feature 3
  isFollowUpLoading, // New prop for Feature 3
}) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !isLoading) {
      onSendMessage(input);
      setInput('');
    }
  };

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  if (!conversation) {
    return (
      <div className="chat-interface">
        <div className="empty-state">
          <h2>Welcome to Wellness Partners,</h2>
          <p>A multidisciplinary AI self-reflection tool</p>
          <p>Create a new conversation to share your thoughts.</p>
          <p>Take your first step to get better, we are here to help.</p>
          <MedicalDisclaimer />
          </div>
      </div>
    );
  }

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {conversation.messages.length === 0 ? (
          <div className="empty-state">
            <h2>Wellness Partners</h2>
            <p>Share your wellness concerns to receive multidisciplinary perspectives</p>
            <MedicalDisclaimer />
          </div>
        ) : (
          <>
            <MedicalDisclaimer />
            {conversation.messages.map((msg, index) => (
              <div key={index} className="message-group">
                {msg.role === 'user' ? (
                  <div className="user-message">
                    <div className="message-label">You</div>
                    <div className="message-content">
                      <div className="markdown-content">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="assistant-message">
                    <div className="message-label">Wellness Council</div>

                    {/* Crisis Resources */}
                    {msg.metadata?.is_crisis && <CrisisResources />}

                    {/* Stage 1: Individual Professional Perspectives */}
                    {msg.loading?.stage1 && (
                      <div className="stage-loading">
                        <div className="spinner"></div>
                        <span>Gathering professional perspectives...</span>
                      </div>
                    )}
                    {msg.stage1 && <Stage1 responses={msg.stage1} />}

                    {/* Stage 2: HIDDEN FROM USERS
                        Stage 2 (peer review/rankings) still runs in the backend for analytics
                        and research purposes, but is no longer displayed to end users.
                        Admins can access Stage 2 data via: GET /api/admin/conversations/{id}/stage2
                    */}

                    {/* Stage 3: Final Synthesis */}
                    {msg.loading?.stage3 && (
                      <div className="stage-loading">
                        <div className="spinner"></div>
                        <span>Synthesizing integrative recommendation...</span>
                      </div>
                    )}
                    {msg.stage3 && <Stage3 finalResponse={msg.stage3} />}

                    {/* Feature 3: Show follow-up form after first report */}
                    {msg.stage3 &&
                      index === conversation.messages.length - 1 && // Last message
                      conversation.report_cycle === 0 && // First report cycle
                      !conversation.has_follow_up && // No follow-up submitted yet
                      !isLoading && // Not currently loading a new message
                      onSubmitFollowUp && ( // Handler is provided
                        <FollowUpForm
                          onSubmit={onSubmitFollowUp}
                          isLoading={isFollowUpLoading}
                        />
                      )}
                  </div>
                )}
              </div>
            ))}
          </>
        )}

        {isLoading && (
          <div className="loading-indicator">
            <div className="spinner"></div>
            <span>Consulting wellness professionals...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {conversation.messages.length === 0 && (
        <form className="input-form" onSubmit={handleSubmit}>
          <textarea
            className="message-input"
            placeholder="Share your wellness concern or question... (Shift+Enter for new line, Enter to send)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            rows={3}
          />
          <button
            type="submit"
            className="send-button"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </form>
      )}
    </div>
  );
}
