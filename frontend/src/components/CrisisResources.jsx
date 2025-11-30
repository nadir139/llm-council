import './CrisisResources.css';

export default function CrisisResources() {
  return (
    <div className="crisis-resources">
      <div className="crisis-header">
        <span className="crisis-icon">🆘</span>
        <strong>CRISIS RESOURCES - IMMEDIATE HELP AVAILABLE</strong>
      </div>
      <div className="crisis-content">
        <p>If you're in crisis or experiencing thoughts of self-harm, please reach out immediately:</p>
        <ul className="crisis-list">
          <li>
            <strong>988 Suicide & Crisis Lifeline:</strong> Call or text <a href="tel:988">988</a>
            <span className="available-24-7"> (Available 24/7)</span>
          </li>
          <li>
            <strong>Crisis Text Line:</strong> Text HOME to <a href="sms:741741">741741</a>
            <span className="available-24-7"> (Available 24/7)</span>
          </li>
          <li>
            <strong>Emergency Services:</strong> Call <a href="tel:911">911</a> or go to your nearest emergency room
          </li>
          <li>
            <strong>International:</strong> Find resources at{' '}
            <a href="https://findahelpline.com" target="_blank" rel="noopener noreferrer">
              FindAHelpline.com
            </a>
          </li>
        </ul>
        <p className="crisis-note">
          Your life matters. Professional help is available right now. Please don't wait.
        </p>
      </div>
    </div>
  );
}
