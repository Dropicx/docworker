# Frag die Leitlinie - Chatbot Documentation

> AI-powered medical guideline assistant for German AWMF guidelines

## Overview

"Frag die Leitlinie" is a RAG-based (Retrieval Augmented Generation) chatbot that answers questions about German medical guidelines (AWMF - Arbeitsgemeinschaft der Wissenschaftlichen Medizinischen Fachgesellschaften).

### Key Features

- **RAG-based answers**: Retrieves relevant guideline excerpts before generating responses
- **Source citations**: Every recommendation includes the source guideline name
- **Recommendation grades**: Displays standardized grades (soll/sollte/kann)
- **Suggested follow-up questions**: AI-generated relevant questions after each answer
- **Local conversation history**: All chats stored in browser localStorage
- **Dark mode support**: Full theme support for comfortable reading
- **Mobile responsive**: Optimized UI for all screen sizes
- **Feedback system**: Users can rate answers (thumbs up/down)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         User Browser                                 │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │ React SPA   │  │ localStorage │  │ Theme/Settings Context     │ │
│  │ (Vite)      │  │ (Chat History)│  │                             │ │
│  └──────┬──────┘  └──────────────┘  └─────────────────────────────┘ │
└─────────┼───────────────────────────────────────────────────────────┘
          │ HTTPS (Cloudflare)
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Railway (Frontend Hosting)                        │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │ Static React Build + API Proxy                                  ││
│  └──────┬──────────────────────────────────────────────────────────┘│
└─────────┼───────────────────────────────────────────────────────────┘
          │ HTTPS
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Hetzner Server (Germany)                          │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                         Dify                                     ││
│  │  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────┐  ││
│  │  │ Chat Workflow │  │ Knowledge Base│  │ Vector Database     │  ││
│  │  │               │  │ (Guidelines)  │  │ (Embeddings)        │  ││
│  │  └───────┬───────┘  └───────────────┘  └─────────────────────┘  ││
│  └──────────┼──────────────────────────────────────────────────────┘│
└─────────────┼───────────────────────────────────────────────────────┘
              │
    ┌─────────┴─────────┬─────────────────────────┐
    ▼                   ▼                         ▼
