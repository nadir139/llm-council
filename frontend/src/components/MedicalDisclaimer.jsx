import './MedicalDisclaimer.css';

export default function MedicalDisclaimer() {
  return (
    <div className="medical-disclaimer">
      <div className="disclaimer-icon">⚠️</div>
      <div className="disclaimer-content">
        <strong>IMPORTANT MEDICAL DISCLAIMER</strong>
        <p>
          This is an AI wellness reflection tool for self-exploration purposes only.
          This is NOT a medical advice, or professional healthcare.
          Always consult with your doctor or healthcare professionals for medical, mental health, or wellness concerns.
        </p>
      </div>
    </div>
  );
}
