import React, { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './AuthCallbackPage.css';

const AuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setToken } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      setToken(token);
      // Short delay so user sees the success state
      setTimeout(() => navigate('/', { replace: true }), 1000);
    } else {
      // No token — redirect home
      navigate('/', { replace: true });
    }
  }, [searchParams, setToken, navigate]);

  return (
    <div className="auth-callback">
      <div className="auth-callback__content animate-fade-in">
        <div className="auth-callback__icon">✓</div>
        <h2>Signed in successfully!</h2>
        <p>Redirecting you back...</p>
      </div>
    </div>
  );
};

export default AuthCallbackPage;
