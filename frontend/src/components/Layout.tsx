import React from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import './Layout.css';

const Layout: React.FC = () => {
  return (
    <div className="layout">
      <Navbar />
      <main className="layout__main">
        <Outlet />
      </main>
      <footer className="layout__footer">
        <div className="container">
          <p>
            © {new Date().getFullYear()} TermsScope Analytics — AI-powered legal document analysis.
          </p>
          <p className="layout__footer-disclaimer">
            This tool provides informational analysis only, not legal advice.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
