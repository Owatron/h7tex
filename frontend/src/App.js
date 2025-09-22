import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import AuthPage from './pages/Auth';
import Dashboard from './pages/Dashboard';
import Spreadsheet from './pages/Spreadsheet';
import { Toaster } from 'react-hot-toast'; // Import the Toaster

function AppContent() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
        Loading...
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={!user ? <AuthPage /> : <Navigate to="/" />} />
      <Route path="/auth" element={!user ? <AuthPage /> : <Navigate to="/" />} />
      <Route path="/spreadsheet/:id" element={user ? <Spreadsheet /> : <Navigate to="/auth" />} />
      <Route path="/" element={user ? <Dashboard /> : <Navigate to="/auth" />} />
    </Routes>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <div> {/* Add a wrapper div */}
          <Toaster position="top-center" reverseOrder={false} /> {/* Add the Toaster component here */}
          <AppContent />
        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;


