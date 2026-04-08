import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Navbar.css';

export default function Navbar({ user, onLogout }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('role');
    onLogout();
    navigate('/login');
  };

  const isHR = user.role === 'HR';

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <h1 className="logo">JOZ AI HR Bot</h1>
        <ul className="nav-links">
          <li><Link to="/dashboard">Dashboard</Link></li>
          <li><Link to="/chat">Chat</Link></li>
          <li><Link to="/leave-request">Leave Request</Link></li>
          {isHR && <li><Link to="/hr-management">HR Management</Link></li>}
        </ul>
        <div className="user-section">
          <span className="username">{user.username}</span>
          {isHR && <span style={{ marginLeft: '10px', backgroundColor: '#ffb74d', color: 'white', padding: '4px 8px', borderRadius: '4px', fontSize: '12px', fontWeight: 'bold' }}>HR</span>}
          <button onClick={handleLogout} className="logout-btn">Logout</button>
        </div>
      </div>
    </nav>
  );
}
