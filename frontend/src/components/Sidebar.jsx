/**
 * Sidebar component with Supabase authentication
 */
import { useState, useEffect, useRef } from 'react';
import { supabase } from '../supabaseClient';
import { useNavigate } from 'react-router-dom';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  onStarConversation,
  onRenameConversation,
  onDeleteConversation,
  isOpen = true,
  onToggleSidebar,
  subscription, // Feature 4: Subscription data
  user, // Supabase user object (passed from App.jsx)
}) {
  const navigate = useNavigate();

  // Sign out handler using Supabase
  const handleSignOut = async () => {
    try {
      await supabase.auth.signOut();
      navigate('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };
  const [openMenuId, setOpenMenuId] = useState(null);
  const [settingsMenuOpen, setSettingsMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const settingsMenuRef = useRef(null);

  // Feature 5: Calculate days remaining until expiration
  const getDaysRemaining = (expiresAt) => {
    if (!expiresAt) return null;
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diffTime = expiry - now;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  };

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenMenuId(null);
      }
      if (settingsMenuRef.current && !settingsMenuRef.current.contains(event.target)) {
        setSettingsMenuOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Separate conversations into starred and recents
  const starredConversations = conversations.filter(conv => conv.starred);
  const recentConversations = conversations.filter(conv => !conv.starred);

  const handleMenuClick = (e, convId) => {
    e.stopPropagation();
    setOpenMenuId(openMenuId === convId ? null : convId);
  };

  const handleStar = (e, conv) => {
    e.stopPropagation();
    onStarConversation(conv.id);
    setOpenMenuId(null);
  };

  const handleRename = (e, conv) => {
    e.stopPropagation();
    const newTitle = prompt('Enter new title:', conv.title);
    if (newTitle && newTitle.trim()) {
      onRenameConversation(conv.id, newTitle.trim());
    }
    setOpenMenuId(null);
  };

  const handleDelete = (e, conv) => {
    e.stopPropagation();
    if (confirm(`Delete "${conv.title}"?`)) {
      onDeleteConversation(conv.id);
    }
    setOpenMenuId(null);
  };

  const renderConversation = (conv) => {
    // Feature 5: Check expiration status
    const daysRemaining = getDaysRemaining(conv.expires_at);
    const isExpiring = daysRemaining !== null && daysRemaining <= 7;
    const isExpired = daysRemaining !== null && daysRemaining <= 0;

    return (
      <div
        key={conv.id}
        className={`conversation-item ${
          conv.id === currentConversationId ? 'active' : ''
        } ${isExpired ? 'expired' : isExpiring ? 'expiring' : ''}`}
        onClick={() => onSelectConversation(conv.id)}
      >
        <div className="conversation-content">
          <div className="conversation-title">
            {conv.title || 'New Conversation'}
          </div>
          <div className="conversation-meta">
            {conv.message_count} messages
            {/* Feature 5: Show expiration warning */}
            {isExpired && (
              <span className="expiration-badge expired">Expired</span>
            )}
            {isExpiring && !isExpired && (
              <span className="expiration-badge expiring">
                {daysRemaining} {daysRemaining === 1 ? 'day' : 'days'} left
              </span>
            )}
          </div>
        </div>
        <div className="conversation-actions">
          <button
            className="menu-button"
            onClick={(e) => handleMenuClick(e, conv.id)}
            aria-label="More actions"
          >
            ⋯
          </button>
          {openMenuId === conv.id && (
            <div className="dropdown-menu" ref={menuRef}>
              <button
                className="dropdown-item"
                onClick={(e) => handleStar(e, conv)}
              >
                <span className="dropdown-icon">⭐</span>
                {conv.starred ? 'Unstar' : 'Star'}
              </button>
              <button
                className="dropdown-item"
                onClick={(e) => handleRename(e, conv)}
              >
                <span className="dropdown-icon">✏️</span>
                Rename
              </button>
              <button
                className="dropdown-item delete"
                onClick={(e) => handleDelete(e, conv)}
              >
                <span className="dropdown-icon">🗑️</span>
                Delete
              </button>
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className={`sidebar ${!isOpen ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-header-top">
          <button
            className="sidebar-toggle"
            onClick={onToggleSidebar}
            aria-label="Toggle sidebar"
            title="Close sidebar"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
              <path d="M1 3h14v1H1V3zm0 4h14v1H1V7zm0 4h14v1H1v-1z"/>
            </svg>
          </button>
          <h1>Wellness Partners</h1>
        </div>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Session
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No sessions yet</div>
        ) : (
          <>
            {starredConversations.length > 0 && (
              <div className="conversation-section">
                <div className="section-header">Starred</div>
                {starredConversations.map(renderConversation)}
              </div>
            )}

            {recentConversations.length > 0 && (
              <div className="conversation-section">
                <div className="section-header">Recents</div>
                {recentConversations.map(renderConversation)}
              </div>
            )}
          </>
        )}
      </div>

      <div className="sidebar-footer">
        {/* Feature 4: Display subscription status */}
        {subscription && (
          <div className="subscription-status">
            <div className="subscription-tier">
              {subscription.tier === 'free' && '🆓 Free Tier'}
              {subscription.tier === 'single_report' && '📄 Single Report'}
              {subscription.tier === 'monthly' && '⭐ Monthly Plan'}
              {subscription.tier === 'yearly' && '🌟 Yearly Plan'}
            </div>
            {subscription.tier === 'free' && (
              <div className="subscription-info">
                {conversations.length}/2 conversations used
              </div>
            )}
          </div>
        )}

        {/* Settings menu */}
        <div className="settings-container">
          <button
            className="settings-button"
            onClick={() => setSettingsMenuOpen(!settingsMenuOpen)}
            aria-label="Settings"
          >
            <span className="settings-icon">⚙️</span>
            Settings
          </button>

          {settingsMenuOpen && (
            <div className="settings-dropdown" ref={settingsMenuRef}>
              {/* Email display */}
              <div className="settings-email">
                {user?.email}
              </div>

              <div className="settings-divider"></div>

              {/* Settings link */}
              <button
                className="settings-item"
                onClick={() => {
                  navigate('/settings');
                  setSettingsMenuOpen(false);
                }}
              >
                <span className="item-icon">⚙️</span>
                Manage Subscription
              </button>

              {/* Language (placeholder - not implemented) */}
              <button className="settings-item" disabled>
                <span className="item-icon">🌐</span>
                Language
              </button>

              {/* Help */}
              <button
                className="settings-item"
                onClick={() => {
                  window.open('https://your-help-url.com', '_blank');
                  setSettingsMenuOpen(false);
                }}
              >
                <span className="item-icon">❓</span>
                Get Help
              </button>

              {/* Learn More */}
              <button
                className="settings-item"
                onClick={() => {
                  window.open('https://your-learn-more-url.com', '_blank');
                  setSettingsMenuOpen(false);
                }}
              >
                <span className="item-icon">📚</span>
                Learn More
              </button>

              <div className="settings-divider"></div>

              {/* Logout - moved from standalone button */}
              <button
                className="settings-item logout"
                onClick={handleSignOut}
              >
                <span className="item-icon">🚪</span>
                Log Out
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
