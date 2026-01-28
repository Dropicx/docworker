/**
 * Main App component for Frag die Leitlinie standalone chat.
 * Uses React Router for legal page navigation.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ChatPage } from './components/chat/ChatPage';
import { Impressum } from './pages/Impressum';
import { Datenschutz } from './pages/Datenschutz';
import { Nutzungsbedingungen } from './pages/Nutzungsbedingungen';
import './styles/index.css';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<ChatPage />} />
        <Route path="/impressum" element={<Impressum />} />
        <Route path="/datenschutz" element={<Datenschutz />} />
        <Route path="/nutzungsbedingungen" element={<Nutzungsbedingungen />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
