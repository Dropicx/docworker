/**
 * Chat sidebar with conversation list.
 */

import React from 'react';
import {
  Plus,
  MessageSquare,
  Trash2,
  X,
  Menu,
} from 'lucide-react';
import { ChatConversation } from '../../types/chat';

interface ChatSidebarProps {
  conversations: ChatConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  isOpen: boolean;
  onToggle: () => void;
}

export const ChatSidebar: React.FC<ChatSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  isOpen,
  onToggle,
}) => {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return 'Heute';
    } else if (days === 1) {
      return 'Gestern';
    } else if (days < 7) {
      return `Vor ${days} Tagen`;
    } else {
      return date.toLocaleDateString('de-DE', {
        day: '2-digit',
        month: '2-digit',
      });
    }
  };

  return (
    <>
      {/* Mobile toggle button */}
      <button
        onClick={onToggle}
        className="md:hidden fixed top-20 left-3 z-40 p-2 bg-white rounded-lg shadow-lg border border-neutral-200"
        title={isOpen ? 'Menu schliessen' : 'Menu offnen'}
      >
        {isOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Overlay for mobile */}
      {isOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/30 z-30"
          onClick={onToggle}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed md:relative inset-y-0 left-0 z-40
          w-72 h-full bg-white border-r border-neutral-200
          flex flex-col overflow-hidden
          transform transition-transform duration-200 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}
          md:transform-none
        `}
      >
        {/* Header */}
        <div className="p-4 border-b border-neutral-200">
          <button
            onClick={onNew}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-brand-600 text-white rounded-lg hover:bg-brand-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="font-medium">Neue Unterhaltung</span>
          </button>
        </div>

        {/* Conversation list */}
        <div className="flex-1 overflow-y-auto p-2">
          {conversations.length === 0 ? (
            <div className="text-center py-8 text-neutral-500">
              <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Keine Unterhaltungen</p>
            </div>
          ) : (
            <div className="space-y-1">
              {conversations.map(conv => (
                <div
                  key={conv.id}
                  className={`
                    group relative rounded-lg cursor-pointer transition-colors
                    ${
                      conv.id === activeId
                        ? 'bg-brand-50 border border-brand-200'
                        : 'hover:bg-neutral-50 border border-transparent'
                    }
                  `}
                >
                  <button
                    onClick={() => {
                      onSelect(conv.id);
                      // Close sidebar on mobile after selection
                      if (window.innerWidth < 768) {
                        onToggle();
                      }
                    }}
                    className="w-full text-left p-3 pr-10"
                  >
                    <div className="flex items-start gap-2">
                      <MessageSquare
                        className={`w-4 h-4 mt-0.5 flex-shrink-0 ${
                          conv.id === activeId ? 'text-brand-600' : 'text-neutral-400'
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-sm font-medium truncate ${
                            conv.id === activeId ? 'text-brand-700' : 'text-neutral-700'
                          }`}
                        >
                          {conv.title}
                        </p>
                        <p className="text-xs text-neutral-400 mt-0.5">
                          {formatDate(conv.updatedAt)}
                        </p>
                      </div>
                    </div>
                  </button>

                  {/* Delete button */}
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      onDelete(conv.id);
                    }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 text-neutral-400 hover:text-error-600 hover:bg-error-50 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Loschen"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-neutral-200 text-center">
          <p className="text-xs text-neutral-400">
            Verlauf wird lokal gespeichert
          </p>
        </div>
      </aside>
    </>
  );
};

export default ChatSidebar;
