import { useState, useEffect, useRef } from 'react';
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
}) {
  const [openMenuId, setOpenMenuId] = useState(null);
  const menuRef = useRef(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenMenuId(null);
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

  const renderConversation = (conv) => (
    <div
      key={conv.id}
      className={`conversation-item ${
        conv.id === currentConversationId ? 'active' : ''
      }`}
      onClick={() => onSelectConversation(conv.id)}
    >
      <div className="conversation-content">
        <div className="conversation-title">
          {conv.title || 'New Conversation'}
        </div>
        <div className="conversation-meta">
          {conv.message_count} messages
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
    </div>
  )
}
