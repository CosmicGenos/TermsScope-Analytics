import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAnalysis } from '../hooks/useAnalysis';
import FileDropzone from '../components/FileDropzone';
import './HomePage.css';

type InputTab = 'url' | 'text' | 'file';

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { submitUrl, submitText, submitFile, error, isLoading } = useAnalysis();
  const [activeTab, setActiveTab] = useState<InputTab>('url');
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    let analysisId: string | null = null;

    if (activeTab === 'url') {
      if (!urlInput.trim()) return;
      analysisId = await submitUrl(urlInput.trim());
    } else if (activeTab === 'text') {
      if (!textInput.trim()) return;
      analysisId = await submitText(textInput.trim());
    } else if (activeTab === 'file') {
      if (!selectedFile) return;
      analysisId = await submitFile(selectedFile);
    }

    if (analysisId) {
      navigate(`/analyzing/${analysisId}`);
    }
  };

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero">
        <div className="container">
          <div className="hero__content animate-fade-in-up">
            <div className="hero__badge">🛡️ AI-Powered Analysis</div>
            <h1 className="hero__title">
              Know What You're{' '}
              <span className="hero__title-accent">Agreeing To</span>
            </h1>
            <p className="hero__subtitle">
              TermsScope analyzes Terms of Service and Privacy Policies using AI to
              identify hidden risks, unfair clauses, and what they really mean for you
              — in plain English.
            </p>
          </div>

          {/* Input Form */}
          <div className="input-section glass-card animate-fade-in-up delay-2">
            <div className="input-tabs">
              <button
                className={`input-tab ${activeTab === 'url' ? 'input-tab--active' : ''}`}
                onClick={() => setActiveTab('url')}
              >
                🔗 URL
              </button>
              <button
                className={`input-tab ${activeTab === 'text' ? 'input-tab--active' : ''}`}
                onClick={() => setActiveTab('text')}
              >
                📝 Paste Text
              </button>
              <button
                className={`input-tab ${activeTab === 'file' ? 'input-tab--active' : ''}`}
                onClick={() => setActiveTab('file')}
              >
                📄 Upload File
              </button>
            </div>

            <form onSubmit={handleSubmit} className="input-form">
              {activeTab === 'url' && (
                <div className="input-form__field">
                  <input
                    type="url"
                    className="input input--large"
                    placeholder="https://example.com/terms-of-service"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    required
                  />
                </div>
              )}

              {activeTab === 'text' && (
                <div className="input-form__field">
                  <textarea
                    className="textarea"
                    placeholder="Paste the Terms of Service or Privacy Policy text here..."
                    value={textInput}
                    onChange={(e) => setTextInput(e.target.value)}
                    rows={8}
                    required
                  />
                </div>
              )}

              {activeTab === 'file' && (
                <div className="input-form__field">
                  <FileDropzone onFileSelect={setSelectedFile} />
                </div>
              )}

              {error && <div className="input-form__error">❌ {error}</div>}

              <button
                type="submit"
                className="btn btn-primary btn--large"
                disabled={
                  isLoading ||
                  (activeTab === 'url' && !urlInput.trim()) ||
                  (activeTab === 'text' && !textInput.trim()) ||
                  (activeTab === 'file' && !selectedFile)
                }
              >
                {isLoading ? (
                  <>
                    <span className="spinner" /> Analyzing...
                  </>
                ) : (
                  <>🔍 Analyze Document</>
                )}
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="how-it-works">
        <div className="container">
          <h2 className="section-title animate-fade-in">How It Works</h2>
          <div className="steps">
            <div className="step glass-card animate-fade-in-up delay-1">
              <div className="step__number">1</div>
              <div className="step__icon">📥</div>
              <h3>Submit</h3>
              <p>Paste a URL, copy the text, or upload a PDF of any Terms of Service or Privacy Policy.</p>
            </div>
            <div className="step glass-card animate-fade-in-up delay-2">
              <div className="step__number">2</div>
              <div className="step__icon">🤖</div>
              <h3>AI Analyzes</h3>
              <p>Our LLM pipeline dissects the document across 5 risk categories: Privacy, Financial, Data Rights, Cancellation, and Liability.</p>
            </div>
            <div className="step glass-card animate-fade-in-up delay-3">
              <div className="step__number">3</div>
              <div className="step__icon">📊</div>
              <h3>Get Results</h3>
              <p>Receive a clear trust score, clause-by-clause breakdown, and plain-English explanations of what you're agreeing to.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features">
        <div className="container">
          <div className="features__grid">
            <div className="feature animate-fade-in delay-1">
              <span className="feature__icon">🔐</span>
              <h4>Privacy Analysis</h4>
              <p>Understand what data is collected and how it's used.</p>
            </div>
            <div className="feature animate-fade-in delay-2">
              <span className="feature__icon">💰</span>
              <h4>Financial Risks</h4>
              <p>Uncover hidden fees, auto-renewals, and billing traps.</p>
            </div>
            <div className="feature animate-fade-in delay-3">
              <span className="feature__icon">📊</span>
              <h4>Data Rights</h4>
              <p>Know who owns your content and data.</p>
            </div>
            <div className="feature animate-fade-in delay-4">
              <span className="feature__icon">⚖️</span>
              <h4>Legal Protections</h4>
              <p>Spot forced arbitration and liability waivers.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
