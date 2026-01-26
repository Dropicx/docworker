/**
 * Main chat page component for GuidelineChat.
 *
 * Composes ChatSidebar, ChatMessageList, and ChatInput.
 * Handles SSE streaming and localStorage persistence.
 */

import React, { useState, useCallback } from 'react';
import { Header } from '../Header';
import { ChatSidebar } from './ChatSidebar';
import { ChatMessageList } from './ChatMessageList';
import { ChatInput } from './ChatInput';
import { useChatHistory } from '../../hooks/useChatHistory';
import { streamChatMessage } from '../../services/chatApi';
import Footer from '../Footer';

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
  } = useChatHistory();

  const [isStreaming, setIsStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  /**
   * Handle sending a message.
   */
  const handleSend = useCallback(
    async (content: string) => {
      // Get or create conversation
      let convId = activeConversationId;
      if (!convId) {
        const newConv = createConversation();
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

      try {
        // Get current Dify conversation ID for context
        const currentConv = conversations.find(c => c.id === convId);
        const difyConvId = currentConv?.difyConversationId;

        let fullContent = '';
        let newDifyConvId: string | undefined;

        // Stream the response
        for await (const event of streamChatMessage(content, difyConvId)) {
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
        console.error('Chat error:', error);
        updateMessage(assistantMessage.id, {
          content: `Fehler: ${error instanceof Error ? error.message : 'Verbindungsfehler'}`,
          isStreaming: false,
        });
      } finally {
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
    createConversation();
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
   * Handle deleting a conversation.
   */
  const handleDeleteConversation = useCallback(
    (id: string) => {
      if (window.confirm('Unterhaltung wirklich loschen?')) {
        deleteConversation(id);
      }
    },
    [deleteConversation]
  );

  // Get messages for active conversation
  const messages = activeConversation?.messages || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-50 via-white to-accent-50/30 flex flex-col">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <ChatSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={handleSelectConversation}
          onNew={handleNewConversation}
          onDelete={handleDeleteConversation}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />

        {/* Main chat area */}
        <main className="flex-1 flex flex-col min-w-0">
          <ChatMessageList messages={messages} isStreaming={isStreaming} />
          <ChatInput onSend={handleSend} disabled={isStreaming} />
        </main>
      </div>

      <Footer />
    </div>
  );
};

export default ChatPage;
