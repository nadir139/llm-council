import ReactMarkdown from 'react-markdown';
import './Stage3.css';

export default function Stage3({ finalResponse }) {
  if (!finalResponse) {
    return null;
  }

  return (
    <div className="stage stage3">
      <h3 className="stage-title">Stage 3: Integrative Wellness Recommendation</h3>
      <p className="stage-description">
        A holistic synthesis combining all professional perspectives into a comprehensive, person-centered recommendation.
      </p>
      <div className="final-response">
        <div className="chairman-label">
          Integrative Wellness Coordinator: {finalResponse.model.split('/')[1] || finalResponse.model}
        </div>
        <div className="final-text markdown-content">
          <ReactMarkdown>{finalResponse.response}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
