import React from 'react';
import { useNavigate } from 'react-router-dom';

interface TopNavProps {
  onToggleSidebar?: () => void;
}

/**
 * TopNav — Clean mobile header bar:
 * - On mobile (<= 768px): shows hamburger button to open sidebar navigation drawer and ECO-SHIELD brand logo
 * - On desktop (> 768px): hidden so desktop layout is clean and uncluttered
 */
export default function TopNav({ onToggleSidebar }: TopNavProps) {
  const navigate = useNavigate();

  return (
    <header className="mobile-topbar">
      <div className="mobile-topbar-left">
        {/* Mobile menu toggle */}
        <button
          type="button"
          className="mobile-menu-btn"
          onClick={onToggleSidebar}
          aria-label="Open navigation menu"
          title="Open menu"
        >
          <span className="three-lines-icon" aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
        </button>

        {/* Mobile brand logo */}
        <div className="mobile-topbar-brand" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <img
            src="/logo.png"
            alt="ECO-SHIELD"
            className="mobile-topbar-logo"
          />
        </div>
      </div>
    </header>
  );
}
