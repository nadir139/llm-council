import { useState, useEffect } from 'react';
import { useUser, useAuth } from '@clerk/clerk-react';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import OnboardingPage from './components/OnboardingPage';
import OnboardingQuestions from './components/OnboardingQuestions';
import AccountCreation from './components/AccountCreation';
import { api } from './api';
import './App.css';

function App() {
  const { isSignedIn, user, isLoaded } = useUser();
  const { getToken } = useAuth();

  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // Feature 3: Follow-up form loading state
  const [isFollowUpLoading, setIsFollowUpLoading] = useState(false);

  // Onboarding state
  const [currentView, setCurrentView] = useState('landing'); // 'landing', 'questions', 'signup', 'signin', 'chat'
  const [userProfile, setUserProfile] = useState(null);
  const [hasBackendProfile, setHasBackendProfile] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(true);

  // Check for existing profile from backend when user is signed in
  useEffect(() => {
    async function checkProfile() {
      if (!isLoaded) {
        return;
      }

      if (!isSignedIn) {
        // User is not signed in, show landing page
        setCurrentView('landing');
        setCheckingProfile(false);
        return;
      }

      try {
        // User is signed in, check if they have a backend profile
        const profile = await api.getProfile(getToken);
        if (profile) {
          // Profile exists in backend
          setHasBackendProfile(true);
          setUserProfile(profile.profile);
          setCurrentView('chat');
        } else {
          // No profile in backend, check localStorage
          const savedProfile = localStorage.getItem('userProfile');
          if (savedProfile) {
            // Has temp profile from questions, need to save to backend
            const tempProfile = JSON.parse(savedProfile);
            setUserProfile(tempProfile);

            // Try to save to backend
            try {
              await api.createProfile(tempProfile, getToken);
              setHasBackendProfile(true);
              localStorage.removeItem('userProfile'); // Clear temp storage
              setCurrentView('chat');
            } catch (error) {
              console.error('Failed to save profile to backend:', error);
              // Stay on current view
            }
          } else {
            // No profile anywhere, send to questions
            setCurrentView('questions');
          }
        }
      } catch (error) {
        // Silently handle errors during authentication flow
        // User will be redirected to landing page
        setCurrentView('landing');
      } finally {
        setCheckingProfile(false);
      }
    }

    checkProfile();
  }, [isLoaded, isSignedIn, getToken]);

  // Load conversations when user is authenticated and in chat view
  useEffect(() => {
    // Only load conversations if user is fully authenticated and in chat view
    // This ensures the token is ready before attempting to fetch conversations
    if (isLoaded && isSignedIn && currentView === 'chat') {
      // Small delay to ensure Clerk's getToken() is ready
      const timer = setTimeout(() => {
        loadConversations();
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [isLoaded, isSignedIn, currentView]);

  // Load conversation details when selected
  useEffect(() => {
    if (currentConversationId) {
      loadConversation(currentConversationId);
    }
  }, [currentConversationId]);

  const loadConversations = async () => {
    try {
      const convs = await api.listConversations(getToken);
      setConversations(convs);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  const loadConversation = async (id) => {
    try {
      const conv = await api.getConversation(id, getToken);
      setCurrentConversation(conv);
    } catch (error) {
      console.error('Failed to load conversation:', error);
    }
  };

  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation(getToken);
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      console.error('Failed to create conversation:', error);
    }
  };

  const handleSelectConversation = (id) => {
    setCurrentConversationId(id);
  };

  const handleStarConversation = async (id) => {
    try {
      await api.toggleStarConversation(id, getToken);
      await loadConversations();
    } catch (error) {
      console.error('Failed to toggle star:', error);
    }
  };

  const handleRenameConversation = async (id, newTitle) => {
    try {
      await api.updateConversationTitle(id, newTitle, getToken);
      await loadConversations();
    } catch (error) {
      console.error('Failed to rename conversation:', error);
    }
  };

  const handleDeleteConversation = async (id) => {
    try {
      await api.deleteConversation(id, getToken);
      // If we deleted the current conversation, clear it
      if (id === currentConversationId) {
        setCurrentConversationId(null);
        setCurrentConversation(null);
      }
      await loadConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
    }
  };

  // Feature 3: Handle follow-up form submission
  const handleSubmitFollowUp = async (followUpAnswers) => {
    if (!currentConversationId) return;

    setIsFollowUpLoading(true);
    try {
      // Call the follow-up API endpoint
      const response = await api.submitFollowUp(
        currentConversationId,
        followUpAnswers,
        getToken
      );

      // Add the second report as a new assistant message
      const secondReport = {
        role: 'assistant',
        stage1: response.stage1,
        stage2: [], // Stage 2 hidden from users
        stage3: response.stage3,
        metadata: response.metadata,
      };

      // Update conversation with the new report
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, secondReport],
        report_cycle: response.report_cycle,
        has_follow_up: true,
        follow_up_answers: followUpAnswers,
      }));

      // Reload conversations list to update sidebar
      loadConversations();
    } catch (error) {
      console.error('Failed to submit follow-up:', error);
      alert('Failed to generate second report. Please try again.');
    } finally {
      setIsFollowUpLoading(false);
    }
  };

  const handleSendMessage = async (content) => {
    if (!currentConversationId) return;

    setIsLoading(true);
    try {
      // Optimistically add user message to UI
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

      // Create a partial assistant message that will be updated progressively
      const assistantMessage = {
        role: 'assistant',
        stage1: null,
        stage2: null,
        stage3: null,
        metadata: null,
        loading: {
          stage1: false,
          stage2: false,
          stage3: false,
        },
      };

      // Add the partial assistant message
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

      // Send message with streaming
      await api.sendMessageStream(currentConversationId, content, (eventType, event) => {
        switch (eventType) {
          case 'stage1_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage1 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage1_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage1 = event.data;
              lastMsg.loading.stage1 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage2_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage2 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage2_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage2 = event.data;
              lastMsg.metadata = event.metadata;
              lastMsg.loading.stage2 = false;
              return { ...prev, messages };
            });
            break;

          case 'stage3_start':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.loading.stage3 = true;
              return { ...prev, messages };
            });
            break;

          case 'stage3_complete':
            setCurrentConversation((prev) => {
              const messages = [...prev.messages];
              const lastMsg = messages[messages.length - 1];
              lastMsg.stage3 = event.data;
              lastMsg.loading.stage3 = false;
              return { ...prev, messages };
            });
            break;

          case 'title_complete':
            // Reload conversations to get updated title
            loadConversations();
            break;

          case 'complete':
            // Stream complete, reload conversations list
            loadConversations();
            // Feature 3: Update report_cycle if provided
            if (event.report_cycle !== undefined) {
              setCurrentConversation((prev) => ({
                ...prev,
                report_cycle: event.report_cycle,
              }));
            }
            setIsLoading(false);
            break;

          case 'error':
            console.error('Stream error:', event.message);
            setIsLoading(false);
            break;

          default:
            console.log('Unknown event type:', eventType);
        }
      }, getToken);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Remove optimistic messages on error
      setCurrentConversation((prev) => ({
        ...prev,
        messages: prev.messages.slice(0, -2),
      }));
      setIsLoading(false);
    }
  };

  // Handle authentication state changes
  useEffect(() => {
    if (isLoaded && isSignedIn && userProfile && currentView !== 'chat') {
      // User is signed in and has profile, go to chat
      // loadConversations will be triggered by the dedicated effect when currentView changes
      setCurrentView('chat');
    }
  }, [isSignedIn, isLoaded, userProfile]);

  // Handle onboarding flow
  const handleStartOnboarding = () => {
    setCurrentView('questions');
  };

  const handleProfileComplete = (profile) => {
    // Save profile to localStorage for now (will move to backend later)
    setUserProfile(profile);
    localStorage.setItem('userProfile', JSON.stringify(profile));

    // Show sign up page
    setCurrentView('signup');
  };

  const handleSignIn = () => {
    setCurrentView('signin');
  };

  const handleSignUp = () => {
    setCurrentView('signup');
  };

  // View routing
  if (!isLoaded || checkingProfile) {
    // Show loading while Clerk initializes or checking profile
    return (
      <div style={{
        minHeight: '100vh',
        backgroundColor: '#791f85',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: '#FFFFFF',
        fontSize: '18px'
      }}>
        Loading...
      </div>
    );
  }

  if (currentView === 'landing') {
    return (
      <OnboardingPage
        logoText="Wellness Partner"
        placeholder="whats on your mind?"
        onSubmit={handleStartOnboarding}
        onSignIn={handleSignIn}
        onSignUp={handleSignUp}
      />
    );
  }

  if (currentView === 'questions') {
    return (
      <OnboardingQuestions onComplete={handleProfileComplete} />
    );
  }

  if (currentView === 'signup') {
    return (
      <AccountCreation mode="signup" />
    );
  }

  if (currentView === 'signin') {
    return (
      <AccountCreation mode="signin" />
    );
  }

  // Main chat view
  return (
    <div className="app">
      {!sidebarOpen && (
        <button
          className="sidebar-toggle-floating"
          onClick={() => setSidebarOpen(true)}
          aria-label="Open sidebar"
          title="Open sidebar (Ctrl+.)"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1 3h14v1H1V3zm0 4h14v1H1V7zm0 4h14v1H1v-1z"/>
          </svg>
        </button>
      )}
      <Sidebar
        conversations={conversations}
        currentConversationId={currentConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onStarConversation={handleStarConversation}
        onRenameConversation={handleRenameConversation}
        onDeleteConversation={handleDeleteConversation}
        isOpen={sidebarOpen}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onSubmitFollowUp={handleSubmitFollowUp}
        isFollowUpLoading={isFollowUpLoading}
      />
    </div>
  );
}

export default App;
