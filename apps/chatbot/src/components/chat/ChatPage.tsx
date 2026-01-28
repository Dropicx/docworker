/**
 * Main chat page component for Frag die Leitlinie.
 *
 * Simplified version for standalone guidelines-only chat.
 * Composes ChatSidebar, ChatMessageList, and ChatInput.
 * Handles SSE streaming and localStorage persistence.
 */

import React, { useState, useCallback, useEffect, useRef } from 'react';
import { AlertTriangle, Clock, Loader2 } from 'lucide-react';
import { Header } from '../Header';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessageList } from './ChatMessageList';
import { ChatInput } from './ChatInput';
import { ConfirmModal } from '../common/ConfirmModal';
import { ConsentModal } from '../common/ConsentModal';
import { useChatHistory } from '../../hooks/useChatHistory';
import { useConsent } from '../../hooks/useConsent';
import { streamChatMessage, ChatRateLimitError, formatRetryTime } from '../../services/chatApi';

// Fixed app ID for this standalone chat
const APP_ID = 'guidelines';

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

  const { hasConsented, acceptConsent, isLoading: consentLoading } = useConsent();

  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
  const countdownIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start fresh on page visit - no active conversation
  useEffect(() => {
    setActiveConversation(null);
  }, [setActiveConversation]);

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

  /**
   * Handle sending a message.
   */
  const handleSend = useCallback(
    async (content: string) => {
      // Get or create conversation
      let convId = activeConversationId;

      if (!convId) {
        const newConv = createConversation(APP_ID);
        convId = newConv.id;
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

        // Stream the response
        for await (const event of streamChatMessage(content, difyConvId, APP_ID, abortControllerRef.current.signal)) {
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
      conversations,
      createConversation,
      addMessage,
      updateMessage,
      setDifyConversationId,
    ]
  );

  /**
   * Handle creating a new conversation.
   */
  const handleNewConversation = useCallback(() => {
    createConversation(APP_ID);
    setSidebarOpen(false);
  }, [createConversation]);

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

  // Get messages for active conversation
  const messages = activeConversation?.messages || [];

  // Loading state while checking consent
  if (consentLoading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 dark:from-neutral-900 dark:via-neutral-900 dark:to-neutral-800">
        <Loader2 className="w-8 h-8 text-brand-600 animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 dark:from-neutral-900 dark:via-neutral-900 dark:to-neutral-800">
      {/* Consent Modal - blocks until accepted */}
      <ConsentModal isOpen={!hasConsented} onAccept={acceptConsent} />

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
        <main className="flex-1 flex flex-col min-w-0 min-h-0 bg-white dark:bg-neutral-900 overflow-hidden">
          {/* Rate Limit Error Banner */}
          {rateLimitError && (
            <div className="flex-shrink-0 bg-amber-50 dark:bg-amber-900/20 border-b border-amber-200 dark:border-amber-800 px-4 py-3">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                    {rateLimitError.limitType === 'permanent_ban'
                      ? 'Zugang gesperrt'
                      : rateLimitError.limitType === 'temp_ban'
                        ? 'Temporar gesperrt'
                        : 'Limit erreicht'}
                  </p>
                  <p className="text-sm text-amber-700 dark:text-amber-400">{rateLimitError.message}</p>
                </div>
                {retryCountdown !== null && retryCountdown > 0 && (
                  <div className="flex items-center gap-2 bg-amber-100 dark:bg-amber-900/30 px-3 py-1.5 rounded-lg">
                    <Clock className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                    <span className="text-sm font-medium text-amber-800 dark:text-amber-300">
                      {formatRetryTime(retryCountdown)}
                    </span>
                  </div>
                )}
                <button
                  onClick={() => {
                    setRateLimitError(null);
                    setRetryCountdown(null);
                  }}
                  className="text-amber-600 dark:text-amber-400 hover:text-amber-800 dark:hover:text-amber-300 text-sm font-medium"
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
            placeholder="Frage zu medizinischen Leitlinien stellen..."
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
