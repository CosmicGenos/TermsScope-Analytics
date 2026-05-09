import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { loginWithEmail, registerWithEmail } from '../services/api';
import './AuthModal.css';

type Mode = 'signup' | 'signin';

interface Props {
  onClose: () => void;
  initialMode?: Mode;
}

const AuthModal: React.FC<Props> = ({ onClose, initialMode = 'signup' }) => {
  const { setToken, loginWithGoogle } = useAuth();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const switchMode = (next: Mode) => {
    setMode(next);
    setError('');
  };

  const validate = (): string => {
    if (mode === 'signup' && !name.trim()) return 'Full name is required.';
    if (!email.trim()) return 'Email is required.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return 'Enter a valid email address.';
    if (!password) return 'Password is required.';
    if (mode === 'signup' && password.length < 8) return 'Password must be at least 8 characters.';
    return '';
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const msg = validate();
    if (msg) { setError(msg); return; }

    setIsSubmitting(true);
    setError('');

    try {
      const res = mode === 'signup'
        ? await registerWithEmail(name.trim(), email.trim(), password)
        : await loginWithEmail(email.trim(), password);

      setToken(res.data.token);
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOverlayClick = (e: React.MouseEvent) => {
    if (e.target === overlayRef.current) onClose();
  };

  const isSignUp = mode === 'signup';

  return (
    <div className="auth-overlay" ref={overlayRef} onClick={handleOverlayClick}>
      <div className="auth-modal" role="dialog" aria-modal="true" aria-label="Sign in">

        {/* Header */}
        <div className="auth-modal__header">
          <div className="auth-modal__tabs">
            <button
              className={`auth-modal__tab ${isSignUp ? 'auth-modal__tab--active' : ''}`}
              onClick={() => switchMode('signup')}
              type="button"
            >
              Sign Up
            </button>
            <button
              className={`auth-modal__tab ${!isSignUp ? 'auth-modal__tab--active' : ''}`}
              onClick={() => switchMode('signin')}
              type="button"
            >
              Sign In
            </button>
          </div>
          <button className="auth-modal__close" onClick={onClose} aria-label="Close" type="button">
            <CloseIcon />
          </button>
        </div>

        {/* Title */}
        <div className="auth-modal__title-block">
          <h2 className="auth-modal__title">
            {isSignUp ? 'Create your account' : 'Welcome back'}
          </h2>
          <p className="auth-modal__subtitle">
            {isSignUp
              ? 'Analyze Terms of Service and Privacy Policies with AI.'
              : 'Sign in to access your analysis history.'}
          </p>
        </div>

        {/* Form */}
        <form className="auth-modal__form" onSubmit={handleSubmit} noValidate>

          {/* Full Name — slides in for Sign Up */}
          <div className={`auth-modal__field-wrap ${isSignUp ? 'auth-modal__field-wrap--visible' : ''}`}>
            <div className="auth-modal__field">
              <label className="auth-modal__label" htmlFor="auth-name">Full Name</label>
              <input
                id="auth-name"
                className="auth-modal__input"
                type="text"
                placeholder="Jane Smith"
                value={name}
                onChange={e => setName(e.target.value)}
                autoComplete="name"
                tabIndex={isSignUp ? 0 : -1}
              />
            </div>
          </div>

          <div className="auth-modal__field">
            <label className="auth-modal__label" htmlFor="auth-email">Email</label>
            <input
              id="auth-email"
              className="auth-modal__input"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoComplete="email"
            />
          </div>

          <div className="auth-modal__field">
            <label className="auth-modal__label" htmlFor="auth-password">Password</label>
            <div className="auth-modal__password-wrap">
              <input
                id="auth-password"
                className="auth-modal__input"
                type={showPassword ? 'text' : 'password'}
                placeholder={isSignUp ? 'Min. 8 characters' : '••••••••'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
              />
              <button
                type="button"
                className="auth-modal__eye"
                onClick={() => setShowPassword(v => !v)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOffIcon /> : <EyeIcon />}
              </button>
            </div>
          </div>

          {error && <p className="auth-modal__error" role="alert">{error}</p>}

          <button
            type="submit"
            className="btn btn-primary auth-modal__submit"
            disabled={isSubmitting}
          >
            {isSubmitting
              ? <span className="auth-modal__spinner" />
              : isSignUp ? 'Create Account' : 'Sign In'}
          </button>
        </form>

        {/* Divider */}
        <div className="auth-modal__divider">
          <span className="auth-modal__divider-line" />
          <span className="auth-modal__divider-text">or</span>
          <span className="auth-modal__divider-line" />
        </div>

        {/* Google */}
        <button
          type="button"
          className="btn btn-google auth-modal__google"
          onClick={loginWithGoogle}
        >
          <GoogleIcon />
          Continue with Google
        </button>

        {/* Switch mode */}
        <p className="auth-modal__switch">
          {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
          <button
            type="button"
            className="auth-modal__switch-btn"
            onClick={() => switchMode(isSignUp ? 'signin' : 'signup')}
          >
            {isSignUp ? 'Sign in' : 'Sign up'}
          </button>
        </p>

      </div>
    </div>
  );
};

const GoogleIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
    <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4" />
    <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853" />
    <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05" />
    <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335" />
  </svg>
);

const CloseIcon: React.FC = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <line x1="18" y1="6" x2="6" y2="18" />
    <line x1="6" y1="6" x2="18" y2="18" />
  </svg>
);

const EyeIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EyeOffIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
    <line x1="1" y1="1" x2="23" y2="23" />
  </svg>
);

export default AuthModal;
