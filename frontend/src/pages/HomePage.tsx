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
      navigate(`/analyzing/${analysisId}`, { state: { inputType: activeTab } });
    }
  };

  const isSubmitDisabled =
    isLoading ||
    (activeTab === 'url' && !urlInput.trim()) ||
    (activeTab === 'text' && !textInput.trim()) ||
    (activeTab === 'file' && !selectedFile);

  return (
    <div className="home-page">
      {/* Hero */}
      <section className="hero">
        <div className="container">
          <div className="hero__content animate-fade-in-up">
            <div className="hero__badge">AI-Powered Analysis</div>
            <h1 className="hero__title">
              Know what you're{' '}
              <span className="hero__title-accent">agreeing to</span>
            </h1>
            <p className="hero__subtitle">
              TermsScope reads Terms of Service and Privacy Policies so you don't have to —
              surfacing hidden risks and what they actually mean for you.
            </p>
          </div>

          {/* Input Card */}
          <div className="input-card glass-card animate-fade-in-up delay-2">
            <div className="input-tabs">
              {(['url', 'text', 'file'] as InputTab[]).map((tab) => (
                <button
                  key={tab}
                  className={`input-tab${activeTab === tab ? ' input-tab--active' : ''}`}
                  onClick={() => setActiveTab(tab)}
                  type="button"
                >
                  {tab === 'url' ? 'URL' : tab === 'text' ? 'Paste text' : 'Upload file'}
                </button>
              ))}
            </div>

            <form onSubmit={handleSubmit} className="input-form">
              {activeTab === 'url' && (
                <input
                  type="url"
                  className="input input--large"
                  placeholder="https://example.com/terms-of-service"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  required
                />
              )}

              {activeTab === 'text' && (
                <textarea
                  className="textarea"
                  placeholder="Paste the Terms of Service or Privacy Policy here..."
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  rows={8}
                  required
                />
              )}

              {activeTab === 'file' && (
                <FileDropzone onFileSelect={setSelectedFile} />
              )}

              {error && (
                <div className="input-form__error">{error}</div>
              )}

              <button
                type="submit"
                className="btn btn-primary btn--full"
                disabled={isSubmitDisabled}
              >
                {isLoading ? (
                  <>
                    <span className="spinner" />
                    Analysing...
                  </>
                ) : (
                  'Analyse document'
                )}
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="how-it-works">
        <div className="container">
          <h2 className="section-title animate-fade-in">How it works</h2>
          <div className="steps">
            <div className="step glass-card animate-fade-in-up delay-1">
              <div className="step__number">1</div>
              <h3>Submit</h3>
              <p>Paste a URL, copy the text, or upload a PDF of any Terms of Service or Privacy Policy.</p>
            </div>
            <div className="step glass-card animate-fade-in-up delay-2">
              <div className="step__number">2</div>
              <h3>AI analyses</h3>
              <p>Our AI pipeline reads the document across five risk categories — Privacy, Financial, Data Rights, Cancellation, and Liability.</p>
            </div>
            <div className="step glass-card animate-fade-in-up delay-3">
              <div className="step__number">3</div>
              <h3>Get results</h3>
              <p>Receive a trust score, clause-by-clause breakdown, and plain-English explanations of what you're agreeing to.</p>
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
              <h4>Privacy</h4>
              <p>Understand what data is collected and how it's used.</p>
            </div>
            <div className="feature animate-fade-in delay-2">
              <span className="feature__icon">💰</span>
              <h4>Financial</h4>
              <p>Uncover hidden fees, auto-renewals, and billing traps.</p>
            </div>
            <div className="feature animate-fade-in delay-3">
              <span className="feature__icon">📊</span>
              <h4>Data rights</h4>
              <p>Know who owns your content and data.</p>
            </div>
            <div className="feature animate-fade-in delay-4">
              <span className="feature__icon">⚖️</span>
              <h4>Liability</h4>
              <p>Spot forced arbitration and liability waivers.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default HomePage;
