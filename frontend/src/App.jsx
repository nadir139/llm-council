/**
 * Main App component for Wellness Partner
 *
 * Uses Supabase for authentication instead of Clerk.
 * Authentication state is managed through Supabase's onAuthStateChange listener.
 */
import { useState, useEffect, useCallback } from 'react';
import { Routes, Route, useNavigate } from 'react-router-dom';
import { supabase } from './supabaseClient';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';
import OnboardingPage from './components/OnboardingPage';
import OnboardingQuestions from './components/OnboardingQuestions';
import AccountCreation from './components/AccountCreation';
import Paywall from './components/Paywall';
import PaymentSuccess from './components/PaymentSuccess';
import Settings from './components/Settings';
import { api } from './api';
import './App.css';

function App() {
  // Supabase authentication state
  const [session, setSession] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const navigate = useNavigate();

  // Derived auth state (for compatibility with existing code)
  const isSignedIn = !!session;

  // Helper function to get auth token (replaces Clerk's getToken)
  // Memoized to prevent infinite re-renders in useEffect dependencies
  const getToken = useCallback(async () => {
    if (!session) return null;
    return session.access_token;
  }, [session]);

  const [conversations, setConversations] = useState([]);
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [isFollowUpLoading, setIsFollowUpLoading] = useState(false);

  // Feature 4: Subscription state
  const [subscription, setSubscription] = useState(null);

  // Onboarding state
  const [currentView, setCurrentView] = useState('landing');
  const [userProfile, setUserProfile] = useState(null);
  const [hasBackendProfile, setHasBackendProfile] = useState(false);
  const [checkingProfile, setCheckingProfile] = useState(true);

  // Initialize Supabase auth listener
  // This runs once on mount and sets up the authentication state listener
  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user || null);
      setIsLoaded(true);
    });

    // Listen for auth state changes (sign in, sign out, token refresh)
    const {
      data: { subscription: authSubscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user || null);
      setIsLoaded(true);
    });

    // Cleanup listener on unmount
    return () => authSubscription.unsubscribe();
  }, []);

  // Feature 4: Load subscription when user is authenticated
  useEffect(() => {
    async function loadSubscription() {
      if (isLoaded && isSignedIn) {
        try {
          const sub = await api.getSubscription(getToken);
          setSubscription(sub);
        } catch (error) {
          console.error('Failed to load subscription:', error);
        }
      }
    }

    loadSubscription();
  }, [isLoaded, isSignedIn, getToken]);

  // Check for existing profile from backend when user is signed in
  useEffect(() => {
    async function checkProfile() {
      if (!isLoaded) {
        return;
      }

      if (!isSignedIn) {
        // User is not signed in - only reset to landing if not already on auth pages
        setCurrentView((prev) => {
          // Keep signin/signup views, otherwise go to landing
          if (prev === 'signin' || prev === 'signup' || prev === 'questions') {
            return prev;
          }
          return 'landing';
        });
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
              localStorage.removeItem('userProfile');
              setCurrentView('chat');
            } catch (error) {
              console.error('Failed to save profile to backend:', error);
            }
          } else {
            // No profile anywhere, send to questions
            setCurrentView('questions');
          }
        }
      } catch (error) {
        // Silently handle errors during authentication flow
        setCurrentView('landing');
      } finally {
        setCheckingProfile(false);
      }
    }

    checkProfile();
  }, [isLoaded, isSignedIn, getToken]);

  // Load conversations when user is authenticated and in chat view
  useEffect(() => {
    if (isLoaded && isSignedIn && currentView === 'chat') {
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

  // Feature 4: Handle paywall when creating new conversation
  const handleNewConversation = async () => {
    try {
      const newConv = await api.createConversation(getToken);
      setConversations([
        { id: newConv.id, created_at: newConv.created_at, message_count: 0 },
        ...conversations,
      ]);
      setCurrentConversationId(newConv.id);
    } catch (error) {
      // Feature 4: Check if it's a paywall error (402 Payment Required)
      if (error.message && error.message.includes('402')) {
        // Redirect to paywall
        navigate('/paywall');
      } else {
        console.error('Failed to create conversation:', error);
        alert('Failed to create conversation. Please try again.');
      }
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
      const response = await api.submitFollowUp(
        currentConversationId,
        followUpAnswers,
        getToken
      );

      const secondReport = {
        role: 'assistant',
        stage1: response.stage1,
        stage2: [],
        stage3: response.stage3,
        metadata: response.metadata,
      };

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, secondReport],
        report_cycle: response.report_cycle,
        has_follow_up: true,
        follow_up_answers: followUpAnswers,
      }));

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
      const userMessage = { role: 'user', content };
      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, userMessage],
      }));

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

      setCurrentConversation((prev) => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
      }));

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
            loadConversations();
            break;

          case 'complete':
            loadConversations();
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
      setCurrentView('chat');
    }
  }, [isSignedIn, isLoaded, userProfile]);

  // Handle onboarding flow
  const handleStartOnboarding = () => {
    setCurrentView('questions');
  };

  const handleProfileComplete = (profile) => {
    setUserProfile(profile);
    localStorage.setItem('userProfile', JSON.stringify(profile));
    setCurrentView('signup');
  };

  const handleSignIn = () => {
    setCurrentView('signin');
  };

  const handleSignUp = () => {
    setCurrentView('signup');
  };

  // Main chat component wrapper
  const ChatView = () => (
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
        subscription={subscription}
        user={user}
      />
      <ChatInterface
        conversation={currentConversation}
        onSendMessage={handleSendMessage}
        isLoading={isLoading}
        onSubmitFollowUp={handleSubmitFollowUp}
        isFollowUpLoading={isFollowUpLoading}
        subscription={subscription}
      />
    </div>
  );

  // Loading state
  if (!isLoaded || checkingProfile) {
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

  // Routing for payment flow and onboarding
  return (
    <Routes>
      <Route path="/paywall" element={<Paywall />} />
      <Route path="/payment-success" element={<PaymentSuccess />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/*" element={
        currentView === 'landing' ? (
          <OnboardingPage
            logoText="Wellness Partner"
            placeholder="whats on your mind?"
            onSubmit={handleStartOnboarding}
            onSignIn={handleSignIn}
            onSignUp={handleSignUp}
          />
        ) : currentView === 'questions' ? (
          <OnboardingQuestions onComplete={handleProfileComplete} />
        ) : currentView === 'signup' ? (
          <AccountCreation mode="signup" />
        ) : currentView === 'signin' ? (
          <AccountCreation mode="signin" />
        ) : (
          <ChatView />
        )
      } />
    </Routes>
  );
}

export default App;
