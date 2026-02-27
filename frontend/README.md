# AI Chatbot Frontend

A premium React application built with Tailwind CSS and Lucide Icons that mimics the Google Gemini/ChatGPT interface.

## Features

### 🎨 Premium UI/UX
- **Gemini-Inspired Design**: Minimalist white theme with Inter font, soft rounded corners, and subtle transitions
- **Glassmorphism Effects**: Modern glass-like UI elements with backdrop blur
- **Smooth Animations**: Powered by Framer Motion for delightful user interactions
- **Responsive Design**: Works seamlessly on desktop and mobile devices

### 🔐 Authentication
- Professional Login/Signup page
- Business Account toggle for role-based access
- JWT token management with automatic refresh
- Persistent sessions with localStorage

### 👔 Business Dashboard (Business Role Only)
- **File Upload**: Drag-and-drop interface for PDF and TXT files
- **Progress Tracking**: Real-time upload progress with shimmer effects
- **File Management**: View uploaded files with status badges (Processed, Processing, Failed)
- **Test Bot**: Launch chat interface to test your AI bot after uploading documents

### 💬 Chat Interface (All Roles)
- **Streaming Text Effect**: AI responses appear word-by-word for natural conversation flow
- **Suggested Questions**: Quick-start chips for common queries
- **Clean Message Bubbles**: Distinct styling for user and AI messages
- **Glassmorphism Input**: Premium input bar with gradient send button
- **New Chat**: Start fresh conversations anytime

### 🔄 Role-Based Routing
- Business users → Dashboard on login
- Regular users → Chat interface on login
- Protected routes with automatic redirects

## Tech Stack

- **React 18** - UI library
- **React Router DOM** - Client-side routing
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Beautiful icon library
- **Framer Motion** - Animation library
- **Axios** - HTTP client with interceptors
- **Vite** - Fast build tool and dev server

## Project Structure

```
frontend/
├── src/
│   ├── context/
│   │   └── AuthContext.jsx       # Global authentication state
│   ├── pages/
│   │   ├── Auth.jsx               # Login/Signup page
│   │   ├── Dashboard.jsx          # Business dashboard
│   │   └── Chat.jsx               # Chat interface
│   ├── api.js                     # Axios instance with JWT interceptors
│   ├── App.jsx                    # Main app with routing
│   ├── main.jsx                   # React entry point
│   └── index.css                  # Tailwind styles and custom components
├── index.html                     # HTML entry point
├── package.json                   # Dependencies
├── vite.config.js                 # Vite configuration
├── tailwind.config.js             # Tailwind configuration
└── postcss.config.js              # PostCSS configuration
```

## Getting Started

### Prerequisites
- Node.js 16+ and npm
- Backend API running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

The optimized build will be in the `dist` folder.

## API Integration

The frontend expects the following backend endpoints:

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login (form-data with username/password)
- `POST /auth/refresh` - Token refresh

### Documents (Business Users)
- `GET /documents/` - List all documents
- `POST /documents/upload` - Upload a document (multipart/form-data)
- `DELETE /documents/{id}` - Delete a document

### Chat
- `POST /chat/` - Send a message and get AI response

## Environment Variables

The API base URL is configured in `src/api.js`. To change it, modify:

```javascript
const api = axios.create({
  baseURL: 'http://localhost:8000', // Change this to your backend URL
  // ...
});
```

## Design System

### Colors
- **Gemini Palette**: Custom gradient colors from gemini-50 to gemini-900
- **Primary**: Gradient from gemini-600 to gemini-500
- **Background**: White with subtle gradients

### Typography
- **Font**: Inter (loaded from Google Fonts)
- **Weights**: 300, 400, 500, 600, 700

### Components
- `.btn-primary` - Primary gradient button
- `.btn-secondary` - Secondary gray button
- `.btn-ghost` - Transparent hover button
- `.input-field` - Styled input with focus ring
- `.card` - Rounded card with hover effect
- `.badge-*` - Status badges (success, warning, error, info)
- `.chat-bubble-user` - User message bubble
- `.chat-bubble-ai` - AI message bubble
- `.glass` - Glassmorphism effect

### Animations
- `animate-shimmer` - Loading shimmer effect
- `animate-fade-in` - Fade in animation
- `animate-slide-up` - Slide up animation

## User Flows

### Business User Flow
1. Sign up with "Business Account" toggle
2. Login → Redirected to Dashboard
3. Upload PDF/TXT documents via drag-and-drop
4. View uploaded files with processing status
5. Click "Test Your Bot" to open chat interface
6. Chat with AI trained on uploaded documents

### Regular User Flow
1. Sign up as regular user
2. Login → Redirected to Chat interface
3. Start chatting immediately with suggested questions
4. Enjoy streaming AI responses

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## License

MIT
