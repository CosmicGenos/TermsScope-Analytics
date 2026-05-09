import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const Navbar: React.FC = () => {
  const { user, isAuthenticated, login, logout } = useAuth();
  const location = useLocation();
  const [showSignOutModal, setShowSignOutModal] = useState(false);

  const handleSignOut = () => {
    logout();
    setShowSignOutModal(false);
  };

  return (
    <>
      <nav className="navbar">
        <div className="container navbar__inner">
          <Link to="/" className="navbar__brand">
            <img src="/Termscope_icon.png" alt="TermsScope" className="navbar__logo-img" />
            <span className="navbar__name">
              Terms<span className="navbar__name-accent">Scope</span>
            </span>
          </Link>

          <div className="navbar__links">
            <Link
              to="/"
              className={`navbar__link ${location.pathname === '/' ? 'navbar__link--active' : ''}`}
            >
              Analyze
            </Link>
            {isAuthenticated && (
              <Link
                to="/history"
                className={`navbar__link ${location.pathname === '/history' ? 'navbar__link--active' : ''}`}
              >
                History
              </Link>
            )}
          </div>

          <div className="navbar__auth">
            {isAuthenticated && user ? (
              <div className="navbar__user">
                {user.avatar_url && (
                  <img src={user.avatar_url} alt={user.name} className="navbar__avatar" />
                )}
                <span className="navbar__user-name">{user.name}</span>
                <button
                  onClick={() => setShowSignOutModal(true)}
                  className="btn btn-ghost navbar__logout"
                >
                  Sign out
                </button>
              </div>
            ) : (
              <button onClick={login} className="btn btn-google">
                <GoogleIcon />
                Sign in
              </button>
            )}
          </div>
        </div>
      </nav>

      {showSignOutModal && (
        <div
          className="signout-overlay"
          onClick={() => setShowSignOutModal(false)}
        >
          <div className="signout-modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="signout-modal__title">Sign out?</h3>
            <p className="signout-modal__desc">
              You'll need to sign back in to view your analysis history.
            </p>
            <div className="signout-modal__actions">
              <button
                className="btn btn-secondary"
                onClick={() => setShowSignOutModal(false)}
              >
                Cancel
              </button>
              <button className="btn btn-danger" onClick={handleSignOut}>
                Sign out
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

const GoogleIcon: React.FC = () => (
  <svg width="16" height="16" viewBox="0 0 18 18" fill="none" aria-hidden="true">
    <path
      d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z"
      fill="#4285F4"
    />
    <path
      d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z"
      fill="#34A853"
    />
    <path
      d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z"
      fill="#FBBC05"
    />
    <path
      d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z"
      fill="#EA4335"
    />
  </svg>
);

export default Navbar;