┌────────────┐  ┌───────────────────┐  ┌──────────────────┐
│ Mistral AI │  │ Amazon Bedrock    │  │ Amazon Bedrock   │
│ (France)   │  │ Titan Embeddings  │  │ Rerank           │
│            │  │ (Frankfurt)       │  │ (Frankfurt)      │
│ mistral-   │  │                   │  │                  │
│ large      │  │ Text → Vectors    │  │ Relevance Rank   │
└────────────┘  └───────────────────┘  └──────────────────┘
```

---

## Tech Stack

### Frontend (apps/chatbot)

| Technology | Purpose |
|------------|---------|
| React 18.3 | UI Framework |
| TypeScript 5.7 | Type Safety |
| Vite 6.0 | Build Tool |
| Tailwind CSS | Styling |
| @tailwindcss/typography | Prose formatting |
| react-markdown | Markdown rendering |
| react-syntax-highlighter | Code highlighting |
| lucide-react | Icons |

### Backend (Dify on Hetzner)

| Component | Purpose |
|-----------|---------|
| Dify | LLM Application Platform |
| PostgreSQL | Dify Database |
| Redis | Caching |
| Weaviate/Qdrant | Vector Database |

### AI Services

| Service | Provider | Region | Purpose |
|---------|----------|--------|---------|
| Mistral Large | Mistral AI | France (EU) | LLM for answer generation |
| Titan Embeddings | AWS Bedrock | Frankfurt (EU) | Text embeddings for RAG |
| Amazon Rerank | AWS Bedrock | Frankfurt (EU) | Relevance ranking |

### Infrastructure

| Service | Purpose |
|---------|---------|
| Railway | Frontend hosting |
| Hetzner | Dify backend hosting |
| Cloudflare | CDN, DNS, DDoS protection |

---

## Project Structure

```
apps/chatbot/
├── src/
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatPage.tsx          # Main chat page
│   │   │   ├── ChatMessage.tsx       # Message bubble with markdown
│   │   │   ├── ChatMessageList.tsx   # Scrollable message list
│   │   │   ├── ChatInput.tsx         # Input textarea + send button
│   │   │   ├── ChatSidebar.tsx       # Conversation list
│   │   │   ├── SuggestedQuestions.tsx# Follow-up questions
│   │   │   ├── CitationsDisplay.tsx  # Source document chips
│   │   │   └── MessageActions.tsx    # Like/dislike/copy buttons
│   │   ├── Header.tsx                # App header with theme toggle
│   │   └── ThemeToggle.tsx           # Dark/light mode switch
│   ├── contexts/
│   │   └── ThemeContext.tsx          # Theme state management
│   ├── hooks/
│   │   ├── useChatHistory.ts         # localStorage persistence
│   │   └── useChatStream.ts          # SSE streaming hook
│   ├── pages/
│   │   ├── Datenschutz.tsx           # Privacy policy
│   │   ├── Nutzungsbedingungen.tsx   # Terms of use
│   │   ├── Impressum.tsx             # Legal notice
│   │   └── LegalLayout.tsx           # Layout for legal pages
│   ├── services/
│   │   └── chatApi.ts                # Dify API client
│   ├── types/
│   │   └── chat.ts                   # TypeScript interfaces
│   ├── App.tsx                       # Root component
│   └── main.tsx                      # Entry point
├── public/
│   └── favicon.svg
├── index.html
├── tailwind.config.cjs
├── vite.config.ts
└── package.json
```

---

## Core Components

### ChatPage.tsx

Main orchestrator component that:
- Manages active conversation state
- Handles message sending via SSE streaming
- Processes Dify API events (message, message_end, suggested_questions)
- Extracts retriever resources for citations

### ChatMessage.tsx

Renders individual messages with:
- User/assistant avatar distinction
- Markdown rendering with prose styling
- Syntax highlighting for code blocks
- Citations display for assistant messages
- Timestamp display

### useChatStream.ts

Custom hook for Server-Sent Events (SSE) streaming:
- Connects to Dify chat-messages endpoint
- Parses streaming events in real-time
- Handles conversation_id management
- Extracts suggested questions from message_end

### useChatHistory.ts

LocalStorage persistence hook:
- Saves/loads conversations to browser storage
- Manages conversation CRUD operations
- Stores suggested questions per conversation

---

## Dify Integration

### API Endpoints

```
POST /v1/chat-messages
  - Streaming SSE response
  - conversation_id for context
  - user identifier
  - query (user message)

POST /v1/messages/:message_id/feedbacks
  - rating: "like" | "dislike" | null
```

### SSE Event Types

| Event | Purpose |
|-------|---------|
| `message` | Streaming text chunks |
| `message_end` | Final metadata with retriever_resources |
| `message_file` | File attachments (unused) |
| `error` | Error handling |

### Retriever Resources

Located in `event.metadata.retriever_resources`:
```typescript
interface RetrieverResource {
  position: number;
  dataset_id: string;
  dataset_name: string;
  document_id: string;
  document_name: string;  // Guideline name
  segment_id: string;
  score: number;          // Relevance 0-1
  content: string;        // Retrieved text chunk
}
```

---

## System Prompt

The Dify system prompt is defined in `docs/dify-guidelines-prompt.md`:

### Key Instructions

1. **Only answer from context** - No hallucination
2. **Full guideline names** - Use exact names like `[S3-Leitlinie Diagnostik, Therapie und Nachsorge des Mammakarzinoms]`
3. **Recommendation grades** - ⬆⬆ soll | ⬆ sollte | ↔ kann | ⬇ sollte nicht | ⬇⬇ soll nicht
4. **Evidence levels** - Where available (LoE 1a, 2b, etc.)
5. **Structured output** - Numbered topic sections for complex answers
6. **No source blocks** - Inline citations only

---

## Data Flow

### 1. User Sends Message

```
User types → ChatInput → onSend callback
                              ↓
