import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

const Navbar: React.FC = () => {
  const { user, isAuthenticated, openAuthModal, logout } = useAuth();
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
              <div className="navbar__auth-buttons">
                <button onClick={() => openAuthModal('signin')} className="btn btn-secondary navbar__signin">
                  Sign in
                </button>
                <button onClick={() => openAuthModal('signup')} className="btn btn-primary navbar__signin">
                  Sign up
                </button>
              </div>
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


export default Navbar;
