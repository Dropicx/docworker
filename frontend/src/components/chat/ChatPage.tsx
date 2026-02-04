/**
 * Main chat page component for GuidelineChat.
 *
 * Composes ChatSidebar, ChatMessageList, and ChatInput.
 * Handles SSE streaming and localStorage persistence.
 * Supports multiple Dify apps via app selector.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { BookOpen, FileText, ChevronDown, AlertTriangle, Clock } from 'lucide-react';
import { Header } from '../Header';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessageList } from './ChatMessageList';
import { ChatInput } from './ChatInput';
import { ConfirmModal } from '../common/ConfirmModal';
import { useChatHistory } from '../../hooks/useChatHistory';
import {
  streamChatMessage,
  getChatApps,
  ChatRateLimitError,
  formatRetryTime,
} from '../../services/chatApi';
import { ChatApp } from '../../types/chat';

// Icon mapping for apps
const APP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  'book-open': BookOpen,
  'file-text': FileText,
};

export const ChatPage: React.FC = () => {
  const {
    conversations,
    activeConversationId,
    activeConversation,
    createConversation,
    addMessage,
    updateMessage,
    setDifyConversationId,
    deleteConversation,
    setActiveConversation,
    updateTitle,
    clearAll,
  } = useChatHistory();

  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [apps, setApps] = useState<ChatApp[]>([]);
  const [selectedAppId, setSelectedAppId] = useState('guidelines');
  const [appSelectorOpen, setAppSelectorOpen] = useState(false);

  // Modal state for confirmations
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [clearAllModalOpen, setClearAllModalOpen] = useState(false);

  // Rate limit error state
  const [rateLimitError, setRateLimitError] = useState<{
    message: string;
    retryAfter: number | null;
    limitType: string | null;
  } | null>(null);
  const [retryCountdown, setRetryCountdown] = useState<number | null>(null);

  // AbortController for stopping stream
  const abortControllerRef = useRef<AbortController | null>(null);
  const countdownIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Fetch available apps on mount
  useEffect(() => {
    getChatApps().then(setApps);
  }, []);

  // Start fresh on page visit - no active conversation
  useEffect(() => {
    setActiveConversation(null);
  }, [setActiveConversation]);

  // Update selected app when conversation changes
  useEffect(() => {
    if (activeConversation?.appId) {
      setSelectedAppId(activeConversation.appId);
    }
  }, [activeConversation]);

  // Handle rate limit countdown
  useEffect(() => {
    if (retryCountdown !== null && retryCountdown > 0) {
      countdownIntervalRef.current = setInterval(() => {
        setRetryCountdown(prev => {
          if (prev === null || prev <= 1) {
            // Clear the error when countdown reaches 0
            setRateLimitError(null);
            return null;
          }
          return prev - 1;
        });
      }, 1000);

      return () => {
        if (countdownIntervalRef.current) {
          clearInterval(countdownIntervalRef.current);
        }
      };
    }
  }, [retryCountdown]);

  // Cleanup countdown on unmount
  useEffect(() => {
    return () => {
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, []);

  const selectedApp = apps.find(a => a.id === selectedAppId) || apps[0];

  /**
   * Handle sending a message.
   */
  const handleSend = useCallback(
    async (content: string) => {
      // Get or create conversation with current app
      let convId = activeConversationId;
      let appId = selectedAppId;

      if (!convId) {
        const newConv = createConversation(selectedAppId);
        convId = newConv.id;
        appId = newConv.appId;
      } else {
        // Use the conversation's app, not the selector
        const currentConv = conversations.find(c => c.id === convId);
        appId = currentConv?.appId || selectedAppId;
      }

      // Add user message
      addMessage({ role: 'user', content }, convId);

      // Create placeholder for assistant message
      const assistantMessage = addMessage(
        { role: 'assistant', content: '', isStreaming: true },
        convId
      );

      setIsStreaming(true);

      // Create new AbortController for this request
      abortControllerRef.current = new AbortController();

      // Track content for abort handling
      let fullContent = '';

      try {
        // Get current Dify conversation ID for context
        const currentConv = conversations.find(c => c.id === convId);
        const difyConvId = currentConv?.difyConversationId;

        let newDifyConvId: string | undefined;

        // Stream the response with the correct app
        for await (const event of streamChatMessage(
          content,
          difyConvId,
          appId,
          abortControllerRef.current.signal
        )) {
          if (event.event === 'message' || event.event === 'agent_message') {
            // Append streamed content
            if (event.answer) {
              fullContent += event.answer;
              updateMessage(assistantMessage.id, {
                content: fullContent,
                isStreaming: true,
              });
            }

            // Capture conversation ID from first response
            if (event.conversation_id && !newDifyConvId) {
              newDifyConvId = event.conversation_id;
            }
          } else if (event.event === 'message_end') {
            // Message complete
            if (event.conversation_id) {
              newDifyConvId = event.conversation_id;
            }
          } else if (event.event === 'error') {
            // Handle error
            fullContent = `Fehler: ${event.message || 'Unbekannter Fehler'}`;
            updateMessage(assistantMessage.id, {
              content: fullContent,
              isStreaming: false,
            });
            break;
          }
        }

        // Finalize message
        updateMessage(assistantMessage.id, {
          content: fullContent || 'Keine Antwort erhalten.',
          isStreaming: false,
        });

        // Store Dify conversation ID for context continuity
        if (newDifyConvId && convId) {
          setDifyConversationId(newDifyConvId, convId);
        }
      } catch (error) {
        // Handle abort gracefully - don't show error, just finalize partial content
        if (error instanceof Error && error.name === 'AbortError') {
          updateMessage(assistantMessage.id, {
            content: fullContent || 'Generierung abgebrochen.',
            isStreaming: false,
          });
        } else if (error instanceof ChatRateLimitError) {
          // Handle rate limit error
          console.warn('Rate limit exceeded:', error.message);
          setRateLimitError({
            message: error.message,
            retryAfter: error.retryAfter,
            limitType: error.limitType,
          });
          if (error.retryAfter) {
            setRetryCountdown(error.retryAfter);
          }
          updateMessage(assistantMessage.id, {
            content: `Limit erreicht: ${error.message}`,
            isStreaming: false,
          });
        } else {
          console.error('Chat error:', error);
          updateMessage(assistantMessage.id, {
            content: `Fehler: ${error instanceof Error ? error.message : 'Verbindungsfehler'}`,
            isStreaming: false,
          });
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
      }
    },
    [
      activeConversationId,
      selectedAppId,
      conversations,
      createConversation,
      addMessage,
      updateMessage,
      setDifyConversationId,
    ]
  );

  /**
   * Handle creating a new conversation with selected app.
   */
  const handleNewConversation = useCallback(() => {
    createConversation(selectedAppId);
    setSidebarOpen(false);
  }, [createConversation, selectedAppId]);

  /**
   * Handle selecting a conversation.
   */
  const handleSelectConversation = useCallback(
    (id: string) => {
      setActiveConversation(id);
    },
    [setActiveConversation]
  );

  /**
   * Handle deleting a conversation - opens confirmation modal.
   */
  const handleDeleteConversation = useCallback((id: string) => {
    setDeleteTargetId(id);
    setDeleteModalOpen(true);
  }, []);

  /**
   * Confirm deletion of conversation.
   */
  const confirmDeleteConversation = useCallback(() => {
    if (deleteTargetId) {
      deleteConversation(deleteTargetId);
    }
    setDeleteModalOpen(false);
    setDeleteTargetId(null);
  }, [deleteTargetId, deleteConversation]);

  /**
   * Handle clearing all conversations - opens confirmation modal.
   */
  const handleClearAll = useCallback(() => {
    setClearAllModalOpen(true);
  }, []);

  /**
   * Confirm clearing all conversations.
   */
  const confirmClearAll = useCallback(() => {
    clearAll();
    setClearAllModalOpen(false);
  }, [clearAll]);

  /**
   * Handle renaming a conversation.
   */
  const handleRename = useCallback(
    (id: string, newTitle: string) => {
      updateTitle(id, newTitle);
    },
    [updateTitle]
  );

  /**
   * Handle stopping the current stream.
   */
  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  /**
   * Handle app selection - switches app and deselects current conversation.
   */
  const handleAppSelect = useCallback(
    (appId: string) => {
      setSelectedAppId(appId);
      setAppSelectorOpen(false);
      // Deselect current conversation so user starts fresh with new app
      setActiveConversation(null);
    },
    [setActiveConversation]
  );

  // Get messages for active conversation
  const messages = activeConversation?.messages || [];

  // Get placeholder text based on selected app
  const getPlaceholder = () => {
    if (selectedAppId === 'befund') {
      return 'Befund eingeben (z.B. "HbA1c 8,2%, Diabetes Typ 2, BMI 31")...';
    }
    return 'Frage zu medizinischen Leitlinien stellen...';
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gradient-to-br from-neutral-50 via-white to-accent-50/30">
      {/* Fixed Header */}
      <Header />

      {/* Main Content - fills remaining height */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - independently scrollable */}
        <ChatSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewConversation}
          onDelete={handleDeleteConversation}
          onClearAll={handleClearAll}
          onRename={handleRename}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* Main chat area - flex column with fixed input */}
        <main className="flex-1 flex flex-col min-w-0 min-h-0 bg-white overflow-hidden">
          {/* App Selector Bar - fixed at top */}
          {apps.length > 1 && (
            <div className="flex-shrink-0 border-b border-neutral-200 bg-white pl-14 md:pl-4 pr-4 py-2 z-10">
              <div className="relative inline-block">
                <button
                  onClick={() => setAppSelectorOpen(!appSelectorOpen)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg bg-neutral-50 hover:bg-neutral-100 border border-neutral-200 transition-colors"
                  title="App wechseln"
                >
                  {selectedApp && (
                    <>
                      {(() => {
                        const IconComponent = APP_ICONS[selectedApp.icon] || BookOpen;
                        return <IconComponent className="w-4 h-4 text-brand-600" />;
                      })()}
                      <span className="text-sm font-medium text-neutral-700">
                        {selectedApp.name}
                      </span>
                      <ChevronDown
                        className={`w-4 h-4 text-neutral-400 transition-transform ${appSelectorOpen ? 'rotate-180' : ''}`}
                      />
                    </>
                  )}
                </button>

                {/* App Dropdown */}
                {appSelectorOpen && (
                  <div className="absolute left-0 top-full mt-1 w-72 bg-white rounded-lg shadow-lg border border-neutral-200 z-50 overflow-hidden">
                    <div className="px-3 py-2 bg-neutral-50 border-b border-neutral-200">
                      <span className="text-xs font-medium text-neutral-500">Assistent wahlen</span>
                    </div>
                    {apps.map(app => {
                      const IconComponent = APP_ICONS[app.icon] || BookOpen;
                      const isSelected = app.id === selectedAppId && !activeConversation;
                      const isCurrentConv = activeConversation?.appId === app.id;
                      return (
                        <button
                          key={app.id}
                          onClick={() => app.available && handleAppSelect(app.id)}
                          disabled={!app.available}
                          className={`w-full flex items-start gap-3 px-4 py-3 transition-colors ${
                            !app.available
                              ? 'opacity-50 cursor-not-allowed bg-neutral-50'
                              : isSelected || isCurrentConv
                                ? 'bg-brand-50 hover:bg-brand-100'
                                : 'hover:bg-neutral-50'
                          }`}
                        >
                          <IconComponent
                            className={`w-5 h-5 mt-0.5 ${isSelected || isCurrentConv ? 'text-brand-600' : 'text-neutral-500'}`}
                          />
                          <div className="flex-1 text-left">
                            <div
                              className={`text-sm font-medium ${isSelected || isCurrentConv ? 'text-brand-700' : 'text-neutral-700'}`}
                            >
                              {app.name}
                            </div>
                            <div className="text-xs text-neutral-500">{app.description}</div>
                          </div>
                          {isCurrentConv && (
                            <span className="text-xs text-brand-600 bg-brand-100 px-2 py-0.5 rounded-full">
                              Aktiv
                            </span>
                          )}
                          {!app.available && (
                            <span className="text-xs text-neutral-400 bg-neutral-200 px-2 py-0.5 rounded-full">
                              Nicht konfiguriert
                            </span>
                          )}
                        </button>
                      );
                    })}
                    {activeConversation && (
                      <div className="px-3 py-2 bg-neutral-50 border-t border-neutral-200">
                        <span className="text-xs text-neutral-400">
                          Wechsel startet neue Unterhaltung
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Rate Limit Error Banner */}
          {rateLimitError && (
            <div className="flex-shrink-0 bg-amber-50 border-b border-amber-200 px-4 py-3">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-800">
                    {rateLimitError.limitType === 'permanent_ban'
                      ? 'Zugang gesperrt'
                      : rateLimitError.limitType === 'temp_ban'
                        ? 'Temporar gesperrt'
                        : 'Limit erreicht'}
                  </p>
                  <p className="text-sm text-amber-700">{rateLimitError.message}</p>
                </div>
                {retryCountdown !== null && retryCountdown > 0 && (
                  <div className="flex items-center gap-2 bg-amber-100 px-3 py-1.5 rounded-lg">
                    <Clock className="w-4 h-4 text-amber-600" />
                    <span className="text-sm font-medium text-amber-800">
                      {formatRetryTime(retryCountdown)}
                    </span>
                  </div>
                )}
                <button
                  onClick={() => {
                    setRateLimitError(null);
                    setRetryCountdown(null);
                  }}
                  className="text-amber-600 hover:text-amber-800 text-sm font-medium"
                >
                  Schliessen
                </button>
              </div>
            </div>
          )}

          {/* Message List - scrollable area */}
          <ChatMessageList messages={messages} isStreaming={isStreaming} />

          {/* Input - fixed at bottom */}
          <ChatInput
            onSend={handleSend}
            onStop={handleStop}
            disabled={isStreaming}
            placeholder={getPlaceholder()}
          />
        </main>
      </div>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Unterhaltung loschen"
        message="Diese Unterhaltung wird unwiderruflich geloscht. Mochten Sie fortfahren?"
        confirmText="Loschen"
        cancelText="Abbrechen"
        variant="danger"
        onConfirm={confirmDeleteConversation}
        onCancel={() => {
          setDeleteModalOpen(false);
          setDeleteTargetId(null);
        }}
      />

      {/* Clear All Confirmation Modal */}
      <ConfirmModal
        isOpen={clearAllModalOpen}
        title="Alle Unterhaltungen loschen"
        message={`Alle ${conversations.length} Unterhaltungen werden unwiderruflich geloscht. Mochten Sie fortfahren?`}
        confirmText="Alle loschen"
        cancelText="Abbrechen"
        variant="danger"
        onConfirm={confirmClearAll}
        onCancel={() => setClearAllModalOpen(false)}
      />
    </div>
  );
};

export default ChatPage;
