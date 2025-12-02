import { useState } from 'react';
import './FollowUpForm.css';

/**
 * FollowUpForm Component (Feature 3: Report Interaction Flow)
 *
 * Displays after the first report to collect additional context from the user.
 * This enables the council to generate a more personalized second report
 * based on follow-up information.
 *
 * Props:
 * - onSubmit: Function called with follow-up text when user submits
 * - isLoading: Boolean indicating if submission is in progress
 */
export default function FollowUpForm({ onSubmit, isLoading }) {
  const [followUpText, setFollowUpText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();

    // Validate that user entered something
    if (!followUpText.trim()) {
      alert('Please provide some follow-up information before submitting.');
      return;
    }

    // Call parent handler
    onSubmit(followUpText);
  };

  return (
    <div className="follow-up-form-container">
      <div className="follow-up-header">
        <h3 className="follow-up-title">📋 Follow-Up Questions</h3>
        <p className="follow-up-subtitle">
          To provide more personalized guidance, please answer the following:
        </p>
      </div>

      <div className="follow-up-questions-list">
        <ol>
          <li>Are there any specific symptoms or experiences you'd like to share in more detail?</li>
          <li>Have you tried any approaches or strategies so far? If so, what were the results?</li>
          <li>What specific areas would you like the wellness team to focus on?</li>
          <li>Is there anything else about your situation that might be relevant?</li>
        </ol>
      </div>

      <form onSubmit={handleSubmit} className="follow-up-form">
        <textarea
          value={followUpText}
          onChange={(e) => setFollowUpText(e.target.value)}
          placeholder="Share any additional details about your situation, what you've tried, or what you'd like guidance on..."
          className="follow-up-textarea"
          rows={8}
          disabled={isLoading}
        />

        <div className="follow-up-actions">
          <button
            type="submit"
            className="follow-up-submit-btn"
            disabled={isLoading || !followUpText.trim()}
          >
            {isLoading ? (
              <>
                <span className="loading-spinner"></span>
                Generating Second Report...
              </>
            ) : (
              <>
                Generate Detailed Report →
              </>
            )}
          </button>
        </div>

        <p className="follow-up-note">
          💡 <strong>Note:</strong> Your follow-up information will help the wellness council provide more
          targeted and personalized recommendations in the second report.
        </p>
      </form>
    </div>
  );
}
