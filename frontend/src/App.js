import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import LeaveRequestPage from './pages/LeaveRequestPage';
import HRManagementPage from './pages/HRManagementPage';
import './App.css';

export default function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    const username = localStorage.getItem('username');
    const role = localStorage.getItem('role');
    
    if (token && username) {
      setUser({ token, username, role });
    }
    setLoading(false);
  }, []);

  if (loading) {
    return <div className="loading">Loading...</div>;
  }

  return (
    <BrowserRouter>
      {user && <Navbar user={user} onLogout={() => setUser(null)} />}
      <main className="main-content">
        <Routes>
          <Route
            path="/login"
            element={user ? <Navigate to="/dashboard" /> : <LoginPage onLogin={setUser} />}
          />
          <Route
            path="/dashboard"
            element={user ? <DashboardPage user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/chat"
            element={user ? <ChatPage user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/leave-request"
            element={user ? <LeaveRequestPage user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/hr-management"
            element={user && user.role === 'HR' ? <HRManagementPage user={user} /> : <Navigate to="/dashboard" />}
          />
          <Route path="/" element={<Navigate to={user ? '/dashboard' : '/login'} />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}