ChatPage creates message → Updates state
                              ↓
useChatStream hook → POST /chat-messages (SSE)
```

### 2. Streaming Response

```
Dify SSE stream → message events → Append to content
                       ↓
           message_end event → Extract resources
                       ↓
           Update message.retrieverResources
                       ↓
           suggested_questions event → Update UI
```

### 3. Conversation Persistence

```
Message complete → useChatHistory.addMessage()
                         ↓
              localStorage.setItem('chat-history')
```

---

## Configuration

### Environment Variables

```bash
# Frontend (apps/chatbot/.env)
VITE_DIFY_API_URL=https://your-dify-instance.com/v1
VITE_DIFY_API_KEY=app-xxxxxxxxxxxx
```

### Tailwind Configuration

```javascript
// tailwind.config.cjs
module.exports = {
  plugins: [
    require('@tailwindcss/typography'),
  ],
  theme: {
    extend: {
      colors: {
        brand: { /* Primary brand colors */ },
        accent: { /* Secondary accent */ },
        neutral: { /* Grays */ },
      },
    },
  },
};
```

---

## Deployment

### Railway (Frontend)

1. Connect GitHub repository
2. Set environment variables:
   - `VITE_DIFY_API_URL`
   - `VITE_DIFY_API_KEY`
3. Build command: `npm run build`
4. Start command: `npm run preview`

### Hetzner (Dify Backend)

1. Docker Compose setup for Dify
2. Configure SSL via Caddy/nginx
3. Set up PostgreSQL, Redis, Vector DB
4. Import guideline documents to knowledge base

### Cloudflare

1. Add domain DNS records
2. Enable SSL (Full Strict)
3. Configure caching rules
4. Enable Bot Protection

---

## Performance Considerations

### Frontend

- **Code splitting**: React.lazy for legal pages
- **Message virtualization**: Consider for very long conversations
- **Debounced scroll**: Optimized scroll-to-bottom logic
- **LocalStorage limits**: ~5MB per origin

### API

- **Streaming**: SSE for real-time response
- **Connection pooling**: Managed by Dify
- **Rate limiting**: Configure in Cloudflare

---

## Security

### Data Privacy

- **No server-side chat storage**: Conversations stay in browser
- **No PII in queries**: Users warned not to enter patient data
- **EU data processing**: Mistral (France), AWS Frankfurt, Hetzner (Germany)
- **GDPR compliant**: Detailed privacy policy

### API Security

- **API key protection**: Server-side proxy recommended for production
- **CORS**: Configured for allowed origins
- **HTTPS**: Enforced via Cloudflare

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No citations showing | Check `event.metadata.retriever_resources` path |
| Streaming not working | Verify SSE connection, check CORS |
| Dark mode not persisting | Check localStorage access |
| Mobile sidebar issues | Verify z-index and transform classes |

### Debug Logging

Add to ChatPage.tsx:
```typescript
console.log('[ChatPage] message_end event:', event);
console.log('[ChatPage] retrieverResources:', event.metadata?.retriever_resources);
```

---

## Future Improvements

- [ ] Export conversation to PDF
- [ ] Share conversation link
- [ ] Voice input/output
- [ ] Multi-language support
- [ ] Guideline version tracking
- [ ] Advanced search within conversations
- [ ] User accounts (optional)

---

## Related Documentation

- [Architecture Overview](./ARCHITECTURE.md)
- [API Reference](./API.md)
- [Deployment Guide](./DEPLOYMENT.md)
- [Dify System Prompt](./dify-guidelines-prompt.md)

---

*Last updated: January 2025*
